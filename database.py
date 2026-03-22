import sqlite3
import os
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "race.db")

DEFAULT_KM    = "2.62"
DEFAULT_DUREE = "86400"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS rouleurs (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            nom  TEXT    NOT NULL UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS passages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            entite    TEXT    NOT NULL,
            timestamp REAL    NOT NULL,
            type      TEXT    NOT NULL DEFAULT 'passage'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS changements (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            velo               INTEGER NOT NULL,
            rouleur_sortant_id INTEGER,
            rouleur_entrant_id INTEGER NOT NULL,
            timestamp          REAL    NOT NULL,
            FOREIGN KEY(rouleur_entrant_id) REFERENCES rouleurs(id)
        )
    """)

    # File d'attente : position ordonnée par velo
    c.execute("""
        CREATE TABLE IF NOT EXISTS file_attente (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            velo       INTEGER NOT NULL,
            rouleur_id INTEGER NOT NULL,
            position   INTEGER NOT NULL,
            FOREIGN KEY(rouleur_id) REFERENCES rouleurs(id)
        )
    """)

    # Offset de tours par vélo (ajusté automatiquement quand écart > 3min)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tour_offset (
            velo    INTEGER PRIMARY KEY,
            offset  INTEGER NOT NULL DEFAULT 0
        )
    """)
    c.execute("INSERT OR IGNORE INTO tour_offset VALUES (1, 0)")
    c.execute("INSERT OR IGNORE INTO tour_offset VALUES (2, 0)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            cle    TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )
    """)

    defaults = {
        "km_par_tour":       DEFAULT_KM,
        "race_start":        "",
        "race_duree":        DEFAULT_DUREE,
        "race_name":         "24h Vélo du Bois de la Cambre",
        "depart_rouleur_v1": "",
        "depart_rouleur_v2": "",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO config VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()


# ── Config ────────────────────────────────────────────────────────────────────

def get_config(cle):
    conn = get_connection()
    row = conn.execute("SELECT valeur FROM config WHERE cle=?", (cle,)).fetchone()
    conn.close()
    return row["valeur"] if row else None


def set_config(cle, valeur):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config VALUES (?,?)", (cle, str(valeur)))
    conn.commit()
    conn.close()


# ── Passages ──────────────────────────────────────────────────────────────────

def save_passage(entite, timestamp, type_event="passage"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO passages (entite, timestamp, type) VALUES (?,?,?)",
        (entite, timestamp, type_event)
    )
    conn.commit()
    conn.close()


def get_passages(entite):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM passages WHERE entite=? ORDER BY timestamp ASC",
        (entite,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_last_passage(entite):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM passages WHERE entite=? ORDER BY timestamp DESC LIMIT 1",
        (entite,)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM passages WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()


# ── Rouleurs ──────────────────────────────────────────────────────────────────

def save_rouleur(nom):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO rouleurs (nom) VALUES (?)", (nom,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    row = conn.execute("SELECT id FROM rouleurs WHERE nom=?", (nom,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_rouleurs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM rouleurs ORDER BY nom").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_rouleur_by_id(rouleur_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM rouleurs WHERE id=?", (rouleur_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def import_rouleurs_csv(filepath):
    count = 0
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(filepath, newline='', encoding=encoding) as f:
                lines = [l.rstrip('\r\n') for l in f if l.strip()]
            break
        except UnicodeDecodeError:
            continue
    else:
        return 0
    if lines and lines[0].strip().lower() == 'nom':
        lines = lines[1:]
    for line in lines:
        nom = line.split(',')[0].split(';')[0].strip()
        if nom:
            save_rouleur(nom)
            count += 1
    return count


# ── Changements ───────────────────────────────────────────────────────────────

def save_changement(velo, rouleur_sortant_id, rouleur_entrant_id, timestamp):
    conn = get_connection()
    conn.execute(
        "INSERT INTO changements (velo, rouleur_sortant_id, rouleur_entrant_id, timestamp) VALUES (?,?,?,?)",
        (velo, rouleur_sortant_id, rouleur_entrant_id, timestamp)
    )
    conn.commit()
    conn.close()


def get_changements(velo):
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*,
               r_in.nom  AS rouleur_entrant_nom,
               r_out.nom AS rouleur_sortant_nom
        FROM changements c
        JOIN rouleurs r_in ON c.rouleur_entrant_id = r_in.id
        LEFT JOIN rouleurs r_out ON c.rouleur_sortant_id = r_out.id
        WHERE c.velo=?
        ORDER BY c.timestamp ASC
    """, (velo,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── File d'attente ────────────────────────────────────────────────────────────

def get_file_attente(velo):
    """Retourne la file dans l'ordre de position."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT f.id, f.position, f.velo, r.id as rouleur_id, r.nom
        FROM file_attente f
        JOIN rouleurs r ON f.rouleur_id = r.id
        WHERE f.velo=?
        ORDER BY f.position ASC
    """, (velo,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_to_file(velo, rouleur_id):
    """Ajoute un rouleur en fin de file."""
    conn = get_connection()
    max_pos = conn.execute(
        "SELECT MAX(position) as m FROM file_attente WHERE velo=?", (velo,)
    ).fetchone()["m"] or 0
    conn.execute(
        "INSERT INTO file_attente (velo, rouleur_id, position) VALUES (?,?,?)",
        (velo, rouleur_id, max_pos + 1)
    )
    conn.commit()
    conn.close()


def remove_from_file(file_id):
    """Supprime un rouleur de la file par son id de ligne."""
    conn = get_connection()
    conn.execute("DELETE FROM file_attente WHERE id=?", (file_id,))
    conn.commit()
    conn.close()


def pop_file_attente(velo):
    """Retire et retourne le 1er rouleur de la file (prochain à rouler)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM file_attente WHERE velo=? ORDER BY position ASC LIMIT 1",
        (velo,)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM file_attente WHERE id=?", (row["id"],))
        conn.commit()
        r = get_rouleur_by_id(row["rouleur_id"])
        conn.close()
        return r["nom"] if r else None
    conn.close()
    return None


def move_file_entry(file_id, direction, velo):
    """Monte (direction=-1) ou descend (direction=+1) un élément dans la file."""
    conn = get_connection()
    entries = conn.execute(
        "SELECT id, position FROM file_attente WHERE velo=? ORDER BY position ASC",
        (velo,)
    ).fetchall()
    entries = [dict(e) for e in entries]
    idx = next((i for i, e in enumerate(entries) if e["id"] == file_id), None)
    if idx is None:
        conn.close()
        return
    swap_idx = idx + direction
    if 0 <= swap_idx < len(entries):
        p1 = entries[idx]["position"]
        p2 = entries[swap_idx]["position"]
        conn.execute("UPDATE file_attente SET position=? WHERE id=?", (p2, entries[idx]["id"]))
        conn.execute("UPDATE file_attente SET position=? WHERE id=?", (p1, entries[swap_idx]["id"]))
        conn.commit()
    conn.close()


# ── Tour offset (pour le calcul d'écart) ─────────────────────────────────────

def get_tour_offset(velo):
    conn = get_connection()
    row = conn.execute("SELECT offset FROM tour_offset WHERE velo=?", (velo,)).fetchone()
    conn.close()
    return row["offset"] if row else 0


def set_tour_offset(velo, offset):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO tour_offset VALUES (?,?)", (velo, offset))
    conn.commit()
    conn.close()


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset_all():
    conn = get_connection()
    conn.execute("DELETE FROM passages")
    conn.execute("DELETE FROM changements")
    conn.execute("DELETE FROM file_attente")
    conn.execute("UPDATE tour_offset SET offset=0")
    conn.execute("UPDATE config SET valeur='' WHERE cle='race_start'")
    conn.execute("UPDATE config SET valeur='' WHERE cle='depart_rouleur_v1'")
    conn.execute("UPDATE config SET valeur='' WHERE cle='depart_rouleur_v2'")
    conn.commit()
    conn.close()


# ── Export CSV ────────────────────────────────────────────────────────────────

def export_historique_csv(velo_state, velo_num, output_dir):
    """
    Exporte l'historique complet d'un vélo en CSV.
    Retourne le chemin du fichier créé.
    """
    from models import format_duration, format_speed, KM_PAR_TOUR, reload_km
    reload_km()

    filename = os.path.join(output_dir, f"historique_velo{velo_num}.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Tour #", "Type", "Durée", "Vitesse (km/h)", "Km cumulé", "Rouleur"])
        km_cumul = 0.0
        for i, t in enumerate(velo_state.tour_times):
            rouleur = velo_state.get_rouleur_at_time(velo_state.timestamps[i]) or "?"
            type_tour = "Départ" if i == 0 else "Course"
            km_cumul += KM_PAR_TOUR
            spd = KM_PAR_TOUR / (t / 3600) if t > 0 else 0
            writer.writerow([
                i + 1,
                type_tour,
                format_duration(t),
                f"{spd:.2f}",
                f"{km_cumul:.2f}",
                rouleur
            ])
    return filename
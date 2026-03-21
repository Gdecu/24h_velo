import sqlite3
import os
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "race.db")

DEFAULT_KM    = "2.62"
DEFAULT_DUREE = "86400"   # 24h en secondes


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    # Rouleurs partagés entre les deux vélos
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            cle    TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )
    """)

    defaults = {
        "km_par_tour": DEFAULT_KM,
        "race_start":  "",
        "race_duree":  DEFAULT_DUREE,
        "race_name":   "24h Vélo du Bois de la Cambre",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO config VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()


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
    """
    Importe les rouleurs depuis un CSV.
    Gère les fichiers à une seule colonne (sans délimiteur détectable),
    avec ou sans en-tête 'nom', encodage UTF-8 ou Latin-1.
    """
    count = 0
    # Essayer d'abord UTF-8, puis Latin-1 en fallback
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(filepath, newline='', encoding=encoding) as f:
                lines = [l.rstrip('\r\n') for l in f if l.strip()]
            break
        except UnicodeDecodeError:
            continue
    else:
        print("[import_csv] Impossible de décoder le fichier.")
        return 0

    # Sauter la ligne d'en-tête si elle vaut exactement 'nom' (insensible à la casse)
    if lines and lines[0].strip().lower() == 'nom':
        lines = lines[1:]

    for line in lines:
        # Prendre la première colonne si séparateur présent, sinon toute la ligne
        nom = line.split(',')[0].split(';')[0].strip()
        if nom:
            save_rouleur(nom)
            count += 1

    return count


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


def reset_all():
    conn = get_connection()
    conn.execute("DELETE FROM passages")
    conn.execute("DELETE FROM changements")
    conn.execute("UPDATE config SET valeur='' WHERE cle='race_start'")
    conn.commit()
    conn.close()

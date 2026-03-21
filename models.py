import time
from database import get_passages, get_changements, get_config

KM_PAR_TOUR = 2.62


def reload_km():
    global KM_PAR_TOUR
    val = get_config("km_par_tour")
    if val:
        try:
            KM_PAR_TOUR = float(val.replace(",", "."))
        except ValueError:
            pass


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_speed(km, seconds):
    if seconds and seconds > 0:
        speed = km / (seconds / 3600)
        return f"{speed:.1f} km/h"
    return "--"


def is_race_finished():
    """Retourne True si la course est terminée (temps écoulé)."""
    start_str = get_config("race_start")
    duree_str = get_config("race_duree")
    if not start_str or not duree_str:
        return False
    try:
        elapsed = time.time() - float(start_str)
        return elapsed >= float(duree_str)
    except Exception:
        return False


def is_race_started():
    """Retourne True si la course a démarré."""
    start_str = get_config("race_start")
    return bool(start_str and start_str.strip())


class EntityState:
    def __init__(self, entite_key):
        self.entite_key = entite_key
        self.timestamps = []
        self.tour_times = []   # durée de chaque tour, index 0 = tour #1 (départ)

    def load_from_db(self):
        passages = get_passages(self.entite_key)
        self.timestamps = [p["timestamp"] for p in passages]
        self._compute_tours()

    def add_passage(self, ts):
        self.timestamps.append(ts)
        self._compute_tours()

    def _compute_tours(self):
        self.tour_times = []
        for i in range(1, len(self.timestamps)):
            self.tour_times.append(self.timestamps[i] - self.timestamps[i - 1])

    @property
    def nb_tours(self):
        return max(0, len(self.timestamps) - 1)

    @property
    def km_total(self):
        reload_km()
        return self.nb_tours * KM_PAR_TOUR

    @property
    def dernier_tour(self):
        if self.tour_times:
            return self.tour_times[-1]
        return None

    @property
    def derniers_tours(self):
        """5 derniers tours (du plus récent au plus ancien), avec numéro."""
        tours = self.tour_times
        if not tours:
            return []
        result = []
        total = len(tours)
        for i, t in enumerate(reversed(tours[-5:])):
            num = total - i
            is_depart = (total - i) == 1
            result.append({"num": num, "time": t, "is_depart": is_depart})
        return result

    @property
    def tour_times_ranked(self):
        """Tours sans le 1er pour les classements."""
        if len(self.tour_times) <= 1:
            return []
        return self.tour_times[1:]

    @property
    def meilleurs_tours(self):
        """Top 5 sans le 1er tour (départ)."""
        return sorted(self.tour_times_ranked)[:5]

    @property
    def temps_depuis_dernier_passage(self):
        if not self.timestamps:
            return None
        if is_race_finished() and self.timestamps:
            # Course terminée : on fige le dernier chrono affiché
            end_ts = float(get_config("race_start")) + float(get_config("race_duree"))
            return end_ts - self.timestamps[-1]
        return time.time() - self.timestamps[-1]

    @property
    def vitesse_dernier_tour(self):
        t = self.dernier_tour
        if t:
            return format_speed(KM_PAR_TOUR, t)
        return "--"

    @property
    def vitesse_moyenne(self):
        ranked = self.tour_times_ranked
        if ranked:
            return format_speed(KM_PAR_TOUR, sum(ranked) / len(ranked))
        return "--"

    def get_tour_at_time(self, ts):
        count = sum(1 for t in self.timestamps if t <= ts)
        return max(0, count - 1)


class VeloState(EntityState):
    def __init__(self, velo_num):
        super().__init__(f"velo{velo_num}")
        self.velo_num = velo_num
        self.changements = []
        self.rouleur_actuel = None
        self.prochain_rouleur = None

    def load_from_db(self):
        super().load_from_db()
        self._load_changements()

    def _load_changements(self):
        self.changements = get_changements(self.velo_num)
        if self.changements:
            self.rouleur_actuel = self.changements[-1].get("rouleur_entrant_nom")

    def set_prochain(self, nom):
        self.prochain_rouleur = nom

    def confirmer_changement(self, ts):
        if self.prochain_rouleur:
            ancien = self.rouleur_actuel
            self.rouleur_actuel = self.prochain_rouleur
            self.prochain_rouleur = None
            return ancien
        return None

    def get_rouleur_at_time(self, ts):
        rouleur = None
        for c in self.changements:
            if c["timestamp"] <= ts:
                rouleur = c.get("rouleur_entrant_nom")
            else:
                break
        return rouleur

    def get_stats_par_rouleur(self):
        """
        Retourne {nom: {...}}.
        Le tour #1 (départ) est inclus dans km/tours mais exclu du meilleur_tour
        et de tours_ranked (classements).
        """
        stats = {}
        for i, tour_time in enumerate(self.tour_times):
            ts_debut = self.timestamps[i]
            rouleur = self.get_rouleur_at_time(ts_debut) or "Inconnu"
            if rouleur not in stats:
                stats[rouleur] = {
                    "tours": 0, "km": 0.0,
                    "meilleur_tour": None, "temps_total": 0.0,
                    "tous_les_tours": [], "tours_ranked": []
                }
            is_depart = (i == 0)
            stats[rouleur]["tours"] += 1
            stats[rouleur]["km"] += KM_PAR_TOUR
            stats[rouleur]["temps_total"] += tour_time
            stats[rouleur]["tous_les_tours"].append((tour_time, is_depart))

            # Exclure le tour de départ des classements
            if not is_depart:
                stats[rouleur]["tours_ranked"].append(tour_time)
                cur = stats[rouleur]["meilleur_tour"]
                if cur is None or tour_time < cur:
                    stats[rouleur]["meilleur_tour"] = tour_time
        return stats


class RetardCalculator:
    """
    Calcule l'ecart entre un velo et le peloton.

    Convention de signe :
      ecart > 0  => velo DERRIERE le peloton  (retard)  => rouge/orange
      ecart < 0  => velo DEVANT  le peloton  (avance)  => vert

    Regle d'affichage (visuelle uniquement, compteurs inchanges) :
      Si |ecart| < 60s => approx_meme_tour=True => affichage "~ meme tour"

    Calcul :
      N = min(tours_peloton, tours_velo)
      ecart_brut = timestamps_peloton[N] - timestamps_velo[N]
        positif = peloton passe APRES velo au tour N = velo etait devant
      retard = -ecart_brut   (positif = velo derriere)
    """

    SEUIL_MEME_TOUR = 60

    def compute(self, peloton, velo):
        """
        Retourne (ecart_secondes, ecart_tours, approx_meme_tour).
          ecart_secondes   : positif=retard, negatif=avance, None si pas calculable
          ecart_tours      : positif=tours de retard, negatif=tours d'avance
          approx_meme_tour : True si |ecart| < 60s
        """
        if not peloton.timestamps or not velo.timestamps:
            return None, 0, False

        tours_p = peloton.nb_tours
        tours_v = velo.nb_tours
        ecart_tours = tours_p - tours_v

        N = min(tours_p, tours_v)
        if N == 0:
            return None, ecart_tours, False

        ts_p = peloton.timestamps[N]
        ts_v = velo.timestamps[N]

        ecart_brut = ts_p - ts_v        # positif = peloton arrive apres velo = velo devant
        ecart_secondes = -ecart_brut    # positif = retard velo

        approx_meme_tour = abs(ecart_secondes) < self.SEUIL_MEME_TOUR

        return ecart_secondes, ecart_tours, approx_meme_tour
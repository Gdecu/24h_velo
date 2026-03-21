import tkinter as tk
import customtkinter as ctk
import time

from models import (EntityState, VeloState, RetardCalculator,
                    format_duration, format_speed, reload_km, KM_PAR_TOUR,
                    is_race_finished, is_race_started)
from database import (save_passage, save_changement, save_rouleur,
                      get_rouleurs, get_config, delete_last_passage, reset_all, set_config)

# ── Palette ───────────────────────────────────────────────────────────────────
CLR_BG      = "#0d0f14"
CLR_CARD    = "#141720"
CLR_BORDER  = "#1e2233"
CLR_ACCENT1 = "#00d4ff"
CLR_ACCENT2 = "#ff6b35"
CLR_PELOTON = "#a8ff3e"
CLR_TEXT    = "#e8eaf0"
CLR_MUTED   = "#6b7280"
CLR_GOOD    = "#22c55e"
CLR_WARN    = "#f59e0b"
CLR_BAD     = "#ef4444"
CLR_PREP    = "#7c3aed"
CLR_END     = "#1a0a00"

FONT_MED    = ("Consolas", 18, "bold")
FONT_SMALL  = ("Consolas", 11)
FONT_MICRO  = ("Consolas", 10)
FONT_BTN    = ("Consolas", 12, "bold")
FONT_BTN_SM = ("Consolas", 10)


# ── Dialog préparer rouleur ───────────────────────────────────────────────────

class DialogProchainRouleur(ctk.CTkToplevel):
    def __init__(self, parent, velo_num, current_next, on_confirm):
        super().__init__(parent)
        self.on_confirm = on_confirm
        color = CLR_ACCENT1 if velo_num == 1 else CLR_ACCENT2

        self.title(f"Préparer le prochain rouleur — Vélo {velo_num}")
        self.geometry("420x520")
        self.configure(fg_color=CLR_BG)
        self.resizable(False, False)
        self.grab_set(); self.lift(); self.focus_force()

        ctk.CTkLabel(self, text=f"⏭  PROCHAIN ROULEUR — VÉLO {velo_num}",
                     font=("Consolas", 14, "bold"), text_color=color
                     ).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Ce rouleur sera prêt pour le prochain changement.",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(0, 10))

        self.selected = tk.StringVar(value=current_next or "")
        scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD,
                                        corner_radius=8, width=360, height=240)
        scroll.pack(padx=24, pady=(0, 10))

        rouleurs = get_rouleurs()
        if rouleurs:
            for r in rouleurs:
                ctk.CTkRadioButton(scroll, text=r["nom"],
                                   variable=self.selected, value=r["nom"],
                                   fg_color=color, text_color=CLR_TEXT,
                                   font=FONT_SMALL
                                   ).pack(anchor="w", padx=8, pady=3)
        else:
            ctk.CTkLabel(scroll, text="Aucun rouleur — ajoutez-en dans Config",
                         text_color=CLR_MUTED, font=FONT_SMALL).pack(pady=8)

        ctk.CTkLabel(self, text="Ou ajouter :", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=24)
        self.entry = ctk.CTkEntry(self, placeholder_text="Prénom Nom",
                                  fg_color=CLR_CARD, border_color=CLR_BORDER,
                                  text_color=CLR_TEXT, font=FONT_SMALL, width=360)
        self.entry.pack(padx=24, pady=(4, 14))

        ctk.CTkButton(self, text="✓  CONFIRMER",
                      fg_color=color, text_color="#fff",
                      font=FONT_BTN, height=44,
                      command=self._confirm).pack(padx=24, fill="x")
        ctk.CTkButton(self, text="Annuler", fg_color="transparent",
                      text_color=CLR_MUTED, font=FONT_SMALL, height=30,
                      command=self.destroy).pack(padx=24, pady=(6, 0), fill="x")

    def _confirm(self):
        nouveau = self.entry.get().strip()
        nom = nouveau if nouveau else self.selected.get().strip()
        if not nom:
            self.entry.configure(border_color=CLR_BAD)
            return
        save_rouleur(nom)
        self.on_confirm(nom)
        self.destroy()


# ── Dialog rouleur de départ ──────────────────────────────────────────────────

class DialogDepartRouleur(ctk.CTkToplevel):
    """Sélection obligatoire du rouleur de départ avant le 1er passage."""
    def __init__(self, parent, velo_num, on_confirm):
        super().__init__(parent)
        self.on_confirm = on_confirm
        color = CLR_ACCENT1 if velo_num == 1 else CLR_ACCENT2

        self.title(f"Rouleur de départ — Vélo {velo_num}")
        self.geometry("420x480")
        self.configure(fg_color=CLR_BG)
        self.resizable(False, False)
        self.grab_set(); self.lift(); self.focus_force()
        # Bloquer la fermeture sans confirmer
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(self, text=f"🚦  ROULEUR DE DÉPART — VÉLO {velo_num}",
                     font=("Consolas", 14, "bold"), text_color=color
                     ).pack(pady=(20, 4))
        ctk.CTkLabel(self,
                     text="Sélectionnez le rouleur qui part en premier\navant d'enregistrer le départ.",
                     font=FONT_SMALL, text_color=CLR_MUTED, justify="center"
                     ).pack(pady=(0, 12))

        self.selected = tk.StringVar(value="")
        scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD,
                                        corner_radius=8, width=360, height=220)
        scroll.pack(padx=24, pady=(0, 10))

        rouleurs = get_rouleurs()
        if rouleurs:
            for r in rouleurs:
                ctk.CTkRadioButton(scroll, text=r["nom"],
                                   variable=self.selected, value=r["nom"],
                                   fg_color=color, text_color=CLR_TEXT,
                                   font=FONT_SMALL
                                   ).pack(anchor="w", padx=8, pady=3)

        ctk.CTkLabel(self, text="Ou nouveau rouleur :", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(anchor="w", padx=24)
        self.entry = ctk.CTkEntry(self, placeholder_text="Prénom Nom",
                                  fg_color=CLR_CARD, border_color=CLR_BORDER,
                                  text_color=CLR_TEXT, font=FONT_SMALL, width=360)
        self.entry.pack(padx=24, pady=(4, 14))

        ctk.CTkButton(self, text="✓  CONFIRMER LE DÉPART",
                      fg_color=color, text_color="#fff",
                      font=FONT_BTN, height=44,
                      command=self._confirm).pack(padx=24, fill="x")

    def _confirm(self):
        nouveau = self.entry.get().strip()
        nom = nouveau if nouveau else self.selected.get().strip()
        if not nom:
            self.entry.configure(border_color=CLR_BAD)
            return
        save_rouleur(nom)
        self.on_confirm(nom)
        self.destroy()


# ── Colonne entité ────────────────────────────────────────────────────────────

class EntityColumn(ctk.CTkFrame):
    def __init__(self, parent, label, color, is_velo=False, velo_num=None,
                 on_passage=None, on_changement=None, on_preparer=None, on_undo=None):
        super().__init__(parent, fg_color=CLR_CARD, corner_radius=12,
                         border_color=color, border_width=2)
        self.color = color
        self.is_velo = is_velo
        self.velo_num = velo_num
        self.on_passage = on_passage
        self.on_changement = on_changement
        self.on_preparer = on_preparer
        self.on_undo = on_undo
        self._frozen = False
        self._build(label)

    def _build(self, label):
        hdr = ctk.CTkFrame(self, fg_color=self.color, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=label, font=("Consolas", 13, "bold"),
                     text_color="#000" if self.color == CLR_PELOTON else "#fff"
                     ).pack(pady=7)

        if self.is_velo:
            rouleur_box = ctk.CTkFrame(self, fg_color="#0d1018", corner_radius=6)
            rouleur_box.pack(fill="x", padx=10, pady=(8, 2))
            self.lbl_rouleur = ctk.CTkLabel(
                rouleur_box, text="🚴  — En selle : —",
                font=FONT_SMALL, text_color=self.color)
            self.lbl_rouleur.pack(pady=(4, 1))
            self.lbl_prochain = ctk.CTkLabel(
                rouleur_box, text="", font=FONT_MICRO, text_color=CLR_PREP)
            self.lbl_prochain.pack(pady=(0, 4))

        ctk.CTkLabel(self, text="DEPUIS DERNIER PASSAGE",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(8, 0))
        self.lbl_elapsed = ctk.CTkLabel(self, text="--:--",
                                        font=("Consolas", 38, "bold"),
                                        text_color=self.color)
        self.lbl_elapsed.pack()

        ctk.CTkLabel(self, text="DERNIER TOUR",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(6, 0))
        self.lbl_dernier = ctk.CTkLabel(self, text="--:--",
                                        font=FONT_MED, text_color=CLR_TEXT)
        self.lbl_dernier.pack()
        self.lbl_speed = ctk.CTkLabel(self, text="",
                                      font=FONT_MICRO, text_color=CLR_MUTED)
        self.lbl_speed.pack()

        ctk.CTkLabel(self, text="5 DERNIERS TOURS",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(6, 0))
        recent_f = ctk.CTkFrame(self, fg_color="transparent")
        recent_f.pack()
        self.lbl_recents = []
        for _ in range(5):
            lbl = ctk.CTkLabel(recent_f, text="", font=FONT_MICRO, text_color=CLR_MUTED)
            lbl.pack(side="left", padx=3)
            self.lbl_recents.append(lbl)

        _sep(self)

        tours_row = ctk.CTkFrame(self, fg_color="transparent")
        tours_row.pack(fill="x", padx=16)
        tours_row.columnconfigure(0, weight=1)
        tours_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(tours_row, text="TOURS", font=FONT_MICRO,
                     text_color=CLR_MUTED).grid(row=0, column=0)
        ctk.CTkLabel(tours_row, text="KM", font=FONT_MICRO,
                     text_color=CLR_MUTED).grid(row=0, column=1)
        self.lbl_tours = ctk.CTkLabel(tours_row, text="0",
                                      font=("Consolas", 26, "bold"), text_color=CLR_TEXT)
        self.lbl_tours.grid(row=1, column=0)
        self.lbl_km = ctk.CTkLabel(tours_row, text="0.0 km",
                                   font=FONT_MED, text_color=CLR_TEXT)
        self.lbl_km.grid(row=1, column=1)

        if self.is_velo:
            _sep(self)
            ctk.CTkLabel(self, text="TOP 5  (hors tour de départ)",
                         font=FONT_MICRO, text_color=CLR_MUTED).pack()
            self.lbl_tops = []
            for i in range(5):
                lbl = ctk.CTkLabel(self, text="", font=FONT_MICRO, text_color=CLR_TEXT)
                lbl.pack()
                self.lbl_tops.append(lbl)

        if self.is_velo:
            _sep(self)
            ctk.CTkLabel(self, text="RETARD / AVANCE SUR PELOTON",
                         font=FONT_MICRO, text_color=CLR_MUTED).pack()
            self.lbl_retard = ctk.CTkLabel(self, text="--",
                                           font=FONT_MED, text_color=CLR_MUTED)
            self.lbl_retard.pack(pady=(0, 6))

        _sep(self)

        # ── Boutons ──
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=(4, 10))

        self.btn_passage = ctk.CTkButton(
            self.btn_frame, text="✔  PASSAGE",
            fg_color=self.color, hover_color=_darken(self.color),
            text_color="#000" if self.color == CLR_PELOTON else "#fff",
            font=FONT_BTN, height=48,
            command=self.on_passage
        )
        self.btn_passage.pack(fill="x", pady=(0, 4))

        if self.is_velo:
            sub = ctk.CTkFrame(self.btn_frame, fg_color="transparent")
            sub.pack(fill="x")
            sub.columnconfigure(0, weight=1)
            sub.columnconfigure(1, weight=1)

            ctk.CTkButton(
                sub, text="⏭ Préparer\nrouleur",
                fg_color=CLR_PREP, hover_color="#5b21b6",
                text_color="#fff", font=FONT_BTN_SM, height=44,
                command=self.on_preparer
            ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

            self.btn_chg = ctk.CTkButton(
                sub, text="🔄 Changement\n!",
                fg_color="#1a1a2e", border_color=self.color, border_width=1,
                text_color=self.color, font=FONT_BTN_SM, height=44,
                command=self.on_changement
            )
            self.btn_chg.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        ctk.CTkButton(
            self.btn_frame, text="↩ Annuler dernier passage",
            fg_color="transparent", border_color=CLR_BORDER, border_width=1,
            text_color=CLR_MUTED, font=("Consolas", 9), height=26,
            command=self.on_undo
        ).pack(fill="x", pady=(4, 0))

    # ── Mise à jour ──────────────────────────────────────────────────────────

    def update_data(self, state, ecart_sec=None, ecart_tours=0, approx_meme_tour=False):
        reload_km()
        elapsed = state.temps_depuis_dernier_passage
        self.lbl_elapsed.configure(text=format_duration(elapsed))

        dt = state.dernier_tour
        self.lbl_dernier.configure(text=format_duration(dt))
        self.lbl_speed.configure(text=state.vitesse_dernier_tour if dt else "")

        # 5 derniers tours avec tag départ
        recents = state.derniers_tours
        for i, lbl in enumerate(self.lbl_recents):
            if i < len(recents):
                info = recents[i]
                tag = "🚦" if info["is_depart"] else f"#{info['num']}"
                lbl.configure(text=f"{tag} {format_duration(info['time'])}")
            else:
                lbl.configure(text="")

        self.lbl_tours.configure(text=str(state.nb_tours))
        self.lbl_km.configure(text=f"{state.km_total:.1f} km")

        if self.is_velo:
            tops = state.meilleurs_tours
            for i, lbl in enumerate(self.lbl_tops):
                if i < len(tops):
                    medal = ["🥇", "🥈", "🥉", "  4.", "  5."][i]
                    lbl.configure(text=f"{medal}  {format_duration(tops[i])}")
                else:
                    lbl.configure(text="")

            self._update_retard(ecart_sec, ecart_tours, approx_meme_tour)

    def _update_retard(self, ecart_sec, ecart_tours, approx_meme_tour):
        """
        Affiche l'ecart velo/peloton.
          ecart_sec > 0  => retard  => rouge/orange
          ecart_sec < 0  => avance  => vert
          approx_meme_tour => |ecart| < 60s => afficher "(~ meme tour)"
        """
        if ecart_sec is None:
            self.lbl_retard.configure(text="-- En attente --", text_color=CLR_MUTED)
            return

        # Signe et couleur de base
        en_retard = ecart_sec > 0
        valeur_abs = abs(ecart_sec)

        if en_retard:
            signe = "+"
            clr = CLR_WARN if valeur_abs < 60 else CLR_BAD
        else:
            signe = "-"
            clr = CLR_GOOD

        # Partie temps
        if valeur_abs < 3:
            temps_str = "≈ 0s"
        else:
            temps_str = f"{signe}{format_duration(valeur_abs)}"

        # Partie tours
        if approx_meme_tour:
            tours_str = "  (≈ même tour)"
        elif ecart_tours == 0:
            tours_str = ""
        elif ecart_tours > 0:
            tours_str = f"  ({ecart_tours} tour{'s' if ecart_tours > 1 else ''} de retard)"
        else:
            tours_str = f"  ({abs(ecart_tours)} tour{'s' if abs(ecart_tours) > 1 else ''} d'avance)"

        self.lbl_retard.configure(text=f"{temps_str}{tours_str}", text_color=clr)

    def set_rouleur(self, nom):
        if self.is_velo:
            self.lbl_rouleur.configure(text=f"🚴  {nom}" if nom else "🚴  —")

    def set_prochain(self, nom):
        if self.is_velo:
            if nom:
                self.lbl_prochain.configure(text=f"⏭  Prochain : {nom}")
                self.btn_chg.configure(fg_color="#2a0a4a",
                                       border_color=CLR_PREP, text_color=CLR_PREP)
            else:
                self.lbl_prochain.configure(text="")
                self.btn_chg.configure(fg_color="#1a1a2e",
                                       border_color=self.color, text_color=self.color)

    def freeze(self):
        """Désactive tous les boutons (fin de course)."""
        self._frozen = True
        self.btn_passage.configure(state="disabled", fg_color=CLR_BORDER,
                                   text_color=CLR_MUTED)
        if self.is_velo:
            self.btn_chg.configure(state="disabled")
            for w in self.btn_frame.winfo_children():
                if isinstance(w, ctk.CTkButton):
                    w.configure(state="disabled")

    def unfreeze(self):
        self._frozen = False
        self.btn_passage.configure(state="normal", fg_color=self.color,
                                   text_color="#000" if self.color == CLR_PELOTON else "#fff")


# ── Écran de fin de course ─────────────────────────────────────────────────────

class EndScreen(ctk.CTkFrame):
    def __init__(self, parent, velo1, velo2, peloton, on_reset):
        super().__init__(parent, fg_color="#080a0e", corner_radius=0)
        self._build(velo1, velo2, peloton, on_reset)

    def _build(self, v1, v2, pel, on_reset):
        reload_km()

        ctk.CTkLabel(self, text="🏁  COURSE TERMINÉE  🏁",
                     font=("Consolas", 28, "bold"), text_color="#f59e0b"
                     ).pack(pady=(40, 8))

        # Résumé en 3 colonnes
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=40, pady=20)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        row.columnconfigure(2, weight=1)

        for col_idx, (entity, label, color) in enumerate([
            (v1, "VÉLO 1", CLR_ACCENT1),
            (pel, "PELOTON", CLR_PELOTON),
            (v2, "VÉLO 2", CLR_ACCENT2),
        ]):
            card = ctk.CTkFrame(row, fg_color=CLR_CARD, corner_radius=12,
                                border_color=color, border_width=2)
            card.grid(row=0, column=col_idx, sticky="nsew", padx=8)
            ctk.CTkLabel(card, text=label, font=("Consolas", 13, "bold"),
                         text_color=color).pack(pady=(12, 4))
            ctk.CTkLabel(card, text=str(entity.nb_tours),
                         font=("Consolas", 48, "bold"),
                         text_color=CLR_TEXT).pack()
            ctk.CTkLabel(card, text="tours",
                         font=FONT_SMALL, text_color=CLR_MUTED).pack()
            ctk.CTkLabel(card, text=f"{entity.km_total:.1f} km",
                         font=FONT_MED, text_color=CLR_TEXT).pack(pady=(4, 4))
            best = entity.meilleurs_tours
            if best:
                ctk.CTkLabel(card, text=f"Meilleur : {format_duration(best[0])}",
                             font=FONT_SMALL, text_color=CLR_GOOD).pack(pady=(0, 12))

        ctk.CTkLabel(self,
                     text="Consultez l'onglet 📊 Stats pour le détail complet.",
                     font=FONT_SMALL, text_color=CLR_MUTED).pack(pady=(20, 8))

        ctk.CTkButton(
            self, text="⚠  RÉINITIALISER ET RELANCER",
            fg_color=CLR_BAD, hover_color="#b91c1c",
            text_color="#fff", font=FONT_BTN, height=50, width=360,
            command=on_reset
        ).pack(pady=12)


# ── Onglet Live ───────────────────────────────────────────────────────────────

class LiveTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=CLR_BG)
        self.app = app
        self._race_ended = False
        self._end_screen = None

        self.peloton = EntityState("peloton")
        self.velo1   = VeloState(1)
        self.velo2   = VeloState(2)
        self.retard_calc = RetardCalculator()

        self.peloton.load_from_db()
        self.velo1.load_from_db()
        self.velo2.load_from_db()

        self._build()
        self._refresh_rouleurs()

    def _build(self):
        # Barre supérieure
        topbar = ctk.CTkFrame(self, fg_color="#08090d", corner_radius=0)
        topbar.pack(fill="x")
        ctk.CTkLabel(topbar, text="⚡  RELAI 24H",
                     font=("Consolas", 14, "bold"), text_color=CLR_TEXT
                     ).pack(side="left", padx=20, pady=8)
        self.lbl_clock = ctk.CTkLabel(topbar, text="00:00:00",
                                      font=("Consolas", 18, "bold"),
                                      text_color=CLR_ACCENT1)
        self.lbl_clock.pack(side="right", padx=20)

        # Bandeau temps restant
        countdown_bar = ctk.CTkFrame(self, fg_color="#0a0c10", corner_radius=0)
        countdown_bar.pack(fill="x")
        ctk.CTkLabel(countdown_bar, text="TEMPS RESTANT",
                     font=("Consolas", 11), text_color=CLR_MUTED).pack(pady=(6, 0))
        self.lbl_countdown = ctk.CTkLabel(countdown_bar, text="--:--:--",
                                          font=("Consolas", 52, "bold"),
                                          text_color="#ffffff")
        self.lbl_countdown.pack(pady=(0, 2))
        prog_f = ctk.CTkFrame(countdown_bar, fg_color="transparent")
        prog_f.pack(fill="x", padx=40, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(prog_f, height=8,
                                               fg_color=CLR_BORDER,
                                               progress_color=CLR_ACCENT1)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.lbl_race_elapsed = ctk.CTkLabel(countdown_bar, text="",
                                             font=FONT_MICRO, text_color=CLR_MUTED)
        self.lbl_race_elapsed.pack(pady=(0, 6))

        # Bouton reset toujours visible en haut à droite
        self.btn_reset_top = ctk.CTkButton(
            topbar, text="⚠ Reset course",
            fg_color="transparent", border_color=CLR_BAD, border_width=1,
            text_color=CLR_BAD, font=("Consolas", 10), height=28, width=120,
            command=self._confirm_reset
        )
        self.btn_reset_top.pack(side="right", padx=(0, 12))

        # Conteneur principal (colonnes ou écran de fin)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=12, pady=8)

        self._build_columns()

    def _build_columns(self):
        # Nettoyer le conteneur
        for w in self.main_container.winfo_children():
            w.destroy()

        self.cols_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.cols_frame.pack(fill="both", expand=True)
        self.cols_frame.columnconfigure(0, weight=1)
        self.cols_frame.columnconfigure(1, weight=1)
        self.cols_frame.columnconfigure(2, weight=1)

        self.col_velo1 = EntityColumn(
            self.cols_frame, "🚴  VÉLO 1", CLR_ACCENT1, is_velo=True, velo_num=1,
            on_passage=self._passage_velo1,
            on_changement=self._changement_velo1,
            on_preparer=self._preparer_velo1,
            on_undo=lambda: self._undo("velo1")
        )
        self.col_velo1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.col_peloton = EntityColumn(
            self.cols_frame, "🏁  PELOTON", CLR_PELOTON, is_velo=False,
            on_passage=self._passage_peloton,
            on_undo=lambda: self._undo("peloton")
        )
        self.col_peloton.grid(row=0, column=1, sticky="nsew", padx=3)

        self.col_velo2 = EntityColumn(
            self.cols_frame, "🚴  VÉLO 2", CLR_ACCENT2, is_velo=True, velo_num=2,
            on_passage=self._passage_velo2,
            on_changement=self._changement_velo2,
            on_preparer=self._preparer_velo2,
            on_undo=lambda: self._undo("velo2")
        )
        self.col_velo2.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    # ── Passage ──────────────────────────────────────────────────────────────

    def _passage_peloton(self):
        if self._race_ended:
            return
        ts = time.time()
        save_passage("peloton", ts)
        self.peloton.add_passage(ts)
        _flash(self.col_peloton, CLR_PELOTON)

    def _passage_velo1(self):
        if self._race_ended:
            return
        # Vérifier rouleur de départ
        if not self.velo1.rouleur_actuel:
            DialogDepartRouleur(self, 1, lambda nom: self._set_depart_rouleur(self.velo1, self.col_velo1, nom, self._passage_velo1))
            return
        ts = time.time()
        save_passage("velo1", ts)
        self.velo1.add_passage(ts)
        _flash(self.col_velo1, CLR_ACCENT1)

    def _passage_velo2(self):
        if self._race_ended:
            return
        if not self.velo2.rouleur_actuel:
            DialogDepartRouleur(self, 2, lambda nom: self._set_depart_rouleur(self.velo2, self.col_velo2, nom, self._passage_velo2))
            return
        ts = time.time()
        save_passage("velo2", ts)
        self.velo2.add_passage(ts)
        _flash(self.col_velo2, CLR_ACCENT2)

    def _set_depart_rouleur(self, velo, col, nom, callback_after):
        """Enregistre le rouleur de départ puis rappelle le passage."""
        ts = time.time()
        from database import save_changement, get_rouleurs as _gr
        rouleurs_dict = {r["nom"]: r["id"] for r in _gr()}
        entrant_id = rouleurs_dict.get(nom)
        if entrant_id:
            save_changement(velo.velo_num, None, entrant_id, ts)
        velo.rouleur_actuel = nom
        velo.changements = [{"timestamp": ts, "rouleur_entrant_nom": nom}]
        col.set_rouleur(nom)
        # Maintenant enregistrer le passage
        callback_after()

    # ── Préparer rouleur ─────────────────────────────────────────────────────

    def _preparer_velo1(self):
        DialogProchainRouleur(self, 1, self.velo1.prochain_rouleur,
                              lambda nom: self._on_prochain(self.velo1, self.col_velo1, nom))

    def _preparer_velo2(self):
        DialogProchainRouleur(self, 2, self.velo2.prochain_rouleur,
                              lambda nom: self._on_prochain(self.velo2, self.col_velo2, nom))

    def _on_prochain(self, velo, col, nom):
        velo.set_prochain(nom)
        col.set_prochain(nom)

    # ── Changement ───────────────────────────────────────────────────────────

    def _changement_velo1(self):
        self._do_changement(self.velo1, self.col_velo1)

    def _changement_velo2(self):
        self._do_changement(self.velo2, self.col_velo2)

    def _do_changement(self, velo, col):
        if not velo.prochain_rouleur:
            DialogProchainRouleur(self, velo.velo_num, None,
                                  lambda nom: self._finaliser_changement(velo, col, nom))
            return
        self._finaliser_changement(velo, col, velo.prochain_rouleur)

    def _finaliser_changement(self, velo, col, nom):
        from database import save_changement, get_rouleurs as _gr
        ts = time.time()
        rouleurs_dict = {r["nom"]: r["id"] for r in _gr()}
        sortant_id  = rouleurs_dict.get(velo.rouleur_actuel)
        entrant_id  = rouleurs_dict.get(nom)
        if entrant_id is None:
            save_rouleur(nom)
            entrant_id = {r["nom"]: r["id"] for r in _gr()}.get(nom)

        save_changement(velo.velo_num, sortant_id, entrant_id, ts)
        velo.confirmer_changement(ts)
        velo.rouleur_actuel = nom
        velo.prochain_rouleur = None
        col.set_rouleur(nom)
        col.set_prochain(None)

        save_passage(f"velo{velo.velo_num}", ts, "changement")
        velo.add_passage(ts)
        _flash(col, CLR_PREP)

    # ── Undo ─────────────────────────────────────────────────────────────────

    def _undo(self, entite):
        delete_last_passage(entite)
        if entite == "peloton":
            self.peloton.load_from_db()
        elif entite == "velo1":
            self.velo1.load_from_db()
        elif entite == "velo2":
            self.velo2.load_from_db()

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _confirm_reset(self):
        dialog = ctk.CTkInputDialog(
            text="Tapez  RESET  pour réinitialiser la course\n(les rouleurs sont conservés) :",
            title="⚠ Réinitialiser la course"
        )
        val = dialog.get_input()
        if val and val.strip().upper() == "RESET":
            self._do_reset()

    def _do_reset(self):
        reset_all()
        set_config("race_start", "")
        # Réinitialiser l'état en mémoire
        self._race_ended = False
        self.peloton = EntityState("peloton")
        self.velo1   = VeloState(1)
        self.velo2   = VeloState(2)
        self.peloton.load_from_db()
        self.velo1.load_from_db()
        self.velo2.load_from_db()
        # Reconstruire les colonnes (effacer l'écran de fin si présent)
        self._build_columns()
        self._race_ended = False
        # Réactiver l'onglet stats dans la fenêtre parent
        if hasattr(self.app, 'tabview'):
            try:
                self.app.tabview.tab("📊  Stats")  # juste vérifier qu'il existe
            except Exception:
                pass

    # ── Fin de course ─────────────────────────────────────────────────────────

    def _show_end_screen(self):
        if self._race_ended:
            return
        self._race_ended = True

        # Figer tous les boutons
        for col in [self.col_velo1, self.col_peloton, self.col_velo2]:
            try:
                col.freeze()
            except Exception:
                pass

        # Remplacer les colonnes par l'écran de fin
        for w in self.main_container.winfo_children():
            w.destroy()

        self._end_screen = EndScreen(
            self.main_container,
            self.velo1, self.velo2, self.peloton,
            on_reset=self._do_reset
        )
        self._end_screen.pack(fill="both", expand=True)

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            self._update_timers()
            if not self._race_ended:
                r1, e1, a1 = self.retard_calc.compute(self.peloton, self.velo1)
                r2, e2, a2 = self.retard_calc.compute(self.peloton, self.velo2)
                self.col_velo1.update_data(self.velo1, r1, e1, a1)
                self.col_peloton.update_data(self.peloton)
                self.col_velo2.update_data(self.velo2, r2, e2, a2)
        except Exception as e:
            print(f"[LiveTab.refresh] {e}")

    def _update_timers(self):
        import datetime
        now = datetime.datetime.now()
        self.lbl_clock.configure(text=now.strftime("%H:%M:%S"))

        start_str = get_config("race_start")
        duree_str = get_config("race_duree")
        if not start_str or not duree_str:
            return
        try:
            start_ts = float(start_str)
            duree    = float(duree_str)
            elapsed  = time.time() - start_ts
            restant  = max(0.0, duree - elapsed)
            progress = min(1.0, elapsed / duree)

            if restant <= 0 and not self._race_ended:
                self.after(0, self._show_end_screen)

            if restant < 3600:
                color = CLR_BAD
            elif restant < 7200:
                color = CLR_WARN
            else:
                color = "#ffffff"

            self.lbl_countdown.configure(
                text="00:00:00" if restant == 0 else format_duration(restant),
                text_color=color)
            self.progress_bar.set(progress)
            self.progress_bar.configure(
                progress_color=CLR_BAD if restant < 3600 else CLR_ACCENT1)
            h_e = int(elapsed // 3600)
            m_e = int((elapsed % 3600) // 60)
            self.lbl_race_elapsed.configure(text=f"Écoulé : {h_e}h{m_e:02d}min")
        except Exception:
            pass

    def _refresh_rouleurs(self):
        # Recharger l'état depuis la DB (les passages de départ ont pu être insérés)
        self.peloton.load_from_db()
        self.velo1.load_from_db()
        self.velo2.load_from_db()

        # Assigner les rouleurs de départ si pas encore en DB
        for velo, col, cfg_key in [
            (self.velo1, self.col_velo1, "depart_rouleur_v1"),
            (self.velo2, self.col_velo2, "depart_rouleur_v2"),
        ]:
            if not velo.rouleur_actuel:
                nom = get_config(cfg_key)
                if nom and nom.strip():
                    from database import save_changement, get_rouleurs as _gr
                    # Utiliser le timestamp du 1er passage (départ) comme référence
                    ts = velo.timestamps[0] if velo.timestamps else time.time()
                    save_rouleur(nom)
                    rouleurs_dict = {r["nom"]: r["id"] for r in _gr()}
                    entrant_id = rouleurs_dict.get(nom)
                    if entrant_id:
                        save_changement(velo.velo_num, None, entrant_id, ts)
                    velo.rouleur_actuel = nom
                    velo._load_changements()

        if self.velo1.rouleur_actuel:
            self.col_velo1.set_rouleur(self.velo1.rouleur_actuel)
        if self.velo2.rouleur_actuel:
            self.col_velo2.set_rouleur(self.velo2.rouleur_actuel)
        self.col_velo1.set_prochain(self.velo1.prochain_rouleur)
        self.col_velo2.set_prochain(self.velo2.prochain_rouleur)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sep(parent):
    ctk.CTkFrame(parent, fg_color=CLR_BORDER, height=1).pack(fill="x", padx=12, pady=6)


def _flash(col, color):
    col.configure(fg_color=color)
    col.after(250, lambda: col.configure(fg_color=CLR_CARD))


def _darken(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    f = 0.72
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"
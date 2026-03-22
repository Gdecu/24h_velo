import tkinter as tk
import customtkinter as ctk
import time

from models import (EntityState, VeloState, RetardCalculator,
                    format_duration, format_speed, reload_km, KM_PAR_TOUR,
                    is_race_finished)
from database import (save_passage, save_changement, save_rouleur,
                      get_rouleurs, get_config, delete_last_passage,
                      reset_all, set_config,
                      get_file_attente, add_to_file, remove_from_file,
                      pop_file_attente, move_file_entry)

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
CLR_QUEUE   = "#7c3aed"

FONT_MED    = ("Consolas", 18, "bold")
FONT_SMALL  = ("Consolas", 11)
FONT_MICRO  = ("Consolas", 10)
FONT_BTN    = ("Consolas", 12, "bold")
FONT_BTN_SM = ("Consolas", 10)


class DialogFileAttente(ctk.CTkToplevel):
    """File d'attente : le 1er = prochain rouleur."""
    def __init__(self, parent, velo_num, on_close=None):
        super().__init__(parent)
        self.velo_num = velo_num
        self.on_close = on_close
        self.color = CLR_ACCENT1 if velo_num == 1 else CLR_ACCENT2
        self.title(f"File d'attente — Vélo {velo_num}")
        self.geometry("520x820")
        self.minsize(480, 700)
        self.configure(fg_color=CLR_BG)
        self.resizable(True, True)
        self.grab_set(); self.lift(); self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self._refresh()

    def _build(self):
        # ── Titre ──
        ctk.CTkLabel(self, text=f"📋  FILE D'ATTENTE — VÉLO {self.velo_num}",
                     font=("Consolas", 14, "bold"), text_color=self.color
                     ).pack(pady=(16, 2))
        ctk.CTkLabel(self, text="Le 1er = prochain à monter. ↑/↓ pour réordonner, ✕ pour supprimer.",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(0, 8))

        # ── Section file actuelle ──
        hdr1 = ctk.CTkFrame(self, fg_color="#0a0c10")
        hdr1.pack(fill="x", padx=16, pady=(0, 0))
        ctk.CTkLabel(hdr1, text="  File actuelle", font=("Consolas", 11, "bold"),
                     text_color=self.color).pack(side="left", pady=6)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD,
                                                  corner_radius=0, height=200)
        self.list_frame.pack(fill="x", padx=16, pady=(0, 12))

        # ── Séparateur ──
        ctk.CTkFrame(self, fg_color=CLR_BORDER, height=1).pack(fill="x", padx=16, pady=(0, 8))

        # ── Section ajout ──
        hdr2 = ctk.CTkFrame(self, fg_color="#0a0c10")
        hdr2.pack(fill="x", padx=16, pady=(0, 0))
        ctk.CTkLabel(hdr2, text="  Ajouter à la file", font=("Consolas", 11, "bold"),
                     text_color=CLR_TEXT).pack(side="left", pady=6)

        # Liste scrollable des rouleurs (radio buttons)
        self.selected = tk.StringVar(value="")
        self.add_scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD,
                                                  corner_radius=0, height=180)
        self.add_scroll.pack(fill="x", padx=16, pady=(0, 8))

        # Champ texte + bouton ajouter — toujours visible, fixe en bas
        add_bar = ctk.CTkFrame(self, fg_color=CLR_CARD, corner_radius=8)
        add_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.entry_new = ctk.CTkEntry(
            add_bar, placeholder_text="Ou saisir un nouveau nom...",
            fg_color="#0d0f14", border_color=CLR_BORDER,
            text_color=CLR_TEXT, font=FONT_SMALL, height=36)
        self.entry_new.pack(side="left", expand=True, fill="x", padx=(10, 6), pady=8)
        ctk.CTkButton(
            add_bar, text="+ Ajouter",
            fg_color=self.color, hover_color=_darken(self.color),
            text_color="#fff" if self.color != CLR_PELOTON else "#000",
            font=("Consolas", 11, "bold"), width=110, height=36,
            command=self._add_selected
        ).pack(side="left", padx=(0, 10), pady=8)

        # ── Bouton fermer ──
        ctk.CTkButton(
            self, text="✓  Fermer",
            fg_color=CLR_GOOD, hover_color="#16a34a",
            text_color="#000", font=FONT_BTN, height=42,
            command=self._close
        ).pack(fill="x", padx=16, pady=(0, 14))

    def _refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        file = get_file_attente(self.velo_num)
        if not file:
            ctk.CTkLabel(self.list_frame, text="File vide — ajoutez des rouleurs ci-dessous.",
                         font=FONT_SMALL, text_color=CLR_MUTED).pack(pady=12)
        else:
            for idx, entry in enumerate(file):
                is_first = (idx == 0)
                row = ctk.CTkFrame(self.list_frame,
                                   fg_color="#1e1a2e" if is_first else "#141720",
                                   corner_radius=6)
                row.pack(fill="x", padx=4, pady=2)
                tag = "⏭ PROCHAIN" if is_first else f"  {idx+1}."
                ctk.CTkLabel(row, text=tag, font=("Consolas", 9, "bold"),
                             text_color=CLR_QUEUE if is_first else CLR_MUTED,
                             width=72).pack(side="left", padx=(8, 4))
                ctk.CTkLabel(row, text=entry["nom"], font=FONT_SMALL,
                             text_color=self.color if is_first else CLR_TEXT,
                             anchor="w").pack(side="left", expand=True, anchor="w")
                fid = entry["id"]
                for txt, cmd, bg, fg in [
                    ("↑", lambda i=fid: self._move(i, -1), CLR_BORDER, CLR_TEXT),
                    ("↓", lambda i=fid: self._move(i, +1), CLR_BORDER, CLR_TEXT),
                    ("✕", lambda i=fid: self._remove(i),   "#2a0a0a", CLR_BAD),
                ]:
                    ctk.CTkButton(row, text=txt, width=28, height=26,
                                  fg_color=bg, text_color=fg, font=FONT_MICRO,
                                  command=cmd).pack(side="left", padx=2)
                ctk.CTkFrame(row, width=4, fg_color="transparent").pack(side="left")

        for w in self.add_scroll.winfo_children():
            w.destroy()
        for r in get_rouleurs():
            ctk.CTkRadioButton(self.add_scroll, text=r["nom"],
                               variable=self.selected, value=r["nom"],
                               fg_color=self.color, text_color=CLR_TEXT,
                               font=FONT_SMALL).pack(anchor="w", padx=8, pady=2)

    def _add_selected(self):
        nouveau = self.entry_new.get().strip()
        nom = nouveau if nouveau else self.selected.get().strip()
        if not nom: return
        save_rouleur(nom)
        rid = {r["nom"]: r["id"] for r in get_rouleurs()}.get(nom)
        if rid:
            add_to_file(self.velo_num, rid)
        self.entry_new.delete(0, "end")
        self.selected.set("")
        self._refresh()

    def _remove(self, file_id):
        remove_from_file(file_id); self._refresh()

    def _move(self, file_id, direction):
        move_file_entry(file_id, direction, self.velo_num); self._refresh()

    def _close(self):
        if self.on_close: self.on_close()
        self.destroy()


class DialogDepartRouleur(ctk.CTkToplevel):
    def __init__(self, parent, velo_num, on_confirm):
        super().__init__(parent)
        self.on_confirm = on_confirm
        color = CLR_ACCENT1 if velo_num == 1 else CLR_ACCENT2
        self.title(f"Rouleur de départ — Vélo {velo_num}")
        self.geometry("420x480")
        self.configure(fg_color=CLR_BG)
        self.resizable(False, False)
        self.grab_set(); self.lift(); self.focus_force()
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(self, text=f"🚦  ROULEUR DE DÉPART — VÉLO {velo_num}",
                     font=("Consolas", 14, "bold"), text_color=color).pack(pady=(20, 8))
        self.selected = tk.StringVar(value="")
        scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_CARD,
                                        corner_radius=8, width=360, height=240)
        scroll.pack(padx=24, pady=(0, 10))
        for r in get_rouleurs():
            ctk.CTkRadioButton(scroll, text=r["nom"], variable=self.selected,
                               value=r["nom"], fg_color=color, text_color=CLR_TEXT,
                               font=FONT_SMALL).pack(anchor="w", padx=8, pady=3)
        self.entry = ctk.CTkEntry(self, placeholder_text="Ou nouveau rouleur",
                                  fg_color=CLR_CARD, border_color=CLR_BORDER,
                                  text_color=CLR_TEXT, font=FONT_SMALL, width=360)
        self.entry.pack(padx=24, pady=(0, 14))
        ctk.CTkButton(self, text="✓  CONFIRMER LE DÉPART", fg_color=color,
                      text_color="#fff", font=FONT_BTN, height=44,
                      command=self._confirm).pack(padx=24, fill="x")

    def _confirm(self):
        nouveau = self.entry.get().strip()
        nom = nouveau if nouveau else self.selected.get().strip()
        if not nom:
            self.entry.configure(border_color=CLR_BAD); return
        save_rouleur(nom)
        self.on_confirm(nom)
        self.destroy()


class EntityColumn(ctk.CTkFrame):
    def __init__(self, parent, label, color, is_velo=False, velo_num=None,
                 on_passage=None, on_changement=None, on_file=None, on_undo=None):
        super().__init__(parent, fg_color=CLR_CARD, corner_radius=12,
                         border_color=color, border_width=2)
        self.color = color
        self.is_velo = is_velo
        self.velo_num = velo_num
        self.on_passage = on_passage
        self.on_changement = on_changement
        self.on_file = on_file
        self.on_undo = on_undo
        self._build(label)

    def _build(self, label):
        hdr = ctk.CTkFrame(self, fg_color=self.color, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=label, font=("Consolas", 13, "bold"),
                     text_color="#000" if self.color == CLR_PELOTON else "#fff").pack(pady=7)

        if self.is_velo:
            rbox = ctk.CTkFrame(self, fg_color="#0d1018", corner_radius=6)
            rbox.pack(fill="x", padx=10, pady=(8, 2))
            self.lbl_rouleur = ctk.CTkLabel(rbox, text="🚴  — En selle : —",
                                             font=FONT_SMALL, text_color=self.color)
            self.lbl_rouleur.pack(pady=(4, 1))
            self.lbl_queue = ctk.CTkLabel(rbox, text="", font=FONT_MICRO, text_color=CLR_QUEUE)
            self.lbl_queue.pack(pady=(0, 4))

        ctk.CTkLabel(self, text="DEPUIS DERNIER PASSAGE",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(8, 0))
        self.lbl_elapsed = ctk.CTkLabel(self, text="--:--",
                                        font=("Consolas", 38, "bold"), text_color=self.color)
        self.lbl_elapsed.pack()

        ctk.CTkLabel(self, text="DERNIER TOUR",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(6, 0))
        self.lbl_dernier = ctk.CTkLabel(self, text="--:--", font=FONT_MED, text_color=CLR_TEXT)
        self.lbl_dernier.pack()
        self.lbl_speed = ctk.CTkLabel(self, text="", font=FONT_MICRO, text_color=CLR_MUTED)
        self.lbl_speed.pack()

        ctk.CTkLabel(self, text="5 DERNIERS TOURS",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(6, 0))
        rf = ctk.CTkFrame(self, fg_color="transparent")
        rf.pack()
        self.lbl_recents = []
        for _ in range(5):
            lbl = ctk.CTkLabel(rf, text="", font=FONT_MICRO, text_color=CLR_MUTED)
            lbl.pack(side="left", padx=3)
            self.lbl_recents.append(lbl)

        _sep(self)

        tr = ctk.CTkFrame(self, fg_color="transparent")
        tr.pack(fill="x", padx=16)
        tr.columnconfigure(0, weight=1); tr.columnconfigure(1, weight=1)
        ctk.CTkLabel(tr, text="TOURS", font=FONT_MICRO, text_color=CLR_MUTED).grid(row=0, column=0)
        ctk.CTkLabel(tr, text="KM", font=FONT_MICRO, text_color=CLR_MUTED).grid(row=0, column=1)
        self.lbl_tours = ctk.CTkLabel(tr, text="0", font=("Consolas", 26, "bold"),
                                       text_color=CLR_TEXT)
        self.lbl_tours.grid(row=1, column=0)
        self.lbl_km = ctk.CTkLabel(tr, text="0.0 km", font=FONT_MED, text_color=CLR_TEXT)
        self.lbl_km.grid(row=1, column=1)

        if self.is_velo:
            _sep(self)
            ctk.CTkLabel(self, text="TOP 5  (hors tour de départ)",
                         font=FONT_MICRO, text_color=CLR_MUTED).pack()
            self.lbl_tops = []
            for _ in range(5):
                lbl = ctk.CTkLabel(self, text="", font=FONT_MICRO, text_color=CLR_TEXT)
                lbl.pack()
                self.lbl_tops.append(lbl)

        if self.is_velo:
            _sep(self)
            ctk.CTkLabel(self, text="ÉCART / PELOTON",
                         font=FONT_MICRO, text_color=CLR_MUTED).pack()
            self.lbl_ecart = ctk.CTkLabel(self, text="--", font=FONT_MED, text_color=CLR_MUTED)
            self.lbl_ecart.pack(pady=(0, 6))

        _sep(self)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=(4, 10))

        self.btn_passage = ctk.CTkButton(
            self.btn_frame, text="✔  PASSAGE",
            fg_color=self.color, hover_color=_darken(self.color),
            text_color="#000" if self.color == CLR_PELOTON else "#fff",
            font=FONT_BTN, height=48, command=self.on_passage)
        self.btn_passage.pack(fill="x", pady=(0, 4))

        if self.is_velo:
            sub = ctk.CTkFrame(self.btn_frame, fg_color="transparent")
            sub.pack(fill="x")
            sub.columnconfigure(0, weight=1); sub.columnconfigure(1, weight=1)

            ctk.CTkButton(sub, text="📋 File d'attente",
                          fg_color=CLR_QUEUE, hover_color="#5b21b6",
                          text_color="#fff", font=FONT_BTN_SM, height=44,
                          command=self.on_file
                          ).grid(row=0, column=0, sticky="ew", padx=(0, 3))

            self.btn_chg = ctk.CTkButton(sub, text="🔄 Changement !",
                                          fg_color="#1a1a2e",
                                          border_color=self.color, border_width=1,
                                          text_color=self.color, font=FONT_BTN_SM, height=44,
                                          command=self.on_changement)
            self.btn_chg.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        ctk.CTkButton(self.btn_frame, text="↩ Annuler dernier passage",
                      fg_color="transparent", border_color=CLR_BORDER, border_width=1,
                      text_color=CLR_MUTED, font=("Consolas", 9), height=26,
                      command=self.on_undo).pack(fill="x", pady=(4, 0))

    def update_data(self, state, ecart_sec=None):
        reload_km()
        self.lbl_elapsed.configure(text=format_duration(state.temps_depuis_dernier_passage))
        dt = state.dernier_tour
        self.lbl_dernier.configure(text=format_duration(dt))
        self.lbl_speed.configure(text=state.vitesse_dernier_tour if dt else "")
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
            medals = ["🥇", "🥈", "🥉", "  4.", "  5."]
            for i, lbl in enumerate(self.lbl_tops):
                lbl.configure(text=f"{medals[i]}  {format_duration(tops[i])}" if i < len(tops) else "")
            self._update_ecart(ecart_sec)

    def _update_ecart(self, ecart_sec):
        if ecart_sec is None:
            self.lbl_ecart.configure(text="-- En attente --", text_color=CLR_MUTED)
            return
        v = abs(ecart_sec)
        if v < 3:
            self.lbl_ecart.configure(text="≈ En contact", text_color=CLR_GOOD)
            return
        en_retard = ecart_sec >= 0
        signe = "+" if en_retard else "-"
        clr = (CLR_WARN if v < 60 else CLR_BAD) if en_retard else CLR_GOOD
        self.lbl_ecart.configure(text=f"{signe}{format_duration(v)}", text_color=clr)

    def set_rouleur(self, nom):
        if self.is_velo:
            self.lbl_rouleur.configure(text=f"🚴  {nom}" if nom else "🚴  —")

    def set_queue_preview(self, file):
        if not self.is_velo: return
        if not file:
            self.lbl_queue.configure(text="")
            return
        txt = f"⏭ {file[0]['nom']}"
        if len(file) > 1:
            txt += "  →  " + "  →  ".join(e["nom"] for e in file[1:3])
        if len(file) > 3:
            txt += f"  (+{len(file)-3})"
        self.lbl_queue.configure(text=txt)

    def highlight_changement_ready(self, ready: bool):
        if not self.is_velo: return
        if ready:
            self.btn_chg.configure(fg_color="#2a0a4a",
                                   border_color=CLR_QUEUE, text_color=CLR_QUEUE)
        else:
            self.btn_chg.configure(fg_color="#1a1a2e",
                                   border_color=self.color, text_color=self.color)

    def freeze(self):
        self.btn_passage.configure(state="disabled", fg_color=CLR_BORDER, text_color=CLR_MUTED)
        if self.is_velo:
            for w in self.btn_frame.winfo_children():
                if isinstance(w, ctk.CTkButton):
                    w.configure(state="disabled")
            if hasattr(self, "btn_chg"):
                self.btn_chg.configure(state="disabled")


class EndScreen(ctk.CTkFrame):
    def __init__(self, parent, velo1, velo2, peloton, on_reset):
        super().__init__(parent, fg_color="#080a0e", corner_radius=0)
        reload_km()
        ctk.CTkLabel(self, text="🏁  COURSE TERMINÉE  🏁",
                     font=("Consolas", 28, "bold"), text_color=CLR_WARN).pack(pady=(40, 8))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=40, pady=20)
        row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=1); row.columnconfigure(2, weight=1)
        for ci, (e, lbl, clr) in enumerate([
            (velo1, "VÉLO 1", CLR_ACCENT1), (peloton, "PELOTON", CLR_PELOTON), (velo2, "VÉLO 2", CLR_ACCENT2)
        ]):
            card = ctk.CTkFrame(row, fg_color=CLR_CARD, corner_radius=12,
                                border_color=clr, border_width=2)
            card.grid(row=0, column=ci, sticky="nsew", padx=8)
            ctk.CTkLabel(card, text=lbl, font=("Consolas", 13, "bold"), text_color=clr).pack(pady=(12, 4))
            ctk.CTkLabel(card, text=str(e.nb_tours), font=("Consolas", 48, "bold"),
                         text_color=CLR_TEXT).pack()
            ctk.CTkLabel(card, text="tours", font=FONT_SMALL, text_color=CLR_MUTED).pack()
            ctk.CTkLabel(card, text=f"{e.km_total:.1f} km", font=FONT_MED, text_color=CLR_TEXT).pack(pady=4)
            best = e.meilleurs_tours
            if best:
                ctk.CTkLabel(card, text=f"Meilleur : {format_duration(best[0])}",
                             font=FONT_SMALL, text_color=CLR_GOOD).pack(pady=(0, 12))
        ctk.CTkLabel(self, text="Consultez l'onglet 📊 Stats pour le détail complet.",
                     font=FONT_SMALL, text_color=CLR_MUTED).pack(pady=(20, 8))
        ctk.CTkButton(self, text="⚠  RÉINITIALISER ET RELANCER",
                      fg_color=CLR_BAD, hover_color="#b91c1c", text_color="#fff",
                      font=FONT_BTN, height=50, width=360, command=on_reset).pack(pady=12)


class LiveTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=CLR_BG)
        self.app = app
        self._race_ended = False
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
        topbar = ctk.CTkFrame(self, fg_color="#08090d", corner_radius=0)
        topbar.pack(fill="x")
        ctk.CTkLabel(topbar, text="⚡  RELAI 24H",
                     font=("Consolas", 14, "bold"), text_color=CLR_TEXT).pack(side="left", padx=20, pady=8)
        self.lbl_clock = ctk.CTkLabel(topbar, text="00:00:00",
                                      font=("Consolas", 18, "bold"), text_color=CLR_ACCENT1)
        self.lbl_clock.pack(side="right", padx=20)
        ctk.CTkButton(topbar, text="⚠ Reset course",
                      fg_color="transparent", border_color=CLR_BAD, border_width=1,
                      text_color=CLR_BAD, font=("Consolas", 10), height=28, width=120,
                      command=self._confirm_reset).pack(side="right", padx=(0, 12))

        cb = ctk.CTkFrame(self, fg_color="#0a0c10", corner_radius=0)
        cb.pack(fill="x")
        ctk.CTkLabel(cb, text="TEMPS RESTANT", font=("Consolas", 11),
                     text_color=CLR_MUTED).pack(pady=(6, 0))
        self.lbl_countdown = ctk.CTkLabel(cb, text="--:--:--",
                                          font=("Consolas", 52, "bold"), text_color="#ffffff")
        self.lbl_countdown.pack(pady=(0, 2))
        pf = ctk.CTkFrame(cb, fg_color="transparent")
        pf.pack(fill="x", padx=40, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(pf, height=8,
                                               fg_color=CLR_BORDER, progress_color=CLR_ACCENT1)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.lbl_race_elapsed = ctk.CTkLabel(cb, text="", font=FONT_MICRO, text_color=CLR_MUTED)
        self.lbl_race_elapsed.pack(pady=(0, 6))

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=12, pady=8)
        self._build_columns()

    def _build_columns(self):
        for w in self.main_container.winfo_children():
            w.destroy()
        cf = ctk.CTkFrame(self.main_container, fg_color="transparent")
        cf.pack(fill="both", expand=True)
        cf.columnconfigure(0, weight=1); cf.columnconfigure(1, weight=1); cf.columnconfigure(2, weight=1)

        self.col_velo1 = EntityColumn(
            cf, "🚴  VÉLO 1", CLR_ACCENT1, is_velo=True, velo_num=1,
            on_passage=self._passage_velo1, on_changement=self._changement_velo1,
            on_file=lambda: self._open_file(1), on_undo=lambda: self._undo("velo1"))
        self.col_velo1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.col_peloton = EntityColumn(
            cf, "🏁  PELOTON", CLR_PELOTON,
            on_passage=self._passage_peloton, on_undo=lambda: self._undo("peloton"))
        self.col_peloton.grid(row=0, column=1, sticky="nsew", padx=3)

        self.col_velo2 = EntityColumn(
            cf, "🚴  VÉLO 2", CLR_ACCENT2, is_velo=True, velo_num=2,
            on_passage=self._passage_velo2, on_changement=self._changement_velo2,
            on_file=lambda: self._open_file(2), on_undo=lambda: self._undo("velo2"))
        self.col_velo2.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

    def _open_file(self, velo_num):
        DialogFileAttente(self, velo_num,
                          on_close=lambda: self._refresh_queue_preview(velo_num))

    def _refresh_queue_preview(self, velo_num):
        col = self.col_velo1 if velo_num == 1 else self.col_velo2
        file = get_file_attente(velo_num)
        col.set_queue_preview(file)
        col.highlight_changement_ready(len(file) > 0)

    def _passage_peloton(self):
        if self._race_ended: return
        ts = time.time()
        save_passage("peloton", ts); self.peloton.add_passage(ts)
        _flash(self.col_peloton, CLR_PELOTON)

    def _passage_velo1(self):
        if self._race_ended: return
        if not self.velo1.rouleur_actuel:
            DialogDepartRouleur(self, 1,
                lambda nom: self._set_depart_rouleur(self.velo1, self.col_velo1, nom, self._passage_velo1))
            return
        ts = time.time()
        save_passage("velo1", ts); self.velo1.add_passage(ts)
        _flash(self.col_velo1, CLR_ACCENT1)

    def _passage_velo2(self):
        if self._race_ended: return
        if not self.velo2.rouleur_actuel:
            DialogDepartRouleur(self, 2,
                lambda nom: self._set_depart_rouleur(self.velo2, self.col_velo2, nom, self._passage_velo2))
            return
        ts = time.time()
        save_passage("velo2", ts); self.velo2.add_passage(ts)
        _flash(self.col_velo2, CLR_ACCENT2)

    def _set_depart_rouleur(self, velo, col, nom, cb):
        ts = time.time()
        save_rouleur(nom)
        rid = {r["nom"]: r["id"] for r in get_rouleurs()}.get(nom)
        if rid: save_changement(velo.velo_num, None, rid, ts)
        velo.rouleur_actuel = nom
        velo.changements = [{"timestamp": ts, "rouleur_entrant_nom": nom}]
        col.set_rouleur(nom)
        cb()

    def _changement_velo1(self): self._do_changement(self.velo1, self.col_velo1)
    def _changement_velo2(self): self._do_changement(self.velo2, self.col_velo2)

    def _do_changement(self, velo, col):
        nom = pop_file_attente(velo.velo_num)
        if not nom:
            DialogFileAttente(self, velo.velo_num,
                              on_close=lambda: self._after_file_edit(velo, col))
            return
        self._finaliser_changement(velo, col, nom)
        self._refresh_queue_preview(velo.velo_num)

    def _after_file_edit(self, velo, col):
        self._refresh_queue_preview(velo.velo_num)
        nom = pop_file_attente(velo.velo_num)
        if nom:
            self._finaliser_changement(velo, col, nom)
            self._refresh_queue_preview(velo.velo_num)

    def _finaliser_changement(self, velo, col, nom):
        ts = time.time()
        rd = {r["nom"]: r["id"] for r in get_rouleurs()}
        sortant_id = rd.get(velo.rouleur_actuel)
        entrant_id = rd.get(nom)
        if entrant_id is None:
            save_rouleur(nom)
            entrant_id = {r["nom"]: r["id"] for r in get_rouleurs()}.get(nom)
        save_changement(velo.velo_num, sortant_id, entrant_id, ts)
        velo.rouleur_actuel = nom
        velo.prochain_rouleur = None
        col.set_rouleur(nom)
        save_passage(f"velo{velo.velo_num}", ts, "changement")
        velo.add_passage(ts)
        _flash(col, CLR_QUEUE)

    def _undo(self, entite):
        delete_last_passage(entite)
        if entite == "peloton": self.peloton.load_from_db()
        elif entite == "velo1": self.velo1.load_from_db()
        elif entite == "velo2": self.velo2.load_from_db()

    def _confirm_reset(self):
        d = ctk.CTkInputDialog(text="Tapez  RESET  pour réinitialiser :", title="⚠ Reset")
        val = d.get_input()
        if val and val.strip().upper() == "RESET": self._do_reset()

    def _do_reset(self):
        reset_all(); set_config("race_start", "")
        self._race_ended = False
        self.peloton = EntityState("peloton")
        self.velo1 = VeloState(1); self.velo2 = VeloState(2)
        self.peloton.load_from_db(); self.velo1.load_from_db(); self.velo2.load_from_db()
        self._build_columns()

    def _show_end_screen(self):
        if self._race_ended: return
        self._race_ended = True
        for col in [self.col_velo1, self.col_peloton, self.col_velo2]:
            try: col.freeze()
            except Exception: pass
        for w in self.main_container.winfo_children():
            w.destroy()
        EndScreen(self.main_container, self.velo1, self.velo2, self.peloton,
                  on_reset=self._do_reset).pack(fill="both", expand=True)

    def refresh(self):
        try:
            self._update_timers()
            if not self._race_ended:
                e1 = self.retard_calc.compute(self.peloton, self.velo1)
                e2 = self.retard_calc.compute(self.peloton, self.velo2)
                self.col_velo1.update_data(self.velo1, e1)
                self.col_peloton.update_data(self.peloton)
                self.col_velo2.update_data(self.velo2, e2)
        except Exception as ex:
            print(f"[LiveTab.refresh] {ex}")

    def _update_timers(self):
        import datetime
        self.lbl_clock.configure(text=datetime.datetime.now().strftime("%H:%M:%S"))
        s = get_config("race_start"); d = get_config("race_duree")
        if not s or not d: return
        try:
            elapsed = time.time() - float(s)
            duree = float(d)
            restant = max(0.0, duree - elapsed)
            if restant <= 0 and not self._race_ended:
                self.after(0, self._show_end_screen)
            clr = CLR_BAD if restant < 3600 else (CLR_WARN if restant < 7200 else "#ffffff")
            self.lbl_countdown.configure(
                text="00:00:00" if restant == 0 else format_duration(restant), text_color=clr)
            self.progress_bar.set(min(1.0, elapsed / duree))
            self.progress_bar.configure(progress_color=CLR_BAD if restant < 3600 else CLR_ACCENT1)
            self.lbl_race_elapsed.configure(
                text=f"Écoulé : {int(elapsed//3600)}h{int((elapsed%3600)//60):02d}min")
        except Exception: pass

    def _refresh_rouleurs(self):
        self.peloton.load_from_db(); self.velo1.load_from_db(); self.velo2.load_from_db()
        for velo, col, cfg in [
            (self.velo1, self.col_velo1, "depart_rouleur_v1"),
            (self.velo2, self.col_velo2, "depart_rouleur_v2"),
        ]:
            if not velo.rouleur_actuel:
                nom = get_config(cfg)
                if nom and nom.strip():
                    ts = velo.timestamps[0] if velo.timestamps else time.time()
                    save_rouleur(nom)
                    rid = {r["nom"]: r["id"] for r in get_rouleurs()}.get(nom)
                    if rid: save_changement(velo.velo_num, None, rid, ts)
                    velo.rouleur_actuel = nom
                    velo._load_changements()
        if self.velo1.rouleur_actuel: self.col_velo1.set_rouleur(self.velo1.rouleur_actuel)
        if self.velo2.rouleur_actuel: self.col_velo2.set_rouleur(self.velo2.rouleur_actuel)
        self._refresh_queue_preview(1)
        self._refresh_queue_preview(2)


def _sep(parent):
    ctk.CTkFrame(parent, fg_color=CLR_BORDER, height=1).pack(fill="x", padx=12, pady=6)

def _flash(col, color):
    col.configure(fg_color=color)
    col.after(250, lambda: col.configure(fg_color=CLR_CARD))

def _darken(h):
    r, g, b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return f"#{int(r*.72):02x}{int(g*.72):02x}{int(b*.72):02x}"
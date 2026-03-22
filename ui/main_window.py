import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (init_db, get_config, set_config, get_rouleurs,
                      save_rouleur, reset_all, import_rouleurs_csv)
from timer_engine import TimerEngine
from ui.tab_live import LiveTab
from ui.tab_stats import StatsTab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CLR_BG      = "#0d0f14"
CLR_CARD    = "#141720"
CLR_BORDER  = "#1e2233"
CLR_TEXT    = "#e8eaf0"
CLR_MUTED   = "#6b7280"
CLR_ACCENT  = "#00d4ff"
CLR_GOOD    = "#22c55e"
CLR_BAD     = "#ef4444"
FONT_SMALL  = ("Consolas", 11)
FONT_MICRO  = ("Consolas", 10)
FONT_BTN    = ("Consolas", 12, "bold")
FONT_TITLE  = ("Consolas", 15, "bold")

PRESETS = {
    "24h Vélo du Bois de la Cambre": {"km": "2.62", "duree_h": "24", "duree_m": "0"},
    "12h Vélo":                       {"km": "2.62", "duree_h": "12", "duree_m": "0"},
    "Personnalisé":                   None,
}


class SetupDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_start):
        super().__init__(parent)
        self.on_start = on_start
        self.title("Configuration — Relai 24H")
        self.geometry("560x820")
        self.minsize(540, 500)
        self.configure(fg_color=CLR_BG)
        self.resizable(True, True)
        self.grab_set(); self.lift(); self.focus_force()
        self._build()
        self._load_current()

    def _build(self):
        # Scrollable wrapper — tout le contenu est scrollable sur petit écran
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=CLR_BG, corner_radius=0)
        self._scroll.pack(fill="both", expand=True)
        p = self._scroll

        ctk.CTkLabel(p, text="⚡  CONFIGURATION DE LA COURSE",
                     font=FONT_TITLE, text_color=CLR_ACCENT).pack(pady=(20, 2))
        ctk.CTkLabel(p, text="Paramètres et liste des rouleurs",
                     font=FONT_MICRO, text_color=CLR_MUTED).pack(pady=(0, 14))

        # Preset
        preset_f = ctk.CTkFrame(p, fg_color=CLR_CARD, corner_radius=8)
        preset_f.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkLabel(preset_f, text="Preset", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(side="left", padx=12, pady=10)
        self.preset_var = tk.StringVar(value="24h Vélo du Bois de la Cambre")
        ctk.CTkOptionMenu(preset_f, variable=self.preset_var,
                          values=list(PRESETS.keys()),
                          fg_color=CLR_BG, button_color=CLR_BORDER,
                          text_color=CLR_TEXT, font=FONT_SMALL,
                          command=self._apply_preset
                          ).pack(side="right", padx=12, pady=8)

        self._field_row(p, "Nom de la course", "entry_name")
        self._field_row(p, "Distance par tour (km)", "entry_km")

        duree_f = ctk.CTkFrame(p, fg_color=CLR_CARD, corner_radius=8)
        duree_f.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkLabel(duree_f, text="Durée de la course",
                     font=FONT_SMALL, text_color=CLR_TEXT).pack(side="left", padx=12, pady=10)
        sub = ctk.CTkFrame(duree_f, fg_color="transparent")
        sub.pack(side="right", padx=12, pady=8)
        self.entry_h = ctk.CTkEntry(sub, width=55, placeholder_text="HH",
                                    fg_color=CLR_BG, border_color=CLR_BORDER,
                                    text_color=CLR_TEXT, font=FONT_SMALL)
        self.entry_h.pack(side="left")
        ctk.CTkLabel(sub, text="h", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(side="left", padx=4)
        self.entry_min = ctk.CTkEntry(sub, width=55, placeholder_text="MM",
                                      fg_color=CLR_BG, border_color=CLR_BORDER,
                                      text_color=CLR_TEXT, font=FONT_SMALL)
        self.entry_min.pack(side="left")
        ctk.CTkLabel(sub, text="min", font=FONT_SMALL,
                     text_color=CLR_MUTED).pack(side="left", padx=4)

        # Rouleurs
        roul_hdr = ctk.CTkFrame(p, fg_color="transparent")
        roul_hdr.pack(fill="x", padx=24, pady=(10, 2))
        ctk.CTkLabel(roul_hdr, text="👥  ROULEURS",
                     font=("Consolas", 12, "bold"), text_color=CLR_TEXT).pack(side="left")
        ctk.CTkButton(roul_hdr, text="📂 Importer CSV",
                      fg_color=CLR_CARD, border_color=CLR_ACCENT, border_width=1,
                      text_color=CLR_ACCENT, font=FONT_MICRO, height=28, width=130,
                      command=self._import_csv).pack(side="right")

        add_f = ctk.CTkFrame(p, fg_color=CLR_CARD, corner_radius=8)
        add_f.pack(fill="x", padx=24, pady=(0, 4))
        self.entry_rouleur = ctk.CTkEntry(add_f, placeholder_text="Prénom Nom",
                                          fg_color=CLR_BG, border_color=CLR_BORDER,
                                          text_color=CLR_TEXT, font=FONT_SMALL, width=280)
        self.entry_rouleur.pack(side="left", padx=(12, 8), pady=8)
        ctk.CTkButton(add_f, text="+ Ajouter",
                      fg_color=CLR_BG, border_color=CLR_ACCENT, border_width=1,
                      text_color=CLR_ACCENT, font=FONT_SMALL, height=30, width=100,
                      command=self._add_rouleur).pack(side="left")

        self.rouleur_scroll = ctk.CTkScrollableFrame(p, fg_color=CLR_CARD,
                                                     corner_radius=8, height=110)
        self.rouleur_scroll.pack(fill="x", padx=24, pady=(0, 14))
        self.lbl_rouleurs_list = ctk.CTkLabel(self.rouleur_scroll, text="",
                                              font=FONT_SMALL, text_color=CLR_TEXT,
                                              justify="left", anchor="w")
        self.lbl_rouleurs_list.pack(anchor="w", padx=8, pady=6)

        # ── Rouleurs de départ ──
        ctk.CTkLabel(p, text="🚦  ROULEURS DE DÉPART  (obligatoire)",
                     font=("Consolas", 12, "bold"), text_color="#f59e0b"
                     ).pack(anchor="w", padx=24, pady=(8, 2))

        depart_f = ctk.CTkFrame(p, fg_color=CLR_CARD, corner_radius=8)
        depart_f.pack(fill="x", padx=24, pady=(0, 14))
        depart_f.columnconfigure(0, weight=1)
        depart_f.columnconfigure(1, weight=1)

        for col_idx, (velo_num, color, attr) in enumerate([
            (1, "#00d4ff", "menu_depart_v1"),
            (2, "#ff6b35", "menu_depart_v2"),
        ]):
            cell = ctk.CTkFrame(depart_f, fg_color="transparent")
            cell.grid(row=0, column=col_idx, padx=10, pady=10, sticky="ew")
            ctk.CTkLabel(cell, text=f"Vélo {velo_num}",
                         font=FONT_SMALL, text_color=color).pack(anchor="w")
            var = tk.StringVar(value="— Sélectionner —")
            setattr(self, f"depart_var_v{velo_num}", var)
            menu = ctk.CTkOptionMenu(
                cell, variable=var,
                values=["— Sélectionner —"],
                fg_color=CLR_BG, button_color=color,
                text_color=CLR_TEXT, font=FONT_SMALL, width=200,
                command=lambda _: self._check_start_ready()
            )
            menu.pack(fill="x", pady=(4, 0))
            setattr(self, attr, menu)

        ctk.CTkButton(p, text="▶  DÉMARRER LA COURSE",
                      fg_color=CLR_GOOD, hover_color="#16a34a",
                      text_color="#000", font=FONT_BTN, height=50,
                      command=self._start).pack(fill="x", padx=24, pady=(0, 4))
        ctk.CTkButton(p, text="▷  Continuer (course déjà démarrée)",
                      fg_color=CLR_CARD, border_color=CLR_ACCENT, border_width=1,
                      text_color=CLR_ACCENT, font=FONT_SMALL, height=36,
                      command=self._continue).pack(fill="x", padx=24, pady=(0, 4))
        ctk.CTkButton(p, text="⚠  Réinitialiser la course",
                      fg_color="transparent", border_color=CLR_BAD, border_width=1,
                      text_color=CLR_BAD, font=FONT_SMALL, height=32,
                      command=self._reset).pack(fill="x", padx=24, pady=(0, 12))

    def _field_row(self, parent, label, attr):
        f = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=8)
        f.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkLabel(f, text=label, font=FONT_SMALL, text_color=CLR_TEXT
                     ).pack(side="left", padx=12, pady=10)
        entry = ctk.CTkEntry(f, width=160, fg_color=CLR_BG,
                             border_color=CLR_BORDER, text_color=CLR_TEXT, font=FONT_SMALL)
        entry.pack(side="right", padx=12, pady=8)
        setattr(self, attr, entry)

    def _apply_preset(self, choice):
        preset = PRESETS.get(choice)
        if not preset:
            return
        self.entry_km.delete(0, "end")
        self.entry_km.insert(0, preset["km"])
        self.entry_h.delete(0, "end")
        self.entry_h.insert(0, preset["duree_h"])
        self.entry_min.delete(0, "end")
        self.entry_min.insert(0, preset.get("duree_m", "0"))
        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, choice)

    def _load_current(self):
        self._apply_preset("24h Vélo du Bois de la Cambre")
        saved_km    = get_config("km_par_tour")
        saved_duree = get_config("race_duree")
        saved_name  = get_config("race_name")
        if saved_km:
            self.entry_km.delete(0, "end")
            self.entry_km.insert(0, saved_km)
        if saved_duree:
            try:
                total_s = int(float(saved_duree))
                self.entry_h.delete(0, "end")
                self.entry_h.insert(0, str(total_s // 3600))
                self.entry_min.delete(0, "end")
                self.entry_min.insert(0, str((total_s % 3600) // 60))
            except Exception:
                pass
        if saved_name:
            self.entry_name.delete(0, "end")
            self.entry_name.insert(0, saved_name)
        self._refresh_rouleur_list()

    def _add_rouleur(self):
        nom = self.entry_rouleur.get().strip()
        if nom:
            save_rouleur(nom)
            self.entry_rouleur.delete(0, "end")
            self._refresh_rouleur_list()

    def _import_csv(self):
        path = filedialog.askopenfilename(
            title="Importer les rouleurs",
            filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        if path:
            n = import_rouleurs_csv(path)
            self._refresh_rouleur_list()
            messagebox.showinfo("Import CSV", f"{n} rouleur(s) importé(s).")

    def _refresh_rouleur_list(self):
        rouleurs = get_rouleurs()
        txt = "\n".join(f"• {r['nom']}" for r in rouleurs) if rouleurs else "(aucun rouleur)"
        self.lbl_rouleurs_list.configure(text=txt)
        # Mettre à jour les menus déroulants de départ
        noms = ["— Sélectionner —"] + [r["nom"] for r in rouleurs]
        for attr in ("menu_depart_v1", "menu_depart_v2"):
            menu = getattr(self, attr, None)
            if menu:
                cur = menu.cget("variable").get() if hasattr(menu, "cget") else "— Sélectionner —"
                menu.configure(values=noms)
                # Garder la sélection courante si encore valide
                var_attr = attr.replace("menu_depart", "depart_var")
                var = getattr(self, var_attr, None)
                if var and var.get() not in noms:
                    var.set("— Sélectionner —")
        self._check_start_ready()

    def _check_start_ready(self):
        """Grise le bouton Démarrer si un rouleur de départ manque."""
        v1_ok = getattr(self, "depart_var_v1", None)
        v2_ok = getattr(self, "depart_var_v2", None)
        ready = (
            v1_ok and v1_ok.get() not in ("— Sélectionner —", "") and
            v2_ok and v2_ok.get() not in ("— Sélectionner —", "")
        )
        # Chercher le bouton Démarrer parmi les widgets
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkButton) and "DÉMARRER" in str(w.cget("text")):
                w.configure(
                    state="normal" if ready else "disabled",
                    fg_color="#22c55e" if ready else "#1a3a1a",
                    text_color="#000" if ready else "#4a7a4a"
                )

    def _save_config(self):
        km_str = self.entry_km.get().strip().replace(",", ".")
        try:
            float(km_str); set_config("km_par_tour", km_str)
        except ValueError:
            pass
        try:
            h = int(self.entry_h.get().strip() or "0")
            m = int(self.entry_min.get().strip() or "0")
            total_s = h * 3600 + m * 60
            if total_s > 0:
                set_config("race_duree", str(total_s))
        except ValueError:
            pass
        name = self.entry_name.get().strip()
        if name:
            set_config("race_name", name)

    def _start(self):
        # Vérification finale
        v1_nom = getattr(self, "depart_var_v1", None)
        v2_nom = getattr(self, "depart_var_v2", None)
        v1_nom = v1_nom.get() if v1_nom else ""
        v2_nom = v2_nom.get() if v2_nom else ""
        if v1_nom in ("— Sélectionner —", "") or v2_nom in ("— Sélectionner —", ""):
            messagebox.showwarning(
                "Rouleurs manquants",
                "Veuillez sélectionner un rouleur de départ\npour le Vélo 1 et le Vélo 2."
            )
            return

        self._save_config()

        # Sauvegarder les rouleurs de départ en config (le LiveTab les lira au démarrage)
        set_config("depart_rouleur_v1", v1_nom)
        set_config("depart_rouleur_v2", v2_nom)

        # Démarrer le chrono de course ET enregistrer le passage de départ
        # pour les 3 entités au même timestamp → leurs chronos de tour démarrent tous ensemble
        if not get_config("race_start"):
            from database import save_passage as _sp
            ts_depart = time.time()
            set_config("race_start", str(ts_depart))
            _sp("peloton", ts_depart, "depart")
            _sp("velo1",   ts_depart, "depart")
            _sp("velo2",   ts_depart, "depart")

        self.on_start()
        self.destroy()

    def _continue(self):
        self._save_config()
        self.on_start()
        self.destroy()

    def _reset(self):
        dialog = ctk.CTkInputDialog(
            text="Tapez  RESET  pour confirmer la réinitialisation :",
            title="⚠ Confirmation"
        )
        val = dialog.get_input()
        if val and val.strip().upper() == "RESET":
            reset_all()
            set_config("race_start", "")
            messagebox.showinfo("Reset", "Course réinitialisée. Les rouleurs sont conservés.")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Relai 24H — Chronomètre")
        self.geometry("1340x900")
        self.minsize(1100, 700)
        self.configure(fg_color=CLR_BG)

        init_db()
        self._build()
        self._start_timer()
        self.after(200, self._open_setup)

    def _build(self):
        self.tabview = ctk.CTkTabview(
            self, fg_color=CLR_BG,
            segmented_button_fg_color=CLR_CARD,
            segmented_button_selected_color="#1e2a3a",
            segmented_button_selected_hover_color="#243040",
            segmented_button_unselected_color=CLR_CARD,
            text_color=CLR_TEXT,
            text_color_disabled=CLR_MUTED,
        )
        self.tabview.pack(fill="both", expand=True)
        self.tabview.add("⚡  Live")
        self.tabview.add("📊  Stats")
        self.tabview.add("⚙  Config")

        self.live_tab = LiveTab(self.tabview.tab("⚡  Live"), self)
        self.live_tab.pack(fill="both", expand=True)

        self.stats_tab = StatsTab(self.tabview.tab("📊  Stats"))
        self.stats_tab.pack(fill="both", expand=True)

        self._build_config_tab()
        self.tabview.configure(command=self._on_tab_change)

    def _build_config_tab(self):
        tab = self.tabview.tab("⚙  Config")
        frame = ctk.CTkFrame(tab, fg_color=CLR_BG)
        frame.pack(fill="both", expand=True)
        ctk.CTkLabel(frame, text="⚙  CONFIGURATION",
                     font=("Consolas", 16, "bold"), text_color=CLR_TEXT
                     ).pack(pady=(40, 12))
        ctk.CTkButton(frame, text="🛠  Ouvrir la configuration complète",
                      fg_color=CLR_CARD, hover_color=CLR_BORDER,
                      border_color=CLR_ACCENT, border_width=1,
                      text_color=CLR_ACCENT, font=FONT_BTN,
                      height=50, width=360, command=self._open_setup
                      ).pack(pady=8)
        ctk.CTkLabel(frame,
                     text="Gérez les rouleurs, importez un CSV,\nmodifiez la distance et la durée de course.",
                     font=FONT_SMALL, text_color=CLR_MUTED, justify="center"
                     ).pack(pady=(4, 0))

    def _on_tab_change(self):
        if "Stats" in self.tabview.get():
            self.stats_tab.refresh()

    def _open_setup(self):
        SetupDialog(self, on_start=self._on_race_started)

    def _on_race_started(self):
        self.live_tab._refresh_rouleurs()

    def _start_timer(self):
        self.timer = TimerEngine(self._tick, interval=0.25)
        self.timer.start()

    def _tick(self):
        self.after(0, self.live_tab.refresh)

    def on_closing(self):
        self.timer.stop()
        self.destroy()
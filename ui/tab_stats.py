import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from models import VeloState, format_duration, format_speed, KM_PAR_TOUR, reload_km
from database import get_rouleurs, export_historique_csv

CLR_BG      = "#0d0f14"
CLR_CARD    = "#141720"
CLR_BORDER  = "#1e2233"
CLR_ACCENT1 = "#00d4ff"
CLR_ACCENT2 = "#ff6b35"
CLR_BOTH    = "#a8ff3e"
CLR_TEXT    = "#e8eaf0"
CLR_MUTED   = "#6b7280"
CLR_GOLD    = "#f59e0b"
CLR_SILVER  = "#94a3b8"
CLR_BRONZE  = "#cd7c3a"
CLR_DEPART  = "#7c3aed"

FONT_TITLE = ("Consolas", 12, "bold")
FONT_SMALL = ("Consolas", 11)
FONT_MICRO = ("Consolas", 10)
FONT_MED   = ("Consolas", 13, "bold")


def medal_color(rank):
    return [CLR_GOLD, CLR_SILVER, CLR_BRONZE][rank] if rank < 3 else CLR_TEXT


class StatsTable(ctk.CTkFrame):
    def __init__(self, parent, title, color, columns, height=200):
        super().__init__(parent, fg_color=CLR_CARD, corner_radius=10,
                         border_color=color, border_width=2)
        self.columns = columns
        hdr = ctk.CTkFrame(self, fg_color=color, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=title, font=FONT_TITLE,
                     text_color="#000" if color == CLR_BOTH else "#fff"
                     ).pack(pady=5, padx=10, anchor="w")
        col_hdr = ctk.CTkFrame(self, fg_color="#0d0f1a")
        col_hdr.pack(fill="x")
        for i, (name, w) in enumerate(columns):
            ctk.CTkLabel(col_hdr, text=name.upper(), font=FONT_MICRO,
                         text_color=CLR_MUTED, width=w, anchor="w"
                         ).grid(row=0, column=i, padx=(10 if i == 0 else 3, 3), pady=3)
        self.rows_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=height)
        self.rows_frame.pack(fill="both", expand=True)

    def set_rows(self, rows, color_col0=True, depart_rows=None):
        for w in self.rows_frame.winfo_children():
            w.destroy()
        depart_rows = depart_rows or set()
        for rank, row_data in enumerate(rows):
            is_depart = rank in depart_rows
            row_f = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=1)
            for i, (value, (_, w)) in enumerate(zip(row_data, self.columns)):
                if is_depart:
                    clr = CLR_DEPART
                elif color_col0 and i == 0:
                    clr = medal_color(rank)
                else:
                    clr = CLR_TEXT
                ctk.CTkLabel(row_f, text=str(value), font=FONT_SMALL,
                             text_color=clr, width=w, anchor="w"
                             ).grid(row=0, column=i, padx=(10 if i == 0 else 3, 3))
            if rank < len(rows) - 1:
                ctk.CTkFrame(self.rows_frame, fg_color=CLR_BORDER,
                             height=1).pack(fill="x", padx=6)


# ── Dialog fiche rouleur ──────────────────────────────────────────────────────

class DialogFicheRouleur(ctk.CTkToplevel):
    def __init__(self, parent, v1: VeloState, v2: VeloState):
        super().__init__(parent)
        self.title("Fiche individuelle rouleur")
        self.geometry("520x620")
        self.configure(fg_color=CLR_BG)
        self.resizable(False, False)
        self.grab_set(); self.lift(); self.focus_force()

        self.v1 = v1
        self.v2 = v2

        ctk.CTkLabel(self, text="👤  FICHE INDIVIDUELLE",
                     font=("Consolas", 14, "bold"), text_color=CLR_BOTH).pack(pady=(18, 4))

        self.selected = tk.StringVar(value="")
        ctk.CTkLabel(self, text="Sélectionner un rouleur :",
                     font=FONT_SMALL, text_color=CLR_MUTED).pack(anchor="w", padx=24)

        roul_f = ctk.CTkFrame(self, fg_color=CLR_CARD, corner_radius=8)
        roul_f.pack(fill="x", padx=24, pady=(4, 10))
        rouleurs = get_rouleurs()
        noms = [r["nom"] for r in rouleurs]
        self.menu = ctk.CTkOptionMenu(roul_f, values=noms if noms else ["—"],
                                      variable=self.selected,
                                      fg_color=CLR_BG, button_color=CLR_BORDER,
                                      text_color=CLR_TEXT, font=FONT_SMALL,
                                      command=lambda _: self._show())
        self.menu.pack(fill="x", padx=10, pady=10)

        self.result_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.result_frame.pack(fill="both", expand=True, padx=24, pady=(0, 10))

        ctk.CTkButton(self, text="Fermer", fg_color=CLR_CARD,
                      text_color=CLR_MUTED, font=FONT_SMALL, height=34,
                      command=self.destroy).pack(fill="x", padx=24, pady=(0, 10))

    def _show(self):
        for w in self.result_frame.winfo_children():
            w.destroy()

        nom = self.selected.get()
        if not nom or nom == "—":
            return

        # Agréger les stats de ce rouleur sur les deux vélos
        tours_all = []   # liste de (duree, is_depart, velo_label)
        total_km = 0.0
        total_tps = 0.0
        meilleur = None

        for velo, label in [(self.v1, "V1"), (self.v2, "V2")]:
            stats = velo.get_stats_par_rouleur()
            if nom in stats:
                s = stats[nom]
                total_km  += s["km"]
                total_tps += s["temps_total"]
                for t, is_dep in s["tous_les_tours"]:
                    tours_all.append((t, is_dep, label))
                    if not is_dep:
                        if meilleur is None or t < meilleur:
                            meilleur = t

        if not tours_all:
            ctk.CTkLabel(self.result_frame, text="Aucune donnée pour ce rouleur.",
                         font=FONT_SMALL, text_color=CLR_MUTED).pack(pady=20)
            return

        nb_tours = len(tours_all)
        nb_ranked = sum(1 for _, is_dep, _ in tours_all if not is_dep)
        moy = total_tps / nb_tours if nb_tours > 0 else None

        # Résumé
        summary = ctk.CTkFrame(self.result_frame, fg_color=CLR_CARD, corner_radius=8)
        summary.pack(fill="x", pady=(0, 10))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        summary.columnconfigure(2, weight=1)
        summary.columnconfigure(3, weight=1)

        for col_idx, (lbl, val) in enumerate([
            ("Tours", str(nb_tours)),
            ("Km", f"{total_km:.1f}"),
            ("Meilleur", format_duration(meilleur)),
            ("Moyenne", format_duration(moy)),
        ]):
            ctk.CTkLabel(summary, text=lbl, font=FONT_MICRO,
                         text_color=CLR_MUTED).grid(row=0, column=col_idx, pady=(8, 0))
            ctk.CTkLabel(summary, text=val, font=("Consolas", 16, "bold"),
                         text_color=CLR_TEXT).grid(row=1, column=col_idx, pady=(0, 8))

        # Historique des tours
        ctk.CTkLabel(self.result_frame, text="Historique des tours :",
                     font=FONT_SMALL, text_color=CLR_MUTED).pack(anchor="w", pady=(0, 4))

        tbl = ctk.CTkFrame(self.result_frame, fg_color=CLR_CARD, corner_radius=8)
        tbl.pack(fill="x")

        hdr = ctk.CTkFrame(tbl, fg_color="#0d0f1a")
        hdr.pack(fill="x")
        for col_idx, (h, w) in enumerate([("#", 40), ("Vélo", 45), ("Durée", 80),
                                           ("Vitesse", 90), ("Type", 70)]):
            ctk.CTkLabel(hdr, text=h, font=FONT_MICRO, text_color=CLR_MUTED,
                         width=w, anchor="w").grid(
                row=0, column=col_idx, padx=(10 if col_idx == 0 else 3, 3), pady=3)

        for idx, (t, is_dep, label) in enumerate(reversed(tours_all)):
            clr = CLR_DEPART if is_dep else CLR_TEXT
            row_f = ctk.CTkFrame(tbl, fg_color="transparent")
            row_f.pack(fill="x", pady=1)
            spd = KM_PAR_TOUR / (t / 3600) if t > 0 else 0
            type_str = "🚦 Départ" if is_dep else "Course"
            for col_idx, (val, w) in enumerate([
                (str(nb_tours - idx), 40),
                (label, 45),
                (format_duration(t), 80),
                (f"{spd:.1f} km/h", 90),
                (type_str, 70),
            ]):
                ctk.CTkLabel(row_f, text=val, font=FONT_MICRO, text_color=clr,
                             width=w, anchor="w").grid(
                    row=0, column=col_idx, padx=(10 if col_idx == 0 else 3, 3))
            if idx < nb_tours - 1:
                ctk.CTkFrame(tbl, fg_color=CLR_BORDER, height=1).pack(fill="x", padx=6)


# ── Onglet Stats ──────────────────────────────────────────────────────────────

class StatsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=CLR_BG)
        self._v1 = None
        self._v2 = None
        self._build()

    def _build(self):
        topbar = ctk.CTkFrame(self, fg_color="#08090d", corner_radius=0)
        topbar.pack(fill="x")
        ctk.CTkLabel(topbar, text="📊  STATISTIQUES DE COURSE",
                     font=("Consolas", 14, "bold"), text_color=CLR_TEXT
                     ).pack(side="left", padx=20, pady=8)

        # Boutons dans la topbar
        btn_f = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_f.pack(side="right", padx=12, pady=6)

        ctk.CTkButton(btn_f, text="👤 Fiche rouleur",
                      fg_color=CLR_CARD, hover_color=CLR_BORDER,
                      border_color=CLR_BOTH, border_width=1,
                      text_color=CLR_BOTH, font=FONT_SMALL,
                      height=30, width=140,
                      command=self._open_fiche).pack(side="left", padx=(0, 6))

        ctk.CTkButton(btn_f, text="💾 Exporter CSV",
                      fg_color=CLR_CARD, hover_color=CLR_BORDER,
                      border_color=CLR_ACCENT1, border_width=1,
                      text_color=CLR_ACCENT1, font=FONT_SMALL,
                      height=30, width=130,
                      command=self._export_csv).pack(side="left", padx=(0, 6))

        ctk.CTkButton(btn_f, text="🔄 Actualiser",
                      fg_color=CLR_CARD, hover_color=CLR_BORDER,
                      text_color=CLR_TEXT, font=FONT_SMALL,
                      height=30, width=110, command=self.refresh).pack(side="left")

        ctk.CTkLabel(topbar, text="🚦 = tour de départ",
                     font=("Consolas", 9), text_color=CLR_DEPART).pack(side="right", padx=8)

        self.inner_tabs = ctk.CTkTabview(
            self, fg_color=CLR_BG,
            segmented_button_fg_color=CLR_CARD,
            segmented_button_selected_color="#1e2a3a",
            segmented_button_unselected_color=CLR_CARD,
            text_color=CLR_TEXT,
        )
        self.inner_tabs.pack(fill="both", expand=True)
        self.inner_tabs.add("🔵  Vélo 1")
        self.inner_tabs.add("🟠  Vélo 2")
        self.inner_tabs.add("🟢  Tous vélos")

        self._build_velo_tab("🔵  Vélo 1", CLR_ACCENT1, 1)
        self._build_velo_tab("🟠  Vélo 2", CLR_ACCENT2, 2)
        self._build_combined_tab()
        self.refresh()

    def _build_velo_tab(self, tab_name, color, velo_num):
        tab = self.inner_tabs.tab(tab_name)
        scroll = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # Rangée 1 : meilleurs tours + km
        row1 = _row(scroll)
        tbl_best = StatsTable(
            row1, f"🏆 MEILLEURS TOURS PAR ROULEUR — VÉLO {velo_num}  (hors départ)",
            color, [("Rouleur", 150), ("Meilleur", 80), ("Moy.", 80), ("Tours", 55), ("Km", 65)])
        tbl_best.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        setattr(self, f"tbl_best_v{velo_num}", tbl_best)

        tbl_km = StatsTable(
            row1, f"🚴 KM PARCOURUS — VÉLO {velo_num}",
            color, [("Rouleur", 150), ("Km", 75), ("Tours", 55), ("Tps total", 90)])
        tbl_km.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        setattr(self, f"tbl_km_v{velo_num}", tbl_km)

        # Rangée 2 : top 15 tous rouleurs confondus + historique
        row2 = _row(scroll, pady=(10, 0))
        tbl_top15 = StatsTable(
            row2, f"🥇 TOP 15 MEILLEURS TEMPS — VÉLO {velo_num}",
            color, [("#", 30), ("Rouleur", 140), ("Temps", 80), ("Vitesse", 90)],
            height=220)
        tbl_top15.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        setattr(self, f"tbl_top15_v{velo_num}", tbl_top15)

        tbl_hist = StatsTable(
            row2, f"📋 HISTORIQUE TOURS — VÉLO {velo_num}",
            color, [("Tour #", 60), ("Durée", 80), ("Vitesse", 90), ("Rouleur", 150)],
            height=220)
        tbl_hist.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        setattr(self, f"tbl_hist_v{velo_num}", tbl_hist)

    def _build_combined_tab(self):
        tab = self.inner_tabs.tab("🟢  Tous vélos")
        scroll = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        row1 = _row(scroll)
        self.tbl_best_all = StatsTable(
            row1, "🏆 MEILLEURS TOURS PAR ROULEUR — TOUS VÉLOS", CLR_BOTH,
            [("Rouleur", 140), ("Vélo", 50), ("Meilleur", 80), ("Moy.", 80), ("Tours", 55), ("Km", 60)])
        self.tbl_best_all.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.tbl_km_all = StatsTable(
            row1, "🚴 KM PARCOURUS — TOUS VÉLOS", CLR_BOTH,
            [("Rouleur", 150), ("Km total", 80), ("Tours", 55), ("Tps total", 90)])
        self.tbl_km_all.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        row2 = _row(scroll, pady=(10, 0))
        self.tbl_top15_all = StatsTable(
            row2, "🥇 TOP 15 MEILLEURS TEMPS — TOUS VÉLOS", CLR_BOTH,
            [("#", 30), ("Rouleur", 130), ("Vélo", 45), ("Temps", 80), ("Vitesse", 90)],
            height=220)
        self.tbl_top15_all.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.tbl_hist_all = StatsTable(
            row2, "📋 HISTORIQUE TOUS TOURS", CLR_BOTH,
            [("Tour", 65), ("Vélo", 45), ("Durée", 80), ("Vitesse", 90), ("Rouleur", 140)],
            height=220)
        self.tbl_hist_all.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        reload_km()
        self._v1 = VeloState(1); self._v1.load_from_db()
        self._v2 = VeloState(2); self._v2.load_from_db()
        self._fill_velo(self._v1, 1)
        self._fill_velo(self._v2, 2)
        self._fill_combined(self._v1, self._v2)

    def _fill_velo(self, velo: VeloState, num: int):
        stats = velo.get_stats_par_rouleur()

        # Meilleurs tours par rouleur
        rows_best = []
        for nom, s in stats.items():
            avg = s["temps_total"] / s["tours"] if s["tours"] > 0 else None
            rows_best.append([nom, format_duration(s["meilleur_tour"]),
                              format_duration(avg), s["tours"], f"{s['km']:.1f}"])
        rows_best.sort(key=lambda r: r[1])
        getattr(self, f"tbl_best_v{num}").set_rows(
            rows_best or [["— Aucune donnée —", "", "", "", ""]])

        # Km parcourus
        rows_km = []
        for nom, s in stats.items():
            rows_km.append([nom, f"{s['km']:.1f} km", s["tours"],
                            format_duration(s["temps_total"])])
        rows_km.sort(key=lambda r: float(r[1].replace(" km", "")), reverse=True)
        getattr(self, f"tbl_km_v{num}").set_rows(
            rows_km or [["— Aucune donnée —", "", "", ""]])

        # Top 15 tous rouleurs
        all_ranked = []
        for nom, s in stats.items():
            for t in s["tours_ranked"]:
                spd = KM_PAR_TOUR / (t / 3600) if t > 0 else 0
                all_ranked.append((nom, t, spd))
        all_ranked.sort(key=lambda x: x[1])
        rows_top15 = []
        for rank, (nom, t, spd) in enumerate(all_ranked[:15]):
            rows_top15.append([f"#{rank+1}", nom, format_duration(t), f"{spd:.1f} km/h"])
        getattr(self, f"tbl_top15_v{num}").set_rows(
            rows_top15 or [["", "— Aucune donnée —", "", ""]])

        # Historique
        rows_hist = []
        depart_indices = set()
        for i, t in enumerate(velo.tour_times):
            rouleur = velo.get_rouleur_at_time(velo.timestamps[i]) or "?"
            is_dep = (i == 0)
            tag = "🚦 Départ" if is_dep else f"#{i+1}"
            rows_hist.append([tag, format_duration(t),
                              format_speed(KM_PAR_TOUR, t), rouleur])
            if is_dep:
                depart_indices.add(i)
        total = len(rows_hist)
        rows_hist_rev = list(reversed(rows_hist))
        depart_rev = {total - 1 - i for i in depart_indices}
        getattr(self, f"tbl_hist_v{num}").set_rows(
            rows_hist_rev or [["—", "—", "—", "—"]],
            color_col0=False, depart_rows=depart_rev)

    def _fill_combined(self, v1: VeloState, v2: VeloState):
        combined = {}
        all_ranked_global = []

        for velo, label in [(v1, "V1"), (v2, "V2")]:
            stats = velo.get_stats_par_rouleur()
            for nom, s in stats.items():
                if nom not in combined:
                    combined[nom] = {"tours": 0, "km": 0.0, "temps_total": 0.0,
                                     "meilleur_tour": None, "velos": set()}
                combined[nom]["tours"]       += s["tours"]
                combined[nom]["km"]          += s["km"]
                combined[nom]["temps_total"] += s["temps_total"]
                combined[nom]["velos"].add(label)
                for t, is_dep in s["tous_les_tours"]:
                    if not is_dep:
                        cur = combined[nom]["meilleur_tour"]
                        if cur is None or t < cur:
                            combined[nom]["meilleur_tour"] = t
                for t in s["tours_ranked"]:
                    spd = KM_PAR_TOUR / (t / 3600) if t > 0 else 0
                    all_ranked_global.append((nom, label, t, spd))

        rows_best = []
        for nom, s in combined.items():
            avg = s["temps_total"] / s["tours"] if s["tours"] > 0 else None
            rows_best.append([nom, "/".join(sorted(s["velos"])),
                              format_duration(s["meilleur_tour"]),
                              format_duration(avg), s["tours"], f"{s['km']:.1f}"])
        rows_best.sort(key=lambda r: r[2])
        self.tbl_best_all.set_rows(rows_best or [["— Aucune donnée —", "", "", "", "", ""]])

        rows_km = []
        for nom, s in combined.items():
            rows_km.append([nom, f"{s['km']:.1f} km", s["tours"],
                            format_duration(s["temps_total"])])
        rows_km.sort(key=lambda r: float(r[1].replace(" km", "")), reverse=True)
        self.tbl_km_all.set_rows(rows_km or [["— Aucune donnée —", "", "", ""]])

        # Top 15 global
        all_ranked_global.sort(key=lambda x: x[2])
        rows_top15 = []
        for rank, (nom, label, t, spd) in enumerate(all_ranked_global[:15]):
            rows_top15.append([f"#{rank+1}", nom, label, format_duration(t), f"{spd:.1f} km/h"])
        self.tbl_top15_all.set_rows(rows_top15 or [["", "— Aucune donnée —", "", "", ""]])

        # Historique fusionné
        all_tours = []
        for velo, label in [(v1, "V1"), (v2, "V2")]:
            for i, t in enumerate(velo.tour_times):
                rouleur = velo.get_rouleur_at_time(velo.timestamps[i]) or "?"
                is_dep = (i == 0)
                tag = "🚦 Départ" if is_dep else f"{label} #{i+1}"
                all_tours.append({"ts": velo.timestamps[i], "label": label,
                                   "tag": tag, "duree": t, "rouleur": rouleur,
                                   "is_depart": is_dep})
        all_tours.sort(key=lambda x: x["ts"], reverse=True)
        rows_hist = []
        depart_indices = set()
        for idx, x in enumerate(all_tours):
            rows_hist.append([x["tag"], x["label"],
                              format_duration(x["duree"]),
                              format_speed(KM_PAR_TOUR, x["duree"]),
                              x["rouleur"]])
            if x["is_depart"]:
                depart_indices.add(idx)
        self.tbl_hist_all.set_rows(
            rows_hist or [["—", "—", "—", "—", "—"]],
            color_col0=False, depart_rows=depart_indices)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_fiche(self):
        if self._v1 is None:
            self.refresh()
        DialogFicheRouleur(self, self._v1, self._v2)

    def _export_csv(self):
        if self._v1 is None:
            self.refresh()
        output_dir = filedialog.askdirectory(title="Choisir le dossier d'export")
        if not output_dir:
            return
        try:
            f1 = export_historique_csv(self._v1, 1, output_dir)
            f2 = export_historique_csv(self._v2, 2, output_dir)
            messagebox.showinfo("Export réussi",
                                f"Fichiers créés :\n{os.path.basename(f1)}\n{os.path.basename(f2)}")
        except Exception as e:
            messagebox.showerror("Erreur export", str(e))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(parent, pady=(0, 0)):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", pady=pady)
    f.columnconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    return f
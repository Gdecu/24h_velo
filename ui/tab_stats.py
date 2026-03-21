import customtkinter as ctk
from models import VeloState, format_duration, format_speed, KM_PAR_TOUR, reload_km

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
CLR_DEPART  = "#7c3aed"   # couleur spéciale pour le tour de départ

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
        """
        depart_rows: set of row indices que sont des tours de départ
                     (affichés en violet avec tag 🚦)
        """
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


class StatsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=CLR_BG)
        self._build()

    def _build(self):
        topbar = ctk.CTkFrame(self, fg_color="#08090d", corner_radius=0)
        topbar.pack(fill="x")
        ctk.CTkLabel(topbar, text="📊  STATISTIQUES DE COURSE",
                     font=("Consolas", 14, "bold"), text_color=CLR_TEXT
                     ).pack(side="left", padx=20, pady=8)
        ctk.CTkButton(topbar, text="🔄 Actualiser",
                      fg_color=CLR_CARD, hover_color=CLR_BORDER,
                      text_color=CLR_TEXT, font=FONT_SMALL,
                      width=120, height=30, command=self.refresh
                      ).pack(side="right", padx=20, pady=6)

        ctk.CTkLabel(topbar,
                     text="🚦 = tour de départ (non classé)",
                     font=("Consolas", 9), text_color=CLR_DEPART
                     ).pack(side="right", padx=8)

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

        row1 = _row(scroll)
        tbl_best = StatsTable(row1, f"🏆 MEILLEURS TOURS — VÉLO {velo_num}  (hors départ)",
                              color, [("Rouleur", 160), ("Meilleur", 80),
                                      ("Moy.", 80), ("Tours", 55), ("Km", 65)])
        tbl_best.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        setattr(self, f"tbl_best_v{velo_num}", tbl_best)

        tbl_km = StatsTable(row1, f"🚴 KILOMÈTRES PARCOURUS — VÉLO {velo_num}",
                            color, [("Rouleur", 160), ("Km", 75), ("Tours", 55), ("Tps total", 90)])
        tbl_km.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        setattr(self, f"tbl_km_v{velo_num}", tbl_km)

        row2 = _row(scroll, pady=(10, 0))
        tbl_hist = StatsTable(row2, f"📋 HISTORIQUE TOURS — VÉLO {velo_num}  (🚦 = départ)",
                              color, [("Tour #", 60), ("Durée", 80),
                                      ("Vitesse", 90), ("Rouleur", 150)],
                              height=260)
        tbl_hist.grid(row=0, column=0, sticky="nsew")
        setattr(self, f"tbl_hist_v{velo_num}", tbl_hist)

    def _build_combined_tab(self):
        tab = self.inner_tabs.tab("🟢  Tous vélos")
        scroll = ctk.CTkScrollableFrame(tab, fg_color=CLR_BG)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        row1 = _row(scroll)
        self.tbl_best_all = StatsTable(
            row1, "🏆 MEILLEURS TOURS — TOUS VÉLOS  (hors départ)", CLR_BOTH,
            [("Rouleur", 150), ("Vélo", 50), ("Meilleur", 80),
             ("Moy.", 80), ("Tours", 55), ("Km", 65)]
        )
        self.tbl_best_all.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.tbl_km_all = StatsTable(
            row1, "🚴 KILOMÈTRES PARCOURUS — TOUS VÉLOS", CLR_BOTH,
            [("Rouleur", 150), ("Km total", 80), ("Tours", 55), ("Tps total", 90)]
        )
        self.tbl_km_all.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        row2 = _row(scroll, pady=(10, 0))
        self.tbl_hist_all = StatsTable(
            row2, "📋 HISTORIQUE TOUS TOURS  (🚦 = départ)", CLR_BOTH,
            [("Tour", 70), ("Vélo", 45), ("Durée", 80),
             ("Vitesse", 90), ("Rouleur", 150)],
            height=280
        )
        self.tbl_hist_all.grid(row=0, column=0, sticky="nsew")

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self):
        reload_km()
        v1 = VeloState(1); v1.load_from_db()
        v2 = VeloState(2); v2.load_from_db()
        self._fill_velo(v1, 1)
        self._fill_velo(v2, 2)
        self._fill_combined(v1, v2)

    def _fill_velo(self, velo: VeloState, num: int):
        stats = velo.get_stats_par_rouleur()

        # Meilleurs tours (classement sans départ)
        rows_best = []
        for nom, s in stats.items():
            avg = s["temps_total"] / s["tours"] if s["tours"] > 0 else None
            rows_best.append([
                nom,
                format_duration(s["meilleur_tour"]),
                format_duration(avg),
                s["tours"],
                f"{s['km']:.1f}"
            ])
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

        # Historique : du plus récent, départ inclus avec flag
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

        # Inverser (du plus récent au plus ancien) + adapter les indices de départ
        total = len(rows_hist)
        rows_hist_rev = list(reversed(rows_hist))
        depart_rev = {total - 1 - i for i in depart_indices}

        getattr(self, f"tbl_hist_v{num}").set_rows(
            rows_hist_rev or [["— Aucun tour —", "", "", ""]],
            color_col0=False,
            depart_rows=depart_rev
        )

    def _fill_combined(self, v1: VeloState, v2: VeloState):
        combined = {}

        for velo, label in [(v1, "V1"), (v2, "V2")]:
            stats = velo.get_stats_par_rouleur()
            for nom, s in stats.items():
                if nom not in combined:
                    combined[nom] = {"tours": 0, "km": 0.0,
                                     "temps_total": 0.0, "meilleur_tour": None,
                                     "velos": set()}
                combined[nom]["tours"]       += s["tours"]
                combined[nom]["km"]          += s["km"]
                combined[nom]["temps_total"] += s["temps_total"]
                combined[nom]["velos"].add(label)
                for t, is_dep in s.get("tous_les_tours", []):
                    if not is_dep:
                        cur = combined[nom]["meilleur_tour"]
                        if cur is None or t < cur:
                            combined[nom]["meilleur_tour"] = t

        rows_best = []
        for nom, s in combined.items():
            avg = s["temps_total"] / s["tours"] if s["tours"] > 0 else None
            rows_best.append([
                nom,
                "/".join(sorted(s["velos"])),
                format_duration(s["meilleur_tour"]),
                format_duration(avg),
                s["tours"],
                f"{s['km']:.1f}"
            ])
        rows_best.sort(key=lambda r: r[2])
        self.tbl_best_all.set_rows(
            rows_best or [["— Aucune donnée —", "", "", "", "", ""]])

        rows_km = []
        for nom, s in combined.items():
            rows_km.append([nom, f"{s['km']:.1f} km", s["tours"],
                            format_duration(s["temps_total"])])
        rows_km.sort(key=lambda r: float(r[1].replace(" km", "")), reverse=True)
        self.tbl_km_all.set_rows(
            rows_km or [["— Aucune donnée —", "", "", ""]])

        # Historique fusionné + départs marqués
        all_tours = []
        for velo, label in [(v1, "V1"), (v2, "V2")]:
            for i, t in enumerate(velo.tour_times):
                rouleur = velo.get_rouleur_at_time(velo.timestamps[i]) or "?"
                is_dep = (i == 0)
                tag = "🚦 Départ" if is_dep else f"{label} #{i+1}"
                all_tours.append({
                    "ts": velo.timestamps[i], "label": label,
                    "tag": tag, "duree": t,
                    "rouleur": rouleur, "is_depart": is_dep
                })
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
            rows_hist or [["— Aucun tour —", "", "", "", ""]],
            color_col0=False,
            depart_rows=depart_indices
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(parent, pady=(0, 0)):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", pady=pady)
    f.columnconfigure(0, weight=1)
    f.columnconfigure(1, weight=1)
    return f

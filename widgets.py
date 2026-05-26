import tkinter as tk
from tkinter import ttk
from core import fmt

class DataTable(ttk.Frame):
    def __init__(self, parent, columns, font_size=10, **kwargs):
        super().__init__(parent, **kwargs)
        self.columns = columns
        self.col_total = sum(c[2] for c in columns)
        self.data = []
        self.sort_col = None
        self.sort_rev = False
        self._theme_data = None
        self._font_size = font_size
        self._filter_win = None
        self._filter_round_from = None
        self._filter_round_to = None
        self._highlight_round = None
        self._build_ui()

    def _build_ui(self):
        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        vsb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._inner = tk.Frame(self._canvas)
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw", tags="inner")
        self._canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        if self._inner.winfo_exists():
            self._inner.configure(width=event.width)

    def set_theme(self, t):
        self._theme_data = t
        if self._canvas.winfo_exists():
            self._canvas.configure(bg=t["tree_bg"])

    def set_font_size(self, size):
        self._font_size = max(8, min(24, size))
        self._rebuild()

    def set_filter(self, win=None, round_from=None, round_to=None):
        self._filter_win = win
        self._filter_round_from = round_from
        self._filter_round_to = round_to
        self._rebuild()

    def highlight_round(self, rnd):
        self._highlight_round = rnd
        self._rebuild()

    def set_data(self, rows):
        self.data = list(rows)
        self._rebuild()

    def _cell_values(self, r):
        df_s = f"+{r['df']}" if r['df'] > 0 else str(r['df'])
        dt_s = f"+{r['dt']:.3f}" if r['dt'] > 0 else f"{r['dt']:.3f}"
        mom_s = f"+{r['mom']}" if r['mom'] > 0 else str(r['mom'])
        vals = [str(r["round"]), str(r["a_frames"]), fmt(r["a_time"]),
                fmt(r["cum_a"]), str(r["b_frames"]), fmt(r["b_time"]),
                fmt(r["cum_b"]), df_s, dt_s, r["win"], mom_s]
        return {c[0]: v for c, v in zip(self.columns, vals)}

    def _cell_fg(self, r, t):
        fg = {}
        for key, _, _ in self.columns:
            if key in ("a_frames", "a_time", "cum_a"):
                fg[key] = t["win_a"]
            elif key in ("b_frames", "b_time", "cum_b"):
                fg[key] = t["win_b"]
            elif key in ("df", "dt"):
                v = r[key]
                fg[key] = t["win_a"] if v > 0 else (t["win_b"] if v < 0 else t["win_t"])
            elif key == "win":
                w = r["win"]
                fg[key] = t["win_a"] if w == "A" else (t["win_b"] if w == "B" else t["win_t"])
            elif key == "mom":
                v = r["mom"]
                fg[key] = t["win_a"] if v > 0 else (t["win_b"] if v < 0 else t["win_t"])
            else:
                fg[key] = t["tree_fg"]
        return fg

    def _rebuild(self):
        for w in self._inner.winfo_children():
            w.destroy()

        t = self._theme_data
        if not t:
            return

        fs = self._font_size
        row_h = fs * 3
        hdr_h = fs * 3 + 2

        is_easy = getattr(self, "_easy_mode", False)
        prefix_a = "Best" if is_easy else "A"
        prefix_b = "You" if is_easy else "B"

        col_labels = {c[0]: c[1] for c in self.columns}
        col_labels["a_frames"] = f"{prefix_a} Fr"
        col_labels["a_time"] = f"{prefix_a} Time"
        col_labels["cum_a"] = f"{prefix_a} Cum"
        col_labels["b_frames"] = f"{prefix_b} Fr"
        col_labels["b_time"] = f"{prefix_b} Time"
        col_labels["cum_b"] = f"{prefix_b} Cum"
        col_labels["df"] = "D Frames"
        col_labels["dt"] = "D Time"

        sort_col = self.sort_col
        data = list(self.data)

        # Apply filters
        if self._filter_win:
            data = [r for r in data if r["win"] == self._filter_win]
        if self._filter_round_from is not None:
            data = [r for r in data if r["round"] >= self._filter_round_from]
        if self._filter_round_to is not None:
            data = [r for r in data if r["round"] <= self._filter_round_to]

        if sort_col:
            data.sort(key=lambda r: (r.get(sort_col) if isinstance(r.get(sort_col), (int, float))
                                     else str(r.get(sort_col, ""))), reverse=self.sort_rev)

        hdr = tk.Frame(self._inner, height=hdr_h, bg=t["heading_bg"])
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for ci, (key, _, w) in enumerate(self.columns):
            fg = t["accent"] if key == sort_col else t["heading_fg"]
            txt = col_labels[key]
            if key == sort_col:
                txt = ("v " if self.sort_rev else "^ ") + txt
            lbl = tk.Label(hdr, text=txt, fg=fg, bg=t["heading_bg"],
                           font=("Segoe UI", max(8, fs - 1), "bold"), anchor="center", cursor="hand2")
            lbl.grid(row=0, column=ci, sticky="ew")
            hdr.grid_columnconfigure(ci, minsize=w, weight=w)
            lbl.bind("<Button-1>", lambda e, c=key: self._sort(c))

        sep = tk.Frame(self._inner, height=1, bg=t["border"])
        sep.pack(fill="x")

        cw = self._canvas.winfo_width()
        total_h = hdr_h + 1 + len(data) * row_h
        self._inner.configure(width=cw if cw > 1 else self.col_total, height=total_h)
        self._inner.pack_propagate(False)

        max_abs = {}
        for key in ("df", "dt"):
            max_abs[key] = max((abs(r[key]) for r in data), default=1)

        for r in data:
            win = r["win"]
            tint = t["a_tint"] if win == "A" else (t["b_tint"] if win == "B" else t["t_tint"])
            vals = self._cell_values(r)
            fg_map = self._cell_fg(r, t)

            rf = tk.Frame(self._inner, height=row_h)
            rf.pack(fill="x")
            rf.pack_propagate(False)

            def make_hover(rf_inner, t_inner, tint_inner, hover_tint_inner):
                def on_enter(ev):
                    try:
                        for c in rf_inner.winfo_children():
                            c.configure(bg=hover_tint_inner)
                    except:
                        pass
                def on_leave(ev):
                    try:
                        for c in rf_inner.winfo_children():
                            c.configure(bg=tint_inner)
                    except:
                        pass
                rf_inner.bind("<Enter>", on_enter)
                rf_inner.bind("<Leave>", on_leave)

            hover_tint = t.get("a_tint_hover", tint) if win == "A" else (
                t.get("b_tint_hover", tint) if win == "B" else t.get("t_tint_hover", tint))

            is_hl = self._highlight_round is not None and r["round"] == self._highlight_round
            bg_tint = t["selectbg"] if is_hl else tint

            for ci, (key, _, w) in enumerate(self.columns):
                if key in ("df", "dt") and r[key] != 0:
                    bar_max = max_abs[key] or 1
                    bar_frac = abs(r[key]) / bar_max
                    bar_w = max(int(w * bar_frac * 0.85), 4)
                    bar_color = t["win_a"] if r[key] > 0 else t["win_b"]
                    cell = tk.Frame(rf, bg=bg_tint)
                    cell.grid(row=0, column=ci, sticky="ew")
                    rf.grid_columnconfigure(ci, minsize=w, weight=w)
                    tk.Frame(cell, width=bar_w, bg=bar_color).pack(side="left")
                    tk.Label(cell, text=vals.get(key, ""), fg=fg_map.get(key, t["tree_fg"]),
                             bg=bg_tint, font=("Segoe UI", fs), anchor="center"
                             ).pack(side="left", fill="x", expand=True)
                else:
                    lbl = tk.Label(rf, text=vals.get(key, ""), fg=fg_map.get(key, t["tree_fg"]),
                                   bg=bg_tint, font=("Segoe UI", fs), anchor="center")
                    lbl.grid(row=0, column=ci, sticky="ew")
                    rf.grid_columnconfigure(ci, minsize=w, weight=w)

            if not is_hl:
                make_hover(rf, t, tint, hover_tint)

    def _sort(self, col):
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        self._rebuild()


class StatCard(tk.Frame):
    def __init__(self, parent, label, value="", fg_tag=None, **kwargs):
        super().__init__(parent, highlightthickness=1, **kwargs)
        self._fg_tag = fg_tag

        self._accent = tk.Frame(self, height=3)
        self._accent.pack(side="top", fill="x")

        content = tk.Frame(self)
        content.pack(fill="both", expand=True, padx=18, pady=(14, 16))
        self._content = content

        self.lbl = tk.Label(content, text=label, font=("Segoe UI", 9))
        self.lbl.pack(anchor="w")

        self.val = tk.Label(content, text=value, font=("Segoe UI", 26, "bold"))
        self.val.pack(anchor="w", pady=(4, 0))
        if fg_tag:
            self.val._fg_tag = fg_tag

        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, enter):
        t = self._theme_data
        if not t:
            return
        bg = t["card_hover_bg"] if enter else t["card_bg"]
        self.configure(bg=bg)
        self._content.configure(bg=bg)
        self.lbl.configure(bg=bg)
        self.val.configure(bg=bg)

    def theme(self, t):
        self._theme_data = t
        self.configure(highlightbackground=t["border"], bg=t["card_bg"])
        self._accent.configure(bg=t["accent"])
        self._content.configure(bg=t["card_bg"])
        self.lbl.configure(bg=t["card_bg"], fg=t["card_label_fg"])
        self.val.configure(bg=t["card_bg"])
        if hasattr(self.val, "_fg_tag"):
            tag_map = {"a": t["win_a"], "b": t["win_b"], "t": t["win_t"],
                       "fg": t["label_fg"]}
            self.val.configure(fg=tag_map.get(self.val._fg_tag, t["label_fg"]))


class MenuCard(tk.Frame):
    def __init__(self, parent, title, desc, command, **kwargs):
        super().__init__(parent, highlightthickness=1, **kwargs)
        self._cmd = command
        self._accent = tk.Frame(self, width=5)
        self._accent.pack(side="left", fill="y")
        self._base_padx = (12, 16)
        self._base_pady = (10, 12)

        content = tk.Frame(self)
        content.pack(side="left", fill="both", expand=True, padx=self._base_padx, pady=self._base_pady)
        self._content = content

        self._title_lbl = tk.Label(content, text=title, font=("Segoe UI", 13, "bold"),
                                   cursor="hand2")
        self._title_lbl.pack(anchor="w")

        self._desc_lbl = tk.Label(content, text=desc, font=("Segoe UI", 9),
                                  justify="left", cursor="hand2")
        self._desc_lbl.pack(anchor="w", pady=(8, 0))

        self._bind_click(command)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def set_font_scale(self, scale):
        scale = max(0.6, min(1.6, scale))
        tf = ("Segoe UI", max(8, int(13 * scale)), "bold")
        df = ("Segoe UI", max(7, int(9 * scale)))
        self._title_lbl.configure(font=tf)
        self._desc_lbl.configure(font=df)
        px = (max(10, int(self._base_padx[0] * scale)), max(10, int(self._base_padx[1] * scale)))
        py = (max(10, int(self._base_pady[0] * scale)), max(10, int(self._base_pady[1] * scale)))
        self._content.pack_configure(padx=px, pady=py)

    def _hover(self, enter):
        t = self._theme_data
        if not t:
            return
        bg = t["card_hover_bg"] if enter else t["card_bg"]
        accent_w = 7 if enter else 5
        self._accent.configure(width=accent_w)
        self.configure(bg=bg)
        self._content.configure(bg=bg)
        for w in self._content.winfo_children():
            try:
                w.configure(bg=bg)
            except:
                pass

    def _bind_click(self, cmd):
        targets = [self, self._content]
        for t_ in self._content.winfo_children():
            targets.append(t_)
        for t_ in targets:
            t_.bind("<Button-1>", lambda e, c=cmd: c())

    def theme(self, t):
        self._theme_data = t
        self.configure(highlightbackground=t["border"])
        self._accent.configure(bg=t["accent"])
        for child in self.winfo_children():
            if isinstance(child, tk.Frame) and child is not self._accent:
                child.configure(bg=t["card_bg"])
                for sub in child.winfo_children():
                    try:
                        sub.configure(bg=t["card_bg"])
                    except:
                        pass

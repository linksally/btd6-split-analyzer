import os
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import ctypes
from ctypes import wintypes

from themes import THEMES, DEFAULT_THEME
from core import (
    SCRIPT_DIR,
    MIN_TIME_SPLITS, MEDIUM_TIME_SPLITS, HARD_TIME_SPLITS, IMPOPPABLE_TIME_SPLITS,
    load_splits, load_splits_text, analyze, fmt, Summary, ComparisonRow,
    build_export_text, export_report,
    set_tesseract_path, ocr_supported,
    set_export_path, get_export_path,
)
from widgets import DataTable, StatCard, MenuCard

CATEGORIES = [
    ("Easy", 1, 40),
    ("Medium", 41, 60),
    ("Hard", 61, 80),
    ("Impoppable", 81, 100),
    ("CHIMPS", 1, 100),
]

CATEGORY_MIN_TIMES = {
    "Easy": MIN_TIME_SPLITS,
    "Medium": MEDIUM_TIME_SPLITS,
    "Hard": HARD_TIME_SPLITS,
    "Impoppable": IMPOPPABLE_TIME_SPLITS,
    "CHIMPS": IMPOPPABLE_TIME_SPLITS,
}

PREFS_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), ".btd6_prefs.json")
SESSION_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), ".btd6_session.json")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BTD6 Split Analyzer")
        self.minsize(900, 500)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.A = []
        self.B = []
        self.nameA = ""
        self.nameB = ""
        self.rows = []
        self.summary = None
        self._easy_mode = False
        self._current_page = None
        self._theme_name = DEFAULT_THEME
        self._selected_cat = ""
        self._font_size = 10
        self._tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        self._recent_files = []
        self._export_path = ""

        self._load_prefs()
        self._build_topbar()
        self._build_statusbar()
        self._build_pages()
        self._show_page("menu")
        self._apply_theme()
        self._bind_shortcuts()
        self._setup_drag_drop()
        self._maybe_restore_session()

    def _setup_drag_drop(self):
        try:
            hwnd = self.winfo_id()
            ctypes.windll.shell32.DragAcceptFiles(hwnd, True)
            GWL_WNDPROC = -4
            WM_DROPFILES = 0x0233
            WndProc = ctypes.WINFUNCTYPE(wintypes.LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            def drag_handler(hwnd, msg, wp, lp):
                if msg == WM_DROPFILES:
                    hDrop = wintypes.HANDLE(wp)
                    count = ctypes.windll.shell32.DragQueryFileW(hDrop, -1, None, 0)
                    files = []
                    for i in range(count):
                        buf = ctypes.create_unicode_buffer(260)
                        ctypes.windll.shell32.DragQueryFileW(hDrop, i, buf, 260)
                        files.append(buf.value)
                    ctypes.windll.shell32.DragFinish(hDrop)
                    if files:
                        self.after(0, self._handle_dropped_files, files)
                    return 0
                return ctypes.windll.user32.CallWindowProcW(self._old_wndproc, hwnd, msg, wp, lp)
            self._drag_proc = WndProc(drag_handler)
            self._old_wndproc = ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, self._drag_proc)
        except Exception:
            pass

    def _handle_dropped_files(self, files):
        valid = [f for f in files if os.path.isfile(f)]
        if not valid:
            return
        if len(valid) >= 2:
            self._load_run_vs_run(valid[0], valid[1])
        else:
            self._load_run_vs_min(valid[0])

    def _add_recent(self, path):
        path = os.path.abspath(path)
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files[:] = self._recent_files[:8]
        self._save_prefs()
        if hasattr(self, "_recent_frame"):
            self._rebuild_recent()

    def _rebuild_recent(self):
        if not hasattr(self, "_recent_frame"):
            return
        for w in self._recent_frame.winfo_children():
            w.destroy()
        t = self._theme()

        hdr_row = tk.Frame(self._recent_frame, bg=t["bg"])
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="Recent Runs", font=("Segoe UI", 9, "bold"),
                 anchor="w", bg=t["bg"], fg=t["label_fg"]).pack(side="left")
        if self._recent_files:
            tk.Label(hdr_row, text="[Clear]", font=("Segoe UI", 8),
                     anchor="e", bg=t["bg"], fg=t["sub_fg"], cursor="hand2").pack(side="right")
            clear_lbl = hdr_row.winfo_children()[-1]
            def clear_recent(e=None):
                self._recent_files.clear()
                self._save_prefs()
                self._rebuild_recent()
            clear_lbl.bind("<Button-1>", clear_recent)

        if not self._recent_files:
            tk.Label(self._recent_frame, text="No recent runs", font=("Segoe UI", 9),
                     bg=t["bg"], fg=t["sub_fg"], anchor="w").pack(fill="x", pady=(4, 0))
            return

        max_h = min(len(self._recent_files), 4) * 28 + 4
        cframe = tk.Frame(self._recent_frame, bg=t["bg"])
        cframe.pack(fill="x", pady=(4, 0))
        cframe.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(cframe, height=max_h, bg=t["bg"],
                           highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="ew")

        vsb = ttk.Scrollbar(cframe, orient="vertical", command=canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=vsb.set)

        inner = tk.Frame(canvas, bg=t["bg"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for path in self._recent_files:
            name = os.path.basename(path)
            row = tk.Frame(inner, bg=t["card_bg"], highlightthickness=1,
                           highlightbackground=t["border"])
            row.pack(fill="x", pady=2, padx=2)
            tk.Label(row, text=name, font=("Segoe UI", 9), bg=t["card_bg"], fg=t["fg"],
                     anchor="w", cursor="hand2").pack(side="left", padx=10, pady=4)
            row.bind("<Button-1>", lambda e, p=path: self._load_run_vs_min(p))
            for ch in row.winfo_children():
                ch.bind("<Button-1>", lambda e, p=path: self._load_run_vs_min(p))

            def make_hover(rf):
                def on_enter(e):
                    try:
                        for c in rf.winfo_children():
                            c.configure(bg=t["card_hover_bg"])
                        rf.configure(bg=t["card_hover_bg"])
                    except:
                        pass
                def on_leave(e):
                    try:
                        for c in rf.winfo_children():
                            c.configure(bg=t["card_bg"])
                        rf.configure(bg=t["card_bg"])
                    except:
                        pass
                rf.bind("<Enter>", on_enter)
                rf.bind("<Leave>", on_leave)
            make_hover(row)

        # Sync inner frame width to canvas
        def sync_width(e):
            canvas.itemconfig("inner", width=e.width)
        canvas.bind("<Configure>", sync_width)

    def _load_run_vs_run(self, pathA, pathB):
        try:
            self.A = load_splits(pathA)
            self.B = load_splits(pathB)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load:\n{e}")
            self._set_status("Error loading files")
            return
        if not self.A or not self.B:
            messagebox.showerror("Error", "Could not read one or both files.")
            self._set_status("Failed to read split data")
            return
        self.nameA = os.path.basename(pathA)
        self.nameB = os.path.basename(pathB)
        self._easy_mode = False
        self._auto_detect_cat(self.A, self.B)
        self._add_recent(pathA)
        self._add_recent(pathB)
        self._set_status(f"Comparing {self.nameA} vs {self.nameB}")
        self._render()

    def _load_run_vs_min(self, path):
        try:
            splits = load_splits(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load:\n{e}")
            self._set_status("Error loading file")
            return
        if not splits:
            messagebox.showerror("Error", "Could not read the selected file.")
            self._set_status("Failed to read split data")
            return
        self._auto_detect_cat(splits, splits)
        if self._selected_cat not in CATEGORY_MIN_TIMES:
            names = "/".join(CATEGORY_MIN_TIMES.keys())
            messagebox.showinfo("Min Time",
                f"Select a category with min time data ({names}) from the dropdown.")
            self._set_status("No min time data for selected category")
            return
        cat = self._selected_cat
        self.A = CATEGORY_MIN_TIMES[cat]
        self.B = splits
        self.nameA = f"Best Possible Time ({cat})"
        self.nameB = os.path.basename(path)
        self._easy_mode = True
        self._add_recent(path)
        self._set_status(f"Comparing your run against the best possible time ({cat})")
        self._render()

    def _theme(self):
        return THEMES.get(self._theme_name, THEMES[DEFAULT_THEME])

    # =====================
    # PREFERENCES
    # =====================
    def _load_prefs(self):
        self._theme_name = DEFAULT_THEME
        geo = "1200x750"
        fs = 10
        try:
            with open(PREFS_PATH, "r") as f:
                d = json.load(f)
            if d.get("theme") in THEMES:
                self._theme_name = d["theme"]
            if d.get("geometry"):
                geo = d["geometry"]
            if d.get("tesseract_path"):
                self._tess_path = d["tesseract_path"]
            self._export_path = d.get("export_path", "")
            self._recent_files = d.get("recent", [])[:8]
            if d.get("font_size"):
                fs = int(d["font_size"])
        except:
            pass
        self._font_size = max(8, min(24, fs))
        set_tesseract_path(self._tess_path)
        if self._export_path:
            set_export_path(self._export_path)

    def _save_prefs(self):
        try:
            d = {
                "theme": self._theme_name,
                "geometry": self.geometry(),
                "font_size": self._font_size,
                "tesseract_path": self._tess_path,
                "recent": self._recent_files[:8],
                "export_path": self._export_path,
            }
            with open(PREFS_PATH, "w") as f:
                json.dump(d, f)
        except:
            self._set_status("Warning: could not save preferences")

    def set_theme(self, name):
        if name in THEMES:
            self._theme_name = name
            self._apply_theme()
            self._save_prefs()

    def set_font_size(self, delta):
        self._font_size = max(8, min(24, self._font_size + delta))
        if hasattr(self, "_table"):
            self._table.set_font_size(self._font_size)
        self._save_prefs()

    # =====================
    # SESSION
    # =====================
    def _save_session(self):
        if not self.rows or not self.summary:
            return
        try:
            rows_data = [
                {
                    "round": r.round, "a_frames": r.a_frames,
                    "a_time": r.a_time, "cum_a": r.cum_a,
                    "b_frames": r.b_frames, "b_time": r.b_time,
                    "cum_b": r.cum_b, "df": r.df, "dt": r.dt,
                    "win": r.win, "mom": r.mom,
                }
                for r in self.rows
            ]
            d = {
                "nameA": self.nameA, "nameB": self.nameB,
                "easy_mode": self._easy_mode,
                "selected_cat": self._selected_cat,
                "rows": rows_data,
                "summary": {
                    "a_wins": self.summary.a_wins,
                    "b_wins": self.summary.b_wins,
                    "ties": self.summary.ties,
                    "ta": self.summary.ta, "tb": self.summary.tb,
                    "ttA": self.summary.ttA, "ttB": self.summary.ttB,
                    "total_rounds": self.summary.total_rounds,
                },
                "font_size": self._font_size,
            }
            with open(SESSION_PATH, "w") as f:
                json.dump(d, f, indent=2)
        except:
            pass

    def _maybe_restore_session(self):
        if not os.path.exists(SESSION_PATH):
            return
        try:
            with open(SESSION_PATH, "r") as f:
                d = json.load(f)
        except:
            return
        if not isinstance(d, dict) or "rows" not in d:
            return
        result = messagebox.askyesno(
            "Restore Session",
            "A previous analysis session was found.\nRestore it?",
        )
        if not result:
            return

        try:
            self.rows = [ComparisonRow(**r) for r in d["rows"]]
            self.summary = Summary(**d["summary"])
            self.nameA = d.get("nameA", "")
            self.nameB = d.get("nameB", "")
            self._easy_mode = d.get("easy_mode", False)
            self._selected_cat = d.get("selected_cat", "")
            if "font_size" in d:
                self._font_size = max(8, min(24, int(d["font_size"])))
        except:
            self._set_status("Could not restore session")
            return

        self._render_restored()

    def _render_restored(self):
        t = self._theme()
        self._table._easy_mode = self._easy_mode
        self._table.set_font_size(self._font_size)
        self._table.set_data([r.__dict__ for r in self.rows])

        self._populate_summary()

        s = self.summary
        time_delta = s.ttA - s.ttB
        time_winner = "T" if time_delta == 0 else ("A" if time_delta < 0 else "B")

        is_easy = self._easy_mode
        card_labels = [
            "You Win" if is_easy else "Run A Wins",
            "Min Wins" if is_easy else "Run B Wins",
            "Tied Rounds",
            "Best Margin",
        ]
        for card, label in zip(self._stat_cards, card_labels):
            card.lbl.configure(text=label)

        card_vals = [
            (str(s.a_wins), "a"),
            (str(s.b_wins), "b"),
            (str(s.ties), "t"),
        ]
        if time_winner == "T":
            card_vals.append(("TIE", "t"))
        else:
            card_vals.append((f"{time_winner} by {abs(time_delta):.3f}s",
                              "a" if time_winner == "A" else "b"))
        for card, (val, tag) in zip(self._stat_cards, card_vals):
            card.val.configure(text=val)
            card.val._fg_tag = tag

        self._results_header.configure(
            text=f"{self.nameA}  vs  {self.nameB}  -  {s.total_rounds} rounds"
        )
        self._show_page("results")
        self.notebook.select(0)
        self.update_idletasks()
        ww = self._table._canvas.winfo_width()
        self._table._on_canvas_resize(type("ev", (), {"width": ww})())
        self._set_status("Session restored")

    # =====================
    # SETTINGS PAGE
    # =====================
    def _build_settings_page(self):
        f = self._frame_settings
        t = self._theme()

        tk.Button(f, text="\u2190 Back", width=8,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=lambda: self._show_page("menu")
                  ).pack(anchor="nw", padx=22, pady=(16, 0))

        container = tk.Frame(f)
        container.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(container, text="Settings", font=("Segoe UI", 22, "bold"),
                 bg=t["bg"], fg=t["fg"]).pack(anchor="w")

        tk.Label(container, text="Tesseract OCR Path:", font=("Segoe UI", 10, "bold"),
                 bg=t["bg"], fg=t["fg"], anchor="w").pack(fill="x", pady=(22, 4))

        tess_frame = tk.Frame(container, bg=t["bg"])
        tess_frame.pack(fill="x")
        tess_frame.grid_columnconfigure(0, weight=1)

        tess_var = tk.StringVar(value=self._tess_path)
        tk.Entry(tess_frame, textvariable=tess_var,
                 bg=t["text_bg"], fg=t["text_fg"],
                 font=("Segoe UI", 9), relief="flat"
                 ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_tess():
            root = tk.Toplevel(self)
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                parent=root,
                title="Select tesseract.exe",
                filetypes=[("Executable", "tesseract.exe"), ("All Files", "*.*")]
            )
            root.destroy()
            if path:
                tess_var.set(path)

        tk.Button(tess_frame, text="Browse", command=browse_tess,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 9)).grid(row=0, column=1)

        tk.Label(container, text="Table Font Size:", font=("Segoe UI", 10, "bold"),
                 bg=t["bg"], fg=t["fg"], anchor="w").pack(fill="x", pady=(16, 4))

        fs_frame = tk.Frame(container, bg=t["bg"])
        fs_frame.pack(fill="x")

        def apply_fs():
            new_fs = int(fs_lbl.cget("text"))
            self._font_size = new_fs
            if hasattr(self, "_table"):
                self._table.set_font_size(new_fs)
        def zoom_in():
            cur = int(fs_lbl.cget("text"))
            if cur < 24:
                fs_lbl.configure(text=str(cur + 1))
                apply_fs()
        def zoom_out():
            cur = int(fs_lbl.cget("text"))
            if cur > 8:
                fs_lbl.configure(text=str(cur - 1))
                apply_fs()

        tk.Button(fs_frame, text="A-", width=3, command=zoom_out,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        fs_lbl = tk.Label(fs_frame, text=str(self._font_size), width=4,
                          bg=t["bg"], fg=t["fg"], font=("Segoe UI", 11, "bold"))
        fs_lbl.pack(side="left", padx=12)
        tk.Button(fs_frame, text="A+", width=3, command=zoom_in,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold")).pack(side="left")

        tk.Label(container, text="Theme:", font=("Segoe UI", 10, "bold"),
                 bg=t["bg"], fg=t["fg"], anchor="w").pack(fill="x", pady=(16, 4))

        self._settings_theme_var = tk.StringVar(value=self._theme_name)
        theme_combo = ttk.Combobox(container, textvariable=self._settings_theme_var,
                                    values=list(THEMES.keys()),
                                    state="readonly", width=22,
                                    font=("Segoe UI", 10))
        theme_combo.pack(fill="x")
        theme_combo.bind("<<ComboboxSelected>>",
                         lambda e: self.set_theme(self._settings_theme_var.get()))

        tk.Label(container, text="Export Folder:", font=("Segoe UI", 10, "bold"),
                 bg=t["bg"], fg=t["fg"], anchor="w").pack(fill="x", pady=(16, 4))

        exp_frame = tk.Frame(container, bg=t["bg"])
        exp_frame.pack(fill="x")
        exp_frame.grid_columnconfigure(0, weight=1)

        self._export_path_var = tk.StringVar(value=self._export_path or get_export_path())
        tk.Entry(exp_frame, textvariable=self._export_path_var,
                 bg=t["text_bg"], fg=t["text_fg"],
                 font=("Segoe UI", 9), relief="flat"
                 ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        def browse_export():
            root = tk.Toplevel(self)
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askdirectory(parent=root, title="Select export folder")
            root.destroy()
            if path:
                self._export_path_var.set(path)

        tk.Button(exp_frame, text="Browse", command=browse_export,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 9)).grid(row=0, column=1)

        # OCR status
        ocr_ok = ocr_supported()
        status_text = "OCR: Available" if ocr_ok else "OCR: Not available (pip install pytesseract pillow)"
        status_color = t["success"] if ocr_ok else t["danger"]
        tk.Label(container, text=status_text, bg=t["bg"], fg=status_color,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(16, 0))

        # Clear cache
        tk.Button(container, text="Clear Cache", command=self._clear_cache,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 9)).pack(fill="x", pady=(16, 0))

        # Save / Back
        btn_row = tk.Frame(container, bg=t["bg"])
        btn_row.pack(fill="x", pady=(24, 0))

        def save_settings():
            self._tess_path = tess_var.get().strip()
            set_tesseract_path(self._tess_path)
            self._export_path = self._export_path_var.get().strip()
            set_export_path(self._export_path)
            apply_fs()
            self._save_prefs()
            self._set_status(f"Settings saved (font size: {self._font_size})")
            self._show_page("menu")

        tk.Button(btn_row, text="Save", width=10, command=save_settings,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side="right", padx=(8, 0))
        tk.Button(btn_row, text="Back", width=10,
                  command=lambda: self._show_page("menu"),
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side="right")

    def _clear_cache(self):
        self._recent_files.clear()
        try:
            if os.path.exists(SESSION_PATH):
                os.remove(SESSION_PATH)
        except:
            pass
        self._save_prefs()
        if hasattr(self, "_recent_frame"):
            self._rebuild_recent()
        self._set_status("Cache cleared (recent runs + session)")

    def _open_settings(self):
        self._show_page("settings")

    # =====================
    # UI BUILDING
    # =====================
    def _build_topbar(self):
        self._topbar = tk.Frame(self, height=56)
        self._topbar.pack(side="top", fill="x")
        self._topbar.pack_propagate(False)

        inner = tk.Frame(self._topbar, height=56)
        inner.pack(fill="x", side="left", expand=True)
        inner.pack_propagate(False)
        self._topbar_inner = inner

        self._topbar_title = tk.Label(inner, text="SPLIT ANALYZER",
                                       font=("Segoe UI", 14, "bold"))
        self._topbar_title.pack(side="left", padx=(22, 8))

        self._topbar_subtitle = tk.Label(inner, text="speedrun split comparator",
                                          font=("Segoe UI", 9))
        self._topbar_subtitle.pack(side="left")

        right_frame = tk.Frame(self._topbar, height=56)
        right_frame.pack(side="right", fill="y")
        self._topbar_right = right_frame

        self._btn_settings = tk.Button(right_frame, text="\u2699", width=3,
                                        font=("Segoe UI", 16), cursor="hand2",
                                        command=self._open_settings, relief="flat")
        self._btn_settings.pack(side="right", padx=(0, 14), pady=(0, 2))

        self._topbar_sep = tk.Frame(self._topbar, height=1)
        self._topbar_sep.pack(side="bottom", fill="x")

    def _build_statusbar(self):
        self._statusbar = tk.Frame(self, height=26)
        self._statusbar.pack(side="bottom", fill="x")
        self._statusbar.pack_propagate(False)

        self._status_lbl = tk.Label(self._statusbar, text="Ready",
                                     font=("Segoe UI", 9), anchor="w")
        self._status_lbl.pack(side="left", padx=(12, 0), fill="x", expand=True)

        self._status_sep = tk.Frame(self._statusbar, height=1)
        self._status_sep.pack(side="top", fill="x")

    def _set_status(self, msg):
        if hasattr(self, "_status_lbl"):
            self._status_lbl.configure(text=msg)

    def _build_pages(self):
        self._frame_menu = tk.Frame(self)
        self._frame_results = tk.Frame(self)
        self._frame_settings = tk.Frame(self)
        self._build_menu_page()
        self._build_results_page()
        self._build_settings_page()

    def _show_page(self, page):
        if self._current_page:
            getattr(self, f"_frame_{self._current_page}").pack_forget()
        self._current_page = page
        getattr(self, f"_frame_{page}").pack(fill="both", expand=True)
        if page == "menu":
            self._set_status("\U0001F4CB Ctrl+V: Paste  |  \u2715 Ctrl+Q: Quit")
        elif page == "results":
            self._set_status("\u2190 Esc: Menu  |  \u2715 Ctrl+Q: Quit")
        elif page == "settings":
            self._set_status("\u2190 Esc: Menu  |  \u2715 Ctrl+Q: Quit")

    # =====================
    # MENU PAGE
    # =====================
    def _build_menu_page(self):
        f = self._frame_menu
        container = tk.Frame(f)
        container.place(relx=0.5, rely=0.38, anchor="center")

        self._menu_title = tk.Label(container, text="SPLIT ANALYZER",
                                    font=("Segoe UI", 22, "bold"))
        self._menu_title.pack()
        self._menu_subtitle = tk.Label(container, text="Compare speedrun splits across multiple runs",
                                       font=("Segoe UI", 9))
        self._menu_subtitle.pack(pady=(4, 24))

        self._menu_btn_frame = tk.Frame(container)
        self._menu_btn_frame.pack(fill="x", padx=40)
        for i in range(3):
            self._menu_btn_frame.grid_columnconfigure(i, weight=1, uniform="card")

        cards_data = [
            ("\U0001F4C1  Compare Two Runs", "Pick any two split files and see\nwho wins each round",
             self.run_vs_run),
            ("\u23F1  Min Time", "See how your run stacks up against\nthe best possible time",
             self.run_vs_min),
            ("\U0001F4CB  Paste Splits", "Copy and paste split data directly\ninstead of picking a file",
             self._paste_splits),
        ]

        self._menu_cards = []
        for i, (title, desc, cmd) in enumerate(cards_data):
            card = MenuCard(self._menu_btn_frame, title, desc, cmd)
            card.grid(row=0, column=i, padx=6, sticky="ew")
            self._menu_cards.append(card)

        self._menu_container = container
        f.bind("<Configure>", self._resize_menu)

        cat_frame = tk.Frame(container)
        cat_frame.pack(pady=(28, 0))

        tk.Label(cat_frame, text="Category:", font=("Segoe UI", 11, "bold")
                 ).pack(side="left", padx=(0, 14))

        self._cat_combo = ttk.Combobox(cat_frame, values=[c[0] for c in CATEGORIES],
                                        state="readonly", width=14,
                                        font=("Segoe UI", 11))
        self._cat_combo.set(self._selected_cat)
        self._cat_combo.bind("<<ComboboxSelected>>",
                             lambda e: self._set_cat(self._cat_combo.get()))
        self._cat_combo.pack(side="left")

        self._update_cat_combo_theme()

        # Bottom section — recent runs + credit
        bottom = tk.Frame(f)
        bottom.pack(side="bottom", fill="x")
        self._menu_bottom = bottom

        sep = tk.Frame(bottom, height=1)
        sep.pack(fill="x")
        self._menu_bottom_sep = sep

        recent_frame = tk.Frame(bottom)
        recent_frame.pack(fill="x", padx=60, pady=(12, 8))
        self._recent_frame = recent_frame

        tk.Label(bottom, text="created by linksally",
                 font=("Segoe UI", 9)).pack(pady=(0, 10))

    def _resize_menu(self, e=None):
        if not hasattr(self, "_menu_container") or self._current_page != "menu":
            return
        w = self.winfo_width()
        scale = w / 900
        scale = max(0.5, min(1.4, scale))
        tf = ("Segoe UI", max(11, int(22 * scale)), "bold")
        sf = ("Segoe UI", max(7, int(9 * scale)))
        self._menu_title.configure(font=tf)
        self._menu_subtitle.configure(font=sf)
        self._menu_subtitle.pack_configure(pady=(max(2, int(4 * scale)), max(12, int(24 * scale))))
        self._menu_btn_frame.pack_configure(padx=max(16, int(32 * scale)))
        for card in self._menu_cards:
            card.set_font_scale(scale)

    def _set_cat(self, name):
        self._selected_cat = name

    def _auto_detect_cat(self, dataA, dataB):
        n = max(len(dataA), len(dataB))
        for cat_name, lo, hi in CATEGORIES:
            if lo <= n <= hi:
                self._selected_cat = cat_name
                if hasattr(self, "_cat_combo"):
                    self._cat_combo.set(cat_name)
                return
        self._selected_cat = ""
        if hasattr(self, "_cat_combo"):
            self._cat_combo.set("")

    def _update_cat_combo_theme(self):
        t = self._theme()
        if hasattr(self, "_cat_combo"):
            style = ttk.Style(self)
            style.configure("TCombobox", fieldbackground=t["button_bg"],
                            foreground=t["fg"], arrowcolor=t["sub_fg"],
                            selectbackground=t["selectbg"])
            style.map("TCombobox", fieldbackground=[("readonly", t["button_bg"])],
                      foreground=[("readonly", t["fg"])])

    # =====================
    # RESULTS PAGE
    # =====================
    def _build_results_page(self):
        f = self._frame_results
        f.grid_rowconfigure(2, weight=1)
        f.grid_columnconfigure(0, weight=1)

        top = tk.Frame(f, height=48)
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 0))
        top.pack_propagate(False)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(3, weight=1)

        self._btn_back = tk.Button(top, text="\u2190 Back", width=8,
                                    font=("Segoe UI", 10), cursor="hand2",
                                    command=lambda: self._show_page("menu"))
        self._btn_back.grid(row=0, column=0, padx=(0, 8))

        self._results_header = tk.Label(top, text="", font=("Segoe UI", 15, "bold"),
                                         anchor="center", cursor="hand2")
        self._results_header.grid(row=0, column=2)
        self._results_header.bind("<Double-Button-1>", lambda e: self._rename_runs())

        btn_right = tk.Frame(top)
        btn_right.grid(row=0, column=4, sticky="e")
        self._btn_export = tk.Button(btn_right, text="\u2b07 Export", width=9,
                                      font=("Segoe UI", 10), cursor="hand2",
                                      command=self.export)
        self._btn_export.pack(side="left", padx=2)

        self._btn_copy = tk.Button(btn_right, text="\U0001F4CB Copy", width=9,
                                    font=("Segoe UI", 10), cursor="hand2",
                                    command=self._copy_table)
        self._btn_copy.pack(side="left", padx=2)

        self._btn_quit = tk.Button(btn_right, text="\u2715", width=4,
                                    font=("Segoe UI", 12), cursor="hand2",
                                    command=self._on_close)
        self._btn_quit.pack(side="left", padx=(2, 0))

        dash = tk.Frame(f)
        dash.grid(row=1, column=0, sticky="ew", padx=22, pady=(18, 12))
        for i in range(4):
            dash.grid_columnconfigure(i, weight=1)

        self._stat_cards = []
        for label in ["Run A Wins", "Run B Wins", "Tied Rounds", "Best Margin"]:
            card = StatCard(dash, label, "-", "fg")
            card.grid(row=0, column=len(self._stat_cards), padx=7, sticky="ew")
            self._stat_cards.append(card)

        nbc = tk.Frame(f)
        nbc.grid(row=2, column=0, sticky="nsew", padx=22, pady=(8, 18))
        nbc.grid_columnconfigure(0, weight=1)
        nbc.grid_rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(nbc)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Table tab
        self._build_table_tab()

        # Summary tab
        summary_frame = tk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="  Summary  ")
        summary_frame.grid_rowconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(0, weight=1)

        self._summary_canvas = tk.Canvas(summary_frame, highlightthickness=0, borderwidth=0)
        self._summary_canvas.grid(row=0, column=0, sticky="nsew")

        vsb_s = ttk.Scrollbar(summary_frame, orient="vertical",
                               command=self._summary_canvas.yview)
        vsb_s.grid(row=0, column=1, sticky="ns")
        self._summary_canvas.configure(yscrollcommand=vsb_s.set)

        self._summary_inner = tk.Frame(self._summary_canvas)
        self._summary_inner.bind("<Configure>",
                                 lambda e: self._summary_canvas.configure(
                                     scrollregion=self._summary_canvas.bbox("all")))
        self._summary_canvas.create_window((0, 0), window=self._summary_inner,
                                            anchor="nw", tags="inner")

        self._summary_placeholder = tk.Label(
            self._summary_inner,
            text="Welcome to BTD6 Split Analyzer!\n\n"
                 "To get started:\n"
                 "  Choose a split file from the main menu\n"
                 "  Compare two runs side by side\n"
                 "  Or test your run against the best possible time\n\n"
                 "Results will appear here with a breakdown\n"
                 "of every round, highlights, and averages.",
            font=("Segoe UI", 11), justify="left", anchor="nw")
        self._summary_placeholder.pack(fill="both", expand=True, padx=24, pady=24)

    def _build_table_tab(self):
        table_tab = tk.Frame(self.notebook)
        self.notebook.add(table_tab, text="  Comparison Table  ")
        table_tab.grid_rowconfigure(1, weight=1)
        table_tab.grid_columnconfigure(0, weight=1)

        # Filter bar
        filter_bar = tk.Frame(table_tab)
        filter_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        filter_bar.grid_columnconfigure(5, weight=1)

        t = self._theme()

        # Win filter
        tk.Label(filter_bar, text="Win:", font=("Segoe UI", 9, "bold"),
                 bg=t["bg"], fg=t["fg"]).grid(row=0, column=0, padx=(4, 4))

        self._filter_win_var = tk.StringVar(value="All")
        win_filter = ttk.Combobox(filter_bar, textvariable=self._filter_win_var,
                                   values=["All", "A", "B", "T"],
                                   state="readonly", width=6, font=("Segoe UI", 9))
        win_filter.grid(row=0, column=1, padx=(0, 12))
        win_filter.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        # Round range
        tk.Label(filter_bar, text="Rounds:", font=("Segoe UI", 9, "bold"),
                 bg=t["bg"], fg=t["fg"]).grid(row=0, column=2, padx=(0, 4))

        self._filter_from_var = tk.StringVar()
        from_entry = tk.Entry(filter_bar, textvariable=self._filter_from_var,
                               width=5, font=("Segoe UI", 9),
                               bg=t["text_bg"], fg=t["text_fg"], relief="flat")
        from_entry.grid(row=0, column=3)
        from_entry.bind("<Return>", lambda e: self._apply_filter())

        tk.Label(filter_bar, text="-", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 9)).grid(row=0, column=4, padx=2)

        self._filter_to_var = tk.StringVar()
        to_entry = tk.Entry(filter_bar, textvariable=self._filter_to_var,
                             width=5, font=("Segoe UI", 9),
                             bg=t["text_bg"], fg=t["text_fg"], relief="flat")
        to_entry.grid(row=0, column=5, padx=(0, 12))
        to_entry.bind("<Return>", lambda e: self._apply_filter())

        # Round search
        tk.Label(filter_bar, text="Search Round:", font=("Segoe UI", 9, "bold"),
                 bg=t["bg"], fg=t["fg"]).grid(row=0, column=6, padx=(0, 4))

        self._search_round_var = tk.StringVar()
        search_entry = tk.Entry(filter_bar, textvariable=self._search_round_var,
                                 width=6, font=("Segoe UI", 9),
                                 bg=t["text_bg"], fg=t["text_fg"], relief="flat")
        search_entry.grid(row=0, column=7, padx=(0, 4))
        search_entry.bind("<Return>", lambda e: self._go_to_round())

        tk.Button(filter_bar, text="\U0001F50D", width=3,
                  font=("Segoe UI", 12), cursor="hand2", command=self._go_to_round,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0).grid(row=0, column=8, padx=(0, 12))

        # Font size controls
        tk.Button(filter_bar, text="A-", width=3,
                  font=("Segoe UI", 8, "bold"), cursor="hand2",
                  command=lambda: self._font_size_change(-1),
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0).grid(row=0, column=9, padx=(0, 2))
        self._fs_label = tk.Label(filter_bar, text=str(self._font_size), width=3,
                                  bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9, "bold"))
        self._fs_label.grid(row=0, column=10, padx=2)
        tk.Button(filter_bar, text="A+", width=3,
                  font=("Segoe UI", 8, "bold"), cursor="hand2",
                  command=lambda: self._font_size_change(+1),
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0).grid(row=0, column=11, padx=(2, 4))

        # Table
        tbl_cols = [
            ("round", "Round", 50),
            ("a_frames", "A Fr", 65),
            ("a_time", "A Time", 95),
            ("cum_a", "A Cum", 95),
            ("b_frames", "B Fr", 65),
            ("b_time", "B Time", 95),
            ("cum_b", "B Cum", 95),
            ("df", "D Frames", 75),
            ("dt", "D Time", 85),
            ("win", "Winner", 60),
            ("mom", "Momentum", 80),
        ]
        self._table = DataTable(table_tab, tbl_cols, font_size=self._font_size)
        self._table.grid(row=1, column=0, sticky="nsew")

    # =====================
    # FILTER / SEARCH / ZOOM
    # =====================
    def _apply_filter(self):
        win = self._filter_win_var.get()
        win = None if win == "All" else win
        try:
            rf = int(self._filter_from_var.get()) if self._filter_from_var.get().strip() else None
        except:
            rf = None
        try:
            rt = int(self._filter_to_var.get()) if self._filter_to_var.get().strip() else None
        except:
            rt = None
        self._table.set_filter(win=win, round_from=rf, round_to=rt)

    def _go_to_round(self):
        raw = self._search_round_var.get().strip()
        if not raw:
            self._table.highlight_round(None)
            self._set_status("Highlight cleared")
            return
        try:
            rnd = int(raw)
        except:
            self._set_status("Enter a valid round number")
            return
        self._table.highlight_round(rnd)
        self._set_status(f"Highlighted round {rnd}")

    def _font_size_change(self, delta):
        self.set_font_size(delta)
        if hasattr(self, "_fs_label"):
            self._fs_label.configure(text=str(self._font_size))

    # =====================
    # ACTIONS
    # =====================
    def _pick_file(self, title):
        root = tk.Toplevel(self)
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            parent=root,
            title=title,
            filetypes=[("All Files", "*.*"),
                       ("Split / Text / Image Files",
                        "*.txt *.log *.csv *.tsv *.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        root.destroy()
        return path

    def run_vs_run(self):
        pathA = self._pick_file("Choose the first run (Run A)")
        if not pathA:
            return
        pathB = self._pick_file("Choose the second run (Run B)")
        if not pathB:
            return
        try:
            self.A = load_splits(pathA)
            self.B = load_splits(pathB)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load split files:\n{e}")
            self._set_status("Error loading files")
            return
        if not self.A or not self.B:
            messagebox.showerror("Error", "Could not read one or both files.")
            self._set_status("Failed to read split data")
            return
        self.nameA = os.path.basename(pathA)
        self.nameB = os.path.basename(pathB)
        self._easy_mode = False
        self._auto_detect_cat(self.A, self.B)
        self._add_recent(pathA)
        self._add_recent(pathB)
        self._set_status(f"Comparing {self.nameA} vs {self.nameB}")
        self._render()

    def run_vs_min(self):
        path = self._pick_file("Choose your run")
        if not path:
            return
        try:
            splits = load_splits(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load split file:\n{e}")
            self._set_status("Error loading file")
            return
        if not splits:
            messagebox.showerror("Error", "Could not read the selected file.")
            self._set_status("Failed to read split data")
            return
        self._auto_detect_cat(splits, splits)
        if self._selected_cat not in CATEGORY_MIN_TIMES:
            names = "/".join(CATEGORY_MIN_TIMES.keys())
            messagebox.showinfo("Min Time",
                f"Select a category with min time data ({names}) from the dropdown.")
            self._set_status("No min time data for selected category")
            return
        cat = self._selected_cat
        self.A = CATEGORY_MIN_TIMES[cat]
        self.B = splits
        self.nameA = f"Best Possible Time ({cat})"
        self.nameB = os.path.basename(path)
        self._easy_mode = True
        self._add_recent(path)
        self._set_status(f"Comparing your run against the best possible time ({cat})")
        self._render()

    def _paste_splits(self):
        d = tk.Toplevel(self)
        d.title("Paste Splits")
        d.geometry("500x400")
        d.transient(self)
        d.grab_set()
        d.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        d.geometry(f"+{x}+{y}")

        t = self._theme()
        d.configure(bg=t["bg"])

        tk.Label(d, text="Paste your split data below:", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 10)).pack(pady=(16, 8), padx=16, anchor="w")

        txt = tk.Text(d, bg=t["text_bg"], fg=t["text_fg"], font=("Consolas", 10),
                      insertbackground=t["fg"], relief="flat", borderwidth=0)
        txt.pack(fill="both", expand=True, padx=16)
        txt.focus_set()

        def submit():
            raw = txt.get("1.0", "end-1c")
            if raw.strip():
                try:
                    splits = load_splits_text(raw)
                except Exception as e:
                    messagebox.showerror("Parse Error", f"Failed to parse data:\n{e}")
                    return
                if splits:
                    self._auto_detect_cat(splits, splits)
                    if self._selected_cat in CATEGORY_MIN_TIMES:
                        self.A = CATEGORY_MIN_TIMES[self._selected_cat]
                        ref_name = self._selected_cat
                    else:
                        self.A = CATEGORY_MIN_TIMES.get("Easy", [])
                        ref_name = "Easy"
                    self.B = splits
                    self.nameA = f"Best Possible Time ({ref_name})"
                    self.nameB = "Pasted Run"
                    self._easy_mode = True
                    d.destroy()
                    self._set_status("Comparing pasted splits against best possible time")
                    self._render()
                else:
                    messagebox.showerror("Parse Error",
                                         "Could not parse the pasted text as split data.")
            else:
                messagebox.showwarning("Empty", "No text to parse.")

        btn_frame = tk.Frame(d, bg=t["bg"])
        btn_frame.pack(fill="x", padx=16, pady=12)

        btn_submit = tk.Button(btn_frame, text="Submit", width=10,
                                font=("Segoe UI", 10), cursor="hand2", command=submit,
                                bg=t["button_bg"], fg=t["button_fg"],
                                activebackground=t["selectbg"], activeforeground=t["button_fg"],
                                highlightthickness=0, bd=0, highlightbackground=t["button_bg"])
        btn_submit.pack(side="right", padx=(8, 0))

        btn_cancel = tk.Button(btn_frame, text="Cancel", width=10,
                                font=("Segoe UI", 10), cursor="hand2", command=d.destroy,
                                bg=t["button_bg"], fg=t["button_fg"],
                                activebackground=t["selectbg"], activeforeground=t["button_fg"],
                                highlightthickness=0, bd=0, highlightbackground=t["button_bg"])
        btn_cancel.pack(side="right")

        d.bind("<Escape>", lambda e: d.destroy())
        d.bind("<Return>", lambda e: submit())
        d.bind("<KP_Enter>", lambda e: submit())
        d.wait_window()

    def _render(self):
        if not self.A or not self.B:
            messagebox.showerror("Oops", "Couldn't read one of the files.")
            return

        try:
            self.rows, self.summary = analyze(self.A, self.B)
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Analysis failed:\n{e}")
            self._set_status("Analysis error")
            return

        # Filter by selected category (skip in min time mode)
        if self._selected_cat and not self._easy_mode:
            allowed = set()
            for cat_name, lo, hi in CATEGORIES:
                if cat_name == self._selected_cat:
                    for rn in range(lo, hi + 1):
                        allowed.add(rn)
                    break
            self.rows = [r for r in self.rows if r.round in allowed]
            a_w = b_w = ties = 0
            ta = tb = 0
            ttA = ttB = 0.0
            for r in self.rows:
                ta += r.a_frames
                tb += r.b_frames
                ttA += r.a_time
                ttB += r.b_time
                if r.win == "A":
                    a_w += 1
                elif r.win == "B":
                    b_w += 1
                else:
                    ties += 1
            self.summary = Summary(
                a_wins=a_w, b_wins=b_w, ties=ties,
                ta=ta, tb=tb, ttA=ttA, ttB=ttB,
                total_rounds=len(self.rows),
            )

        s = self.summary
        time_delta = s.ttA - s.ttB
        time_winner = "T" if time_delta == 0 else ("A" if time_delta < 0 else "B")

        is_easy = self._easy_mode
        card_labels = [
            "You Win" if is_easy else "Run A Wins",
            "Min Wins" if is_easy else "Run B Wins",
            "Tied Rounds",
            "Best Margin",
        ]
        for card, label in zip(self._stat_cards, card_labels):
            card.lbl.configure(text=label)

        card_vals = [
            (str(s.a_wins), "a"),
            (str(s.b_wins), "b"),
            (str(s.ties), "t"),
        ]
        if time_winner == "T":
            card_vals.append(("TIE", "t"))
        else:
            card_vals.append((f"{time_winner} by {abs(time_delta):.3f}s",
                              "a" if time_winner == "A" else "b"))

        for card, (val, tag) in zip(self._stat_cards, card_vals):
            card.val.configure(text=val)
            card.val._fg_tag = tag

        # Update table
        self._table._easy_mode = self._easy_mode
        self._table.set_font_size(self._font_size)
        self._table.set_data([r.__dict__ for r in self.rows])

        # Update summary
        self._populate_summary()

        self._results_header.configure(
            text=f"{self.nameA}  vs  {self.nameB}  -  {s.total_rounds} rounds"
        )
        self._show_page("results")
        self.notebook.select(0)
        self.update_idletasks()
        ww = self._table._canvas.winfo_width()
        self._table._on_canvas_resize(type("ev", (), {"width": ww})())

        self._save_session()

    def _rename_runs(self):
        if not self.rows:
            return
        d = tk.Toplevel(self)
        d.title("Rename Runs")
        d.geometry("400x180")
        d.transient(self)
        d.grab_set()
        t = self._theme()
        d.configure(bg=t["bg"])

        tk.Label(d, text="Run A name:", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(16, 4))
        a_var = tk.StringVar(value=self.nameA)
        tk.Entry(d, textvariable=a_var, bg=t["text_bg"], fg=t["text_fg"],
                 font=("Segoe UI", 10), relief="flat").pack(fill="x", padx=20)

        tk.Label(d, text="Run B name:", bg=t["bg"], fg=t["fg"],
                 font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(12, 4))
        b_var = tk.StringVar(value=self.nameB)
        tk.Entry(d, textvariable=b_var, bg=t["text_bg"], fg=t["text_fg"],
                 font=("Segoe UI", 10), relief="flat").pack(fill="x", padx=20)

        def save_names():
            self.nameA = a_var.get().strip() or self.nameA
            self.nameB = b_var.get().strip() or self.nameB
            s = self.summary
            self._results_header.configure(text=f"{self.nameA}  vs  {self.nameB}  -  {s.total_rounds} rounds")
            self._set_status(f"Renamed to {self.nameA} vs {self.nameB}")
            d.destroy()

        btn_f = tk.Frame(d, bg=t["bg"])
        btn_f.pack(fill="x", padx=20, pady=(16, 0))
        tk.Button(btn_f, text="OK", width=10, command=save_names,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side="right", padx=(8, 0))
        tk.Button(btn_f, text="Cancel", width=10, command=d.destroy,
                  bg=t["button_bg"], fg=t["button_fg"],
                  activebackground=t["selectbg"], activeforeground=t["button_fg"],
                  highlightthickness=0, bd=0, cursor="hand2",
                  font=("Segoe UI", 10)).pack(side="right")

        d.bind("<Escape>", lambda e: d.destroy())
        d.bind("<Return>", lambda e: save_names())
        d.wait_window()

    def _populate_summary(self):
        for w in self._summary_inner.winfo_children():
            w.destroy()

        t = self._theme()
        rows = self.rows
        s = self.summary

        bg = t["text_bg"]
        fg = t["text_fg"]
        sub = t["sub_fg"]
        ca = t["win_a"]
        cb = t["win_b"]
        ct = t["win_t"]
        is_easy = self._easy_mode

        # Stats header
        tk.Label(self._summary_inner, text="Summary", font=("Segoe UI", 16, "bold"),
                 bg=bg, fg=fg, anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        tk.Label(self._summary_inner, text=f"{self.nameA} vs {self.nameB}",
                 font=("Segoe UI", 10), bg=bg, fg=sub, anchor="w"
                 ).pack(fill="x", padx=24, pady=(0, 16))

        # Stats block
        stats_frame = tk.Frame(self._summary_inner, bg=bg)
        stats_frame.pack(fill="x", padx=24)

        def stat_row(parent, label, value, vcolor):
            row = tk.Frame(parent, bg=bg)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=("Segoe UI", 10), bg=bg, fg=fg,
                     anchor="w", width=30).pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10, "bold"), bg=bg, fg=vcolor,
                     anchor="w").pack(side="left")

        total = s.total_rounds
        stat_row(stats_frame, "Total Rounds:", str(total), fg)
        stat_row(stats_frame, "Frames:", f"{s.ta} (A) vs {s.tb} (B)", ca if s.ta < s.tb else cb)
        stat_row(stats_frame, "Time:", f"{fmt(s.ttA)} (A) vs {fmt(s.ttB)} (B)", ca if s.ttA < s.ttB else cb)
        stat_row(stats_frame, "A Wins:", str(s.a_wins), ca)
        stat_row(stats_frame, "B Wins:", str(s.b_wins), cb)
        stat_row(stats_frame, "Ties:", str(s.ties), ct)
        if total:
            apct = s.a_wins / total * 100
            bpct = s.b_wins / total * 100
            stat_row(stats_frame, "A Win Rate:", f"{apct:.1f}%", ca)
            stat_row(stats_frame, "B Win Rate:", f"{bpct:.1f}%", cb)

        if rows:
            best = max(rows, key=lambda r: r.df)
            worst = min(rows, key=lambda r: r.df)
            avg_df = sum(r.df for r in rows) / len(rows)
            avg_dt = sum(r.dt for r in rows) / len(rows)
            stat_row(stats_frame, "Avg Frame Delta:", f"{avg_df:+.1f}", ca if avg_df > 0 else (cb if avg_df < 0 else ct))
            stat_row(stats_frame, "Avg Time Delta:", f"{avg_dt:+.3f}s", ca if avg_dt > 0 else (cb if avg_dt < 0 else ct))
            stat_row(stats_frame, "Best Round for A:", f"R{best.round} ({best.df:+} fr)", ca)
            stat_row(stats_frame, "Best Round for B:", f"R{worst.round} ({worst.df:+} fr)", cb if worst.df < 0 else (ca if worst.df > 0 else ct))

        # Winner callout
        win_callout = ""
        if s.a_wins > s.b_wins:
            win_callout = f"{'You' if is_easy else 'Run A'} wins {(s.a_wins - s.b_wins)} more rounds!"
            win_color = ca
        elif s.b_wins > s.a_wins:
            win_callout = f"{'Minimum Time' if is_easy else 'Run B'} wins {(s.b_wins - s.a_wins)} more rounds!"
            win_color = cb
        else:
            win_callout = "It's a tie!"
            win_color = ct
        tk.Label(self._summary_inner, text=win_callout, font=("Segoe UI", 18, "bold"),
                 bg=bg, fg=win_color, anchor="w").pack(fill="x", padx=24, pady=(16, 8))

        # Cumulative delta chart
        if rows:
            tk.Label(self._summary_inner, text="", bg=bg).pack(pady=4)
            tk.Label(self._summary_inner, text="Cumulative Frame Delta",
                     font=("Segoe UI", 14, "bold"), bg=bg, fg=fg, anchor="w"
                     ).pack(fill="x", padx=24, pady=(8, 4))
            tk.Label(self._summary_inner,
                     text="Running total of frame difference (A over B) across rounds",
                     font=("Segoe UI", 9), bg=bg, fg=sub, anchor="w"
                     ).pack(fill="x", padx=24, pady=(0, 8))

            cum_frame = tk.Frame(self._summary_inner, bg=bg)
            cum_frame.pack(fill="x", padx=24, pady=(0, 12))

            max_cum = max(abs(r.cum_a - r.cum_b) for r in rows) or 1
            for r in rows:
                cum_df = r.cum_a - r.cum_b
                bar_h = 16
                w_pos = int(cum_df / max_cum * 200) if cum_df > 0 else 0
                w_neg = int(abs(cum_df) / max_cum * 200) if cum_df < 0 else 0

                row_f = tk.Frame(cum_frame, height=bar_h, bg=bg)
                row_f.pack(fill="x", pady=1)
                row_f.pack_propagate(False)

                tk.Label(row_f, text=f"R{r.round:>2}", font=("Segoe UI", 8),
                         bg=bg, fg=fg, width=4).pack(side="left")

                bar_f = tk.Frame(row_f, bg=bg)
                bar_f.pack(side="left", fill="x", expand=True, padx=(4, 4))

                if cum_df > 0:
                    tk.Frame(bar_f, width=w_pos, bg=ca).pack(side="left")
                elif cum_df < 0:
                    tk.Frame(bar_f, width=200 - w_neg, bg=bg).pack(side="left")
                    tk.Frame(bar_f, width=w_neg, bg=cb).pack(side="left")
                else:
                    tk.Frame(bar_f, width=2, bg=ct).pack(side="left")

                tk.Label(row_f, text=f"{cum_df:+}", font=("Segoe UI", 8), bg=bg,
                         fg=ca if cum_df > 0 else (cb if cum_df < 0 else ct), width=7
                         ).pack(side="left")

            # Spacer between charts
            tk.Label(self._summary_inner, text="", bg=bg).pack(pady=8)

        # Per-round bar chart
        tk.Label(self._summary_inner, text="Per-Round Comparison",
                 font=("Segoe UI", 14, "bold"), bg=bg, fg=fg, anchor="w"
                 ).pack(fill="x", padx=24, pady=(8, 8))

        max_df = max(abs(r.df) for r in rows) or 1

        for r in rows:
            round_frame = tk.Frame(self._summary_inner, bg=bg)
            round_frame.pack(fill="x", padx=24, pady=3)

            bar_h = 22
            wA = int(abs(r.df) / max_df * 250) if r.df < 0 else 0
            wB = int(abs(r.df) / max_df * 250) if r.df > 0 else 0
            wT = 2 if r.df == 0 else 0

            tk.Label(round_frame, text=f"R{r.round:>2}",
                     font=("Segoe UI", 9, "bold"), bg=bg, fg=fg, width=4
                     ).pack(side="left")

            bar_frame = tk.Frame(round_frame, height=bar_h, bg=bg)
            bar_frame.pack(side="left", fill="x", expand=True, padx=(4, 4))
            bar_frame.pack_propagate(False)

            if wA > 0:
                tk.Frame(bar_frame, width=wA, bg=cb).pack(side="left")
            if wT > 0:
                tk.Frame(bar_frame, width=wT, bg=ct).pack(side="left")
            if wB > 0:
                tk.Frame(bar_frame, width=wB, bg=ca).pack(side="left")

            tk.Label(round_frame, text=f"{r.df:+}",
                     font=("Segoe UI", 9), bg=bg,
                     fg=ca if r.df > 0 else (cb if r.df < 0 else ct), width=7
                     ).pack(side="left")

    # =====================
    # THEME / SHORTCUTS
    # =====================
    def _bind_shortcuts(self):
        self.bind("<Escape>", lambda e: self._show_page("menu"))
        self.bind("<Control-q>", lambda e: self._on_close())
        self.bind("<Control-Q>", lambda e: self._on_close())
        self.bind("<Control-v>", lambda e: self._paste_splits())
        self.bind("<Control-V>", lambda e: self._paste_splits())

    def _apply_theme(self):
        t = self._theme()
        self.configure(bg=t["bg"])

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=t["bg"], foreground=t["fg"],
                        fieldbackground=t["tree_bg"])
        style.configure("TNotebook", background=t["notebook_bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=t["notebook_tab_bg"],
                        foreground=t["notebook_tab_fg"], padding=[20, 8], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", t["notebook_bg"])],
                  foreground=[("selected", t["fg"])])
        style.configure("Vertical.TScrollbar", gripcount=0,
                        background=t["notebook_tab_bg"], troughcolor=t["trough"],
                        bordercolor=t["trough"], arrowcolor=t["sub_fg"])
        style.configure("TCombobox", fieldbackground=t["button_bg"],
                        foreground=t["fg"], arrowcolor=t["sub_fg"],
                        selectbackground=t["selectbg"])
        style.map("TCombobox", fieldbackground=[("readonly", t["button_bg"])],
                  foreground=[("readonly", t["fg"])])
        style.configure("TCombobox.Listbox", background=t["bg"],
                        foreground=t["fg"], selectbackground=t["selectbg"])

        if hasattr(self, "_cat_combo"):
            self._cat_combo.set(self._selected_cat)

        # Theme table
        if hasattr(self, "_table"):
            self._table.set_theme(t)
            if self.rows:
                self._table.set_data([r.__dict__ for r in self.rows])

        # Walk all widgets
        tag_map = {"a": t["win_a"], "b": t["win_b"], "t": t["win_t"],
                   "fg": t["label_fg"]}
        for w in self._walk_children(self):
            if hasattr(w, "_fg_tag") and w.winfo_class() == "Label":
                w.configure(fg=tag_map.get(w._fg_tag, t["label_fg"]))
            cls = w.winfo_class()

            p = w.master
            in_summary = False
            while p:
                if p is getattr(self, "_summary_inner", None):
                    in_summary = True
                    break
                p = p.master if p is not self else None

            if not in_summary:
                if cls in ("Frame", "Labelframe"):
                    try:
                        w.configure(bg=t["bg"])
                    except:
                        pass
                elif cls == "Label":
                    try:
                        w.configure(bg=t["bg"], fg=t["label_fg"])
                    except:
                        pass
                elif cls == "Entry":
                    try:
                        w.configure(bg=t["text_bg"], fg=t["text_fg"],
                                    relief="flat", highlightthickness=0)
                    except:
                        pass
                elif cls == "Button":
                    try:
                        w.configure(bg=t["button_bg"], fg=t["button_fg"],
                                    activebackground=t["selectbg"],
                                    activeforeground=t["button_fg"],
                                    highlightthickness=0, bd=0, font=("Segoe UI", 10),
                                    highlightbackground=t["button_bg"],
                                    highlightcolor=t["button_bg"])
                    except:
                        pass
                elif cls in ("Text", "ScrolledText"):
                    try:
                        w.configure(bg=t["text_bg"], fg=t["text_fg"])
                    except:
                        pass

            # StatCards
            if hasattr(w, "lbl"):
                try:
                    w.theme(t)
                except:
                    pass

            # MenuCards
            if hasattr(w, "_cmd"):
                try:
                    w.theme(t)
                except:
                    pass

        # Topbar / statusbar specific overrides
        for attr, props in [
            ("_topbar", [("bg", "nav_bg")]),
            ("_topbar_inner", [("bg", "nav_bg")]),
            ("_topbar_sep", [("bg", "border")]),
            ("_topbar_title", [("bg", "nav_bg"), ("fg", "fg")]),
            ("_topbar_subtitle", [("bg", "nav_bg"), ("fg", "sub_fg")]),
            ("_topbar_right", [("bg", "nav_bg")]),
            ("_btn_settings", [("bg", "nav_bg"), ("fg", "fg")]),
            ("_statusbar", [("bg", "nav_bg")]),
            ("_status_lbl", [("bg", "nav_bg"), ("fg", "sub_fg")]),
            ("_status_sep", [("bg", "border")]),
            ("_menu_bottom_sep", [("bg", "border")]),
        ]:
            w = getattr(self, attr, None)
            if w:
                kw = {k: t[v] for k, v in props}
                try:
                    w.configure(**kw)
                except:
                    pass

        # Rebuild recent runs with new theme
        if hasattr(self, "_recent_frame"):
            self._rebuild_recent()

        # Theme summary (re-applied after walk loop to avoid override)
        if hasattr(self, "_btn_settings"):
            try:
                self._btn_settings.configure(font=("Segoe UI", 16), relief="flat")
            except:
                pass
        if hasattr(self, "_summary_inner"):
            self._summary_inner.configure(bg=t["text_bg"])
        if hasattr(self, "_summary_canvas"):
            self._summary_canvas.configure(bg=t["text_bg"])
        if self.rows:
            self._populate_summary()

    def _walk_children(self, parent):
        for w in parent.winfo_children():
            yield w
            yield from self._walk_children(w)

    def _copy_table(self):
        if not self.rows:
            return
        lines = []
        hdr = "Round\tA Fr\tA Time\tA Cum\tB Fr\tB Time\tB Cum\tD Frames\tD Time\tWinner\tMomentum"
        lines.append(hdr)
        for r in self.rows:
            lines.append(
                f"{r.round}\t{r.a_frames}\t{fmt(r.a_time)}\t{fmt(r.cum_a)}\t"
                f"{r.b_frames}\t{fmt(r.b_time)}\t{fmt(r.cum_b)}\t"
                f"{r.df:+}\t{r.dt:+.3f}\t{r.win}\t{r.mom:+}"
            )
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Copied to clipboard")

    def export(self):
        if not self.rows:
            messagebox.showinfo("Export", "Nothing to export yet.")
            return
        text = build_export_text(self.rows, self.summary, self.nameA, self.nameB)
        try:
            path = export_report(text)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")
            self._set_status("Export failed")
            return
        self._set_status(f"Exported to {path}")
        messagebox.showinfo("Export Complete", f"Saved to:\n{path}")

    def _on_close(self):
        self._save_prefs()
        self.destroy()

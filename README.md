# BTD6 Split Analyzer

A desktop GUI tool for comparing speedrun splits from **Bloons TD 6** side-by-side. Load two runs and see who wins each round, track deltas, and export results.

## Features

- **Compare Two Runs** — Load any two split files and compare round-by-round
- **Min-Time Comparison** — See how your run stacks up against optimal splits
- **Paste Splits** — Copy/paste split data directly instead of picking files
- **OCR Support** — Read timestamps from screenshots via Tesseract
- **Category Presets** — Easy, Medium, Hard, Impoppable, CHIMPS with pre-defined min-time datasets
- **Per-Cell Colored Table** — Custom DataTable with win/loss/delta highlighting
- **Bar Charts** — Visual delta bars in D Frames and D Time columns
- **Cumulative Delta Chart** — Running bar chart of A−B over all rounds
- **8 Themes** — Dark and light color schemes
- **Filter & Search** — Filter by win type, round range, or search a specific round
- **Font Zoom** — Adjustable table font size (8–24pt)
- **Drag & Drop** — Drop split files onto the window
- **Session Restore** — Auto-saves last comparison, prompts to restore on startup
- **Export to Text** — Save comparison results as a timestamped report file
- **Keyboard Shortcuts** — `Ctrl+V` paste, `Ctrl+Q` quit, `Esc` back to menu

## Requirements

- **Python 3.13+**
- `tkinter` (built into Python)
- `pytesseract` + `Pillow` (optional, for OCR)
- **Tesseract-OCR** engine (optional, for OCR)

## Quick Start

```bash
cd v3
python main.pyw
```

Or double-click `main.pyw`.

## Build Executable

```bash
pip install pyinstaller
cd v3
python -m PyInstaller --onefile --windowed --name "BTD6 Split Analyzer" main.pyw
```

The exe will be in `v3/dist/`.

## File Structure

```
v3/
├── main.pyw       # Entry point
├── app.py         # GUI application (~1600 lines)
├── core.py        # Business logic: parsing, analysis, OCR, export (~660 lines)
├── themes.py      # 8 color themes
├── widgets.py     # Custom DataTable, StatCard, MenuCard
└── dist/
    └── BTD6 Split Analyzer.exe  # Pre-built standalone executable
```

## Export Location

When running as a script, exports go to `EXPORTED TEXT FILES HERE/` next to the project root. When running as a frozen exe, exports go to the same directory as the executable. You can change this in **Settings → Export Folder**.

## License

MIT

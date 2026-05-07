import sys as _sys

_DARK = dict(
    BG         = "#0d1117",
    BG_CARD    = "#161b22",
    BG_SIDE    = "#010409",
    BG_SUCCESS = "#162416",
    ACCENT     = "#58a6ff",
    GREEN      = "#3fb950",
    RED        = "#f85149",
    YELLOW     = "#d29922",
    TEXT       = "#e6edf3",
    TEXT_DIM   = "#8b949e",
    BORDER     = "#30363d",
)

_LIGHT = dict(
    BG         = "#f6f8fa",
    BG_CARD    = "#ffffff",
    BG_SIDE    = "#eaeef2",
    BG_SUCCESS = "#dafbe1",
    ACCENT     = "#0969da",
    GREEN      = "#1a7f37",
    RED        = "#cf222e",
    YELLOW     = "#9a6700",
    TEXT       = "#1f2328",
    TEXT_DIM   = "#57606a",
    BORDER     = "#d0d7de",
)

# Current values — initialised to dark
BG         = _DARK["BG"]
BG_CARD    = _DARK["BG_CARD"]
BG_SIDE    = _DARK["BG_SIDE"]
BG_SUCCESS = _DARK["BG_SUCCESS"]
ACCENT     = _DARK["ACCENT"]
GREEN      = _DARK["GREEN"]
RED        = _DARK["RED"]
YELLOW     = _DARK["YELLOW"]
TEXT       = _DARK["TEXT"]
TEXT_DIM   = _DARK["TEXT_DIM"]
BORDER     = _DARK["BORDER"]

_is_dark = True


def _resolve_palette(theme: str) -> dict:
    if theme == "light":
        return _LIGHT
    if theme == "system":
        import subprocess
        try:
            r = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2,
            )
            return _DARK if r.stdout.strip() == "Dark" else _LIGHT
        except Exception:
            return _DARK
    return _DARK


def apply_theme(theme: str) -> str:
    global _is_dark
    mod = _sys.modules[__name__]
    p = _resolve_palette(theme)
    _is_dark = (p is _DARK)
    for k, v in p.items():
        setattr(mod, k, v)
    return _build_stylesheet()


def _build_stylesheet() -> str:
    m   = _sys.modules[__name__]
    BG       = m.BG
    BG_CARD  = m.BG_CARD
    BG_SIDE  = m.BG_SIDE
    ACCENT   = m.ACCENT
    GREEN    = m.GREEN
    RED      = m.RED
    TEXT     = m.TEXT
    TEXT_DIM = m.TEXT_DIM
    BORDER   = m.BORDER
    dark     = m._is_dark

    _sel  = "#1f2d3d"  if dark else "#ddf4ff"
    _hvr  = "#21262d"  if dark else "#f3f4f6"
    _hvr2 = "#161b22"  if dark else "#eaeef2"
    _btn  = "#21262d"  if dark else "#f6f8fa"
    _btn2 = "#30363d"  if dark else "#eaeef2"
    _dng  = "#2d1515"  if dark else "#ffebe9"

    return f"""
* {{
    font-family: -apple-system, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
}}
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
}}
QLabel {{
    background-color: transparent;
}}

QFrame#sidebar {{
    background-color: {BG_SIDE};
    border-right: 1px solid {BORDER};
}}
QToolButton#nav_btn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 4px 6px 4px;
    color: {TEXT_DIM};
    font-size: 14px;
}}
QToolButton#nav_btn:checked {{
    background-color: {_hvr};
    color: {ACCENT};
}}
QToolButton#nav_btn:hover:!checked {{
    background-color: {_hvr2};
    color: {TEXT};
}}

QFrame#panel {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#panel QWidget {{
    background-color: transparent;
}}

QLineEdit, QSpinBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT};
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus {{
    border-color: {ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 20px;
    background-color: {_btn};
    border: none;
}}

QPushButton {{
    background-color: {_btn};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT};
    font-size: 12px;
}}
QPushButton:hover  {{ background-color: {_btn2}; }}
QPushButton:pressed {{ background-color: {BG_CARD}; }}

QPushButton#primary_btn {{
    background-color: {ACCENT};
    color: #000000;
    border: none;
    font-weight: bold;
}}
QPushButton#primary_btn:hover {{ background-color: {ACCENT}cc; }}

QPushButton#danger_btn {{
    background-color: transparent;
    color: {RED};
    border: 1px solid {RED};
}}
QPushButton#danger_btn:hover {{ background-color: {_dng}; }}

QTableWidget {{
    background-color: {BG};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    font-size: 11px;
    selection-background-color: {_sel};
}}
QHeaderView::section {{
    background-color: {BG_SIDE};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 4px 6px;
    font-size: 10px;
    color: {TEXT_DIM};
}}
QHeaderView::section:first {{
    border-left: 1px solid {BORDER};
}}

QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background-color: {_sel};
    color: {ACCENT};
}}
QListWidget::item:hover:!selected {{
    background-color: {_hvr};
}}
QListWidget QLineEdit {{
    background-color: {_btn};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 2px 8px;
    color: {TEXT};
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: #000000;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 0px;
    margin: 2px 2px 2px 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    border-radius: 0px;
    margin: 2px 2px 2px 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

QMessageBox {{ background-color: {BG_CARD}; }}
QMessageBox QLabel {{ color: {TEXT}; }}
"""

STYLESHEET = _build_stylesheet()

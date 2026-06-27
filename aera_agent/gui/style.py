"""Global QSS stylesheet for the main AERA window."""

from ..theme import BG, PANEL, INK, MUTED, ACCENT, ACCENT_DK, RED


STYLE = f"""
* {{ font-family: "Segoe UI", "SF Pro", "Inter", sans-serif; color: {INK}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}

QFrame#card {{
    background: {PANEL};
    border: 1.5px solid {INK};
    border-radius: 18px;
}}

QFrame#softCard {{
    background: {PANEL};
    border: 1px solid #dcdcdc;
    border-radius: 14px;
}}

QPushButton#navBtn {{
    background: transparent;
    border: 1.5px solid {INK};
    border-radius: 14px;
    padding: 6px 14px 6px 38px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#navBtn:hover  {{ background: #f3f6fb; }}
QPushButton#navBtn:checked {{ background: {ACCENT}; color: white; border-color: {ACCENT_DK}; }}

QPushButton#logo {{
    background: transparent;
    border: 2px solid {INK};
    border-radius: 18px;
    padding: 6px 18px;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 1px;
}}

QPushButton#winBtn {{
    background: transparent;
    border: none;
    color: {INK};
    font-size: 18px;
    padding: 4px 10px;
}}
QPushButton#winBtn:hover {{ background: #eee; border-radius: 6px; }}
QPushButton#closeBtn:hover {{ background: {RED}; color: white; border-radius: 6px; }}

QLabel#panelTitle {{ color: {MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 0.6px; }}
QLabel#bigTitle  {{ font-size: 22px; font-weight: 800; }}

QPushButton#tapBtn {{
    background: white;
    border: 2px solid {ACCENT};
    border-radius: 22px;
    padding: 10px 28px;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: {ACCENT_DK};
}}
QPushButton#tapBtn:hover {{ background: #eaf6ff; }}
QPushButton#tapBtn:pressed {{ background: {ACCENT}; color: white; }}

QTextEdit#transcript {{
    background: transparent;
    border: none;
    color: white;
    font-size: 13px;
}}

QTreeWidget, QTreeView {{
    background: transparent;
    border: none;
    font-size: 13px;
}}
QTreeWidget::item:selected, QTreeView::item:selected {{
    background: #eaf3ff;
    color: {INK};
}}
"""

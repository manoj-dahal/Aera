"""
Centralized theme: colors, fonts, and reusable QSS button styles.

Before this existed every page defined its own button styles inline,
causing ~250 lines of duplicated stylesheet strings. Now every widget
imports from here, so:
  • one place to change the theme,
  • smaller files (~30 % reduction in pages.py / voice_studio.py),
  • a future dark-mode is a single dict swap.
"""

from __future__ import annotations

# ---------------------------------------------------------------- #
#  Palette
# ---------------------------------------------------------------- #
BG          = "#fdfdfd"
PANEL       = "#ffffff"
PANEL_SOFT  = "#fafafa"
INK         = "#111111"
MUTED       = "#666666"
BORDER      = "#dcdcdc"
BORDER_SOFT = "#f0f0f0"
HOVER_TINT  = "#eaf3ff"
HOVER_SOFT  = "#f3f6fb"

ACCENT      = "#1da1ff"
ACCENT_DK   = "#0078d4"
ORANGE      = "#ff7a1a"
GREEN       = "#27c074"
RED         = "#e8413c"

# semantic aliases
SUCCESS     = GREEN
WARNING     = ORANGE
DANGER      = RED
INFO        = ACCENT


# ---------------------------------------------------------------- #
#  Button stylesheets (use sparingly — most widgets use the global
#  STYLE in gui.py, but pages need a few one-offs).
# ---------------------------------------------------------------- #
def primary_btn(color: str = ACCENT, dark: str = ACCENT_DK) -> str:
    """Filled blue button — main call-to-action."""
    return (
        f"QPushButton {{ background:{color}; color:white; border:none;"
        f" border-radius:10px; padding:8px 16px; font-weight:700; }}"
        f"QPushButton:hover {{ background:{dark}; }}"
        f"QPushButton:disabled {{ background:#cccccc; color:#777; }}"
    )


def danger_btn() -> str:
    """Filled red button — destructive / record."""
    return (
        f"QPushButton {{ background:{RED}; color:white; border:none;"
        f" border-radius:10px; padding:10px 18px; font-weight:800; }}"
        f"QPushButton:hover {{ background:#c92a26; }}"
    )


def ghost_btn(color: str = ACCENT, dark: str = ACCENT_DK) -> str:
    """Outlined button — secondary action."""
    return (
        f"QPushButton {{ background:white; color:{dark};"
        f" border:1.5px solid {color}; border-radius:10px;"
        f" padding:8px 14px; font-weight:600; }}"
        f"QPushButton:hover {{ background:{HOVER_TINT}; }}"
        f"QPushButton:disabled {{ color:#888; border-color:#ccc; }}"
    )


def muted_btn() -> str:
    """Subtle gray button — tertiary action."""
    return (
        f"QPushButton {{ background:transparent; color:{MUTED};"
        f" border:1px solid {BORDER}; border-radius:8px; padding:6px 10px; }}"
        f"QPushButton:hover {{ background:{HOVER_SOFT}; }}"
    )


# ---------------------------------------------------------------- #
#  Card stylesheet (reused by pages.Card and voice_studio.Card)
# ---------------------------------------------------------------- #
CARD_QSS = (
    f"QFrame {{ background:{PANEL}; border:1px solid {BORDER};"
    f" border-radius:14px; }}"
    f"QLabel#cardTitle {{ color:{MUTED}; font-size:11px; font-weight:700;"
    f" letter-spacing:0.8px; border:none; }}"
)

# ---------------------------------------------------------------- #
#  Title / muted labels
# ---------------------------------------------------------------- #
TITLE_QSS  = "font-size:22px; font-weight:800;"
SUBTLE_QSS = f"color:{MUTED}; font-size:12px;"
HINT_QSS   = f"color:{MUTED}; font-size:11px;"

# ---------------------------------------------------------------- #
#  Generic list style
# ---------------------------------------------------------------- #
LIST_QSS = (
    "QListWidget { background:transparent; border:none; font-size:13px; }"
    f"QListWidget::item {{ padding:8px; border-bottom:1px solid {BORDER_SOFT}; }}"
    f"QListWidget::item:selected {{ background:{HOVER_TINT}; color:{INK}; }}"
)

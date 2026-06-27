"""Page widgets for the AERA Agent main window."""

from .common    import Card, StatPill, Sparkline
from .dashboard import DashboardPage
from .macros    import MacrosPage
from .apps      import AppsPage
from .gallery   import GalleryPage
from .phone     import PhonePage
from .studio    import VoiceStudioPage
from .settings  import SettingsPage

__all__ = [
    "Card", "StatPill", "Sparkline",
    "DashboardPage", "MacrosPage", "AppsPage", "GalleryPage",
    "PhonePage", "VoiceStudioPage", "SettingsPage",
]

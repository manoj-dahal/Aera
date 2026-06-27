"""
Main AERA Agent window. Wires together:
  • TopBar (navigation)
  • Left column: HoloIndicator, PCInfoCard, WorkspacePanel, StatusFrame
  • Center: stacked pages (Home / Dashboard / Macros / Apps / Gallery / Phone / Studio / Settings)
  • Right column: TranscriptPhone
  • AssistantWorker (background voice loop)
"""

import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QStackedWidget, QLineEdit, QTextEdit,
)

from .style import STYLE
from .widgets import (
    HomePage, HoloIndicator, PCInfoCard, WorkspacePanel,
    StatusFrame, TranscriptPhone, TopBar, placeholder,
)
from .worker import AssistantWorker
from .wizard import run_wizard_if_needed
from .pages import (
    DashboardPage as DashStats,
    MacrosPage, AppsPage, GalleryPage, PhonePage,
    VoiceStudioPage, SettingsPage,
)

from ..paths import ASSETS_DIR
ICON_PATH = ASSETS_DIR / "aera_icon.png"


class AeraWindow(QMainWindow):
    _NAV_INDEX = {
        "Home": 0, "Dashboard": 1, "Macros": 2, "Apps": 3,
        "Gallery": 4, "Phone": 5, "Studio": 6, "Settings": 7,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AERA Agent")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1480, 820)
        self.setStyleSheet(STYLE)

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(8, 8, 8, 8); outer.setSpacing(6)

        bg = QFrame(); bg.setObjectName("card")
        outer.addWidget(bg, 1)
        bg_lay = QVBoxLayout(bg); bg_lay.setContentsMargins(8, 8, 8, 8); bg_lay.setSpacing(8)

        # top
        self.top = TopBar()
        self.top.nav.connect(self._nav)
        bg_lay.addWidget(self.top)

        body = QHBoxLayout(); body.setSpacing(14)
        bg_lay.addLayout(body, 1)

        # left column
        left = QVBoxLayout(); left.setSpacing(10)
        left.addWidget(HoloIndicator())
        left.addWidget(PCInfoCard())
        self.workspace = WorkspacePanel()
        left.addWidget(self.workspace, 1)
        self.status = StatusFrame()
        left.addWidget(self.status, 0, Qt.AlignLeft)
        left_wrap = QWidget(); left_wrap.setLayout(left); left_wrap.setFixedWidth(190)
        body.addWidget(left_wrap)

        # center — stacked pages
        self.pages = QStackedWidget()
        self.home = HomePage(); self.home.tap.connect(self._on_tap)
        self.pages.addWidget(self.home)                       # 0 Home

        self.dash_stats = DashStats()
        self.pages.addWidget(self.dash_stats)                 # 1 Dashboard

        self.macros = MacrosPage()
        self.macros.fire.connect(self._on_phrase)
        self.pages.addWidget(self.macros)                     # 2 Macros

        self.apps_page = AppsPage()
        self.apps_page.status.connect(lambda s: self.status.set("● APP", s))
        self.pages.addWidget(self.apps_page)                  # 3 Apps

        self.gallery = GalleryPage()
        self.pages.addWidget(self.gallery)                    # 4 Gallery

        self.phone_page = PhonePage()
        self.phone_page.fire.connect(self._on_phrase)
        self.pages.addWidget(self.phone_page)                 # 5 Phone

        # Studio + Settings need worker.cfg — built after init_backend
        self.pages.addWidget(placeholder("Voice Studio", "Loading…"))   # 6 Studio
        self.pages.addWidget(placeholder("Settings", "Loading…"))       # 7 Settings
        body.addWidget(self.pages, 1)

        # right
        self.phone = TranscriptPhone()
        body.addWidget(self.phone)

        # worker
        self.worker = AssistantWorker()
        self.worker.user_said.connect(self._on_user_said)
        self.worker.assistant_said.connect(self._on_aera_said)
        self.worker.state_changed.connect(self.home.orb.set_state)
        self.worker.status.connect(self.status.set)
        self.worker.ready.connect(self._build_late_pages)
        QTimer.singleShot(200, self.worker.init_backend)

        # hotkeys
        QShortcut(QKeySequence("Space"),   self, activated=self._hotkey_space)
        QShortcut(QKeySequence("Escape"),  self, activated=self._hotkey_esc)
        QShortcut(QKeySequence("Ctrl+1"),  self, activated=lambda: self._nav("Dashboard"))
        QShortcut(QKeySequence("Ctrl+2"),  self, activated=lambda: self._nav("Macros"))
        QShortcut(QKeySequence("Ctrl+3"),  self, activated=lambda: self._nav("Apps"))
        QShortcut(QKeySequence("Ctrl+,"),  self, activated=lambda: self._nav("Settings"))

        self.phone.append("aera", "Tap mic or press <b>Space</b> to talk. <b>Esc</b> interrupts.")

    # ---- worker bridges ---- #
    def _on_user_said(self, t: str):
        self.phone.append("you", t)
        self.dash_stats.log_event(t, "user")

    def _on_aera_said(self, t: str):
        self.phone.append("aera", t)
        self.dash_stats.log_event(t[:120] + ("…" if len(t) > 120 else ""), "aera")

    def _on_phrase(self, phrase: str):
        self.worker.trigger_text(phrase)

    def _build_late_pages(self):
        """Replace Studio + Settings placeholders once worker.cfg is loaded."""
        try:
            studio = VoiceStudioPage(self.worker.cfg)
            studio.voice_set.connect(lambda *_: self.worker.reload_config())
            old = self.pages.widget(6); self.pages.removeWidget(old); old.deleteLater()
            self.pages.insertWidget(6, studio)

            settings = SettingsPage(self.worker.cfg)
            settings.config_changed.connect(self.worker.reload_config)
            old = self.pages.widget(7); self.pages.removeWidget(old); old.deleteLater()
            self.pages.insertWidget(7, settings)
        except Exception:
            traceback.print_exc()

    # ---- hotkeys ---- #
    def _hotkey_space(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTextEdit)): return
        self._on_tap()

    def _hotkey_esc(self):
        self.worker.stop_speaking()

    def _nav(self, name: str):
        for n, b in self.top._buttons.items():
            b.setChecked(n == name)
        self.pages.setCurrentIndex(self._NAV_INDEX.get(name, 0))

    def _on_tap(self):
        self.worker.trigger_listen()

    def closeEvent(self, e):
        self.worker.shutdown()
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AERA Agent")
    app.setOrganizationName("AERA")
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    # First-run setup wizard — auto-shown if no config or placeholder API key
    run_wizard_if_needed()

    win = AeraWindow(); win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

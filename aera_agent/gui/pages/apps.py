"""Auto-split from monolithic pages.py."""

import json
import platform
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient, QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QFrame, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QListWidget, QListWidgetItem, QFormLayout, QFileDialog,
    QMessageBox, QStackedWidget, QSlider, QCheckBox,
    QDialog, QDialogButtonBox, QInputDialog,
)

try:
    import psutil
except ImportError:
    psutil = None

from ...theme import (
    ACCENT, ACCENT_DK, ORANGE, GREEN, RED, PANEL, INK, MUTED, BORDER,
    BORDER_SOFT, HOVER_TINT,
    primary_btn, ghost_btn, muted_btn,
    CARD_QSS, TITLE_QSS, SUBTLE_QSS, HINT_QSS, LIST_QSS,
)
from ...paths import (
    MACROS_FILE, APPS_FILE, CONTACTS_FILE, GALLERY_DIR, WORKSPACE_DIR,
)
from .common import Card, StatPill, Sparkline



def _default_apps():
    sysname = platform.system()
    return [
        {"name": "Browser",     "emoji": "🌐", "cmd": ""},
        {"name": "Notepad",     "emoji": "📝", "cmd": "notepad" if sysname == "Windows" else "gedit"},
        {"name": "Calculator",  "emoji": "🧮", "cmd": "calc" if sysname == "Windows" else "gnome-calculator"},
        {"name": "Terminal",    "emoji": "💻", "cmd": "cmd" if sysname == "Windows" else "x-terminal-emulator"},
        {"name": "Files",       "emoji": "📁", "cmd": "explorer" if sysname == "Windows" else "nautilus"},
        {"name": "VS Code",     "emoji": "🟦", "cmd": "code"},
        {"name": "Spotify",     "emoji": "🎵", "cmd": "spotify"},
        {"name": "ChatGPT",     "emoji": "💬", "cmd": "", "url": "https://chat.openai.com"},
        {"name": "YouTube",     "emoji": "▶️", "cmd": "", "url": "https://youtube.com"},
        {"name": "GitHub",      "emoji": "🐙", "cmd": "", "url": "https://github.com"},
    ]


class AppsPage(QWidget):
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("Apps"); t.setStyleSheet(TITLE_QSS)
        hdr.addWidget(t); hdr.addStretch(1)
        add = QPushButton("＋ Add app"); add.setStyleSheet(primary_btn())
        add.clicked.connect(self._add); hdr.addWidget(add)
        lay.addLayout(hdr)

        sub = QLabel("Click to launch. Right-click to remove.")
        sub.setStyleSheet(SUBTLE_QSS)
        lay.addWidget(sub)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border:none;")
        body = QWidget(); self.grid = QGridLayout(body); self.grid.setSpacing(10)
        scroll.setWidget(body); lay.addWidget(scroll, 1)

        self.apps = self._load()
        self._render()

    def _load(self):
        if APPS_FILE.exists():
            try: return json.loads(APPS_FILE.read_text())
            except Exception: pass
        return _default_apps()

    def _save(self): APPS_FILE.write_text(json.dumps(self.apps, indent=2))

    def _render(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        cols = 6
        for i, a in enumerate(self.apps):
            r, c = divmod(i, cols)
            self.grid.addWidget(self._tile(a, i), r, c)

    def _tile(self, app: dict, idx: int):
        w = QFrame(); w.setFixedSize(120, 110)
        w.setStyleSheet(f"""
            QFrame {{ background: {PANEL}; border: 1.5px solid {BORDER}; border-radius: 14px; }}
            QFrame:hover {{ border-color: {ACCENT}; background: #f7fbff; }}
        """)
        v = QVBoxLayout(w); v.setContentsMargins(8, 10, 8, 10); v.setAlignment(Qt.AlignCenter)
        e = QLabel(app.get("emoji", "📦")); e.setAlignment(Qt.AlignCenter)
        e.setStyleSheet("font-size: 36px; border: none;")
        n = QLabel(app["name"]); n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet("font-size: 12px; font-weight: 600; border: none;")
        v.addWidget(e); v.addWidget(n)
        w.mousePressEvent = lambda ev, a=app, i=idx: self._click(ev, a, i)
        return w

    def _click(self, ev, app: dict, idx: int):
        if ev.button() == Qt.RightButton:
            self.apps.pop(idx); self._save(); self._render(); return
        # left-click: launch
        try:
            if app.get("url"):
                import webbrowser; webbrowser.open(app["url"])
                self.status.emit(f"Opened {app['url']}")
                return
            cmd = app.get("cmd", "")
            if not cmd: return
            if platform.system() == "Windows":
                subprocess.Popen(cmd, shell=True)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", cmd])
            else:
                subprocess.Popen(cmd.split())
            self.status.emit(f"Launched {app['name']}")
        except Exception as e:
            self.status.emit(f"Failed: {e}")

    def _add(self):
        dlg = AppEditDialog({"name": "New app", "emoji": "📦", "cmd": "", "url": ""}, self)
        if dlg.exec():
            self.apps.append(dlg.value()); self._save(); self._render()


class AppEditDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Application")
        f = QFormLayout(self)
        self.name = QLineEdit(app["name"])
        self.emoji = QLineEdit(app.get("emoji", "📦"))
        self.cmd = QLineEdit(app.get("cmd", ""))
        self.url = QLineEdit(app.get("url", ""))
        f.addRow("Name:", self.name); f.addRow("Emoji:", self.emoji)
        f.addRow("Command:", self.cmd); f.addRow("URL:", self.url)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def value(self):
        return {"name": self.name.text(), "emoji": self.emoji.text(),
                "cmd": self.cmd.text(), "url": self.url.text()}


# ============================================================ #
#  4. GALLERY  — thumbnails of images in workspace/gallery
# ============================================================ #



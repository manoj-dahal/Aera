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



DEFAULT_MACROS = [
    {"name": "Morning Brief",   "emoji": "☀️",  "say": "Tell me today's weather, top news, and the time."},
    {"name": "Where Am I?",     "emoji": "📍",  "say": "What's my current IP location?"},
    {"name": "Quick Note",      "emoji": "📝",  "say": "Add a note: "},
    {"name": "5 Min Timer",     "emoji": "⏰",  "say": "Set a timer for 5 minutes."},
    {"name": "Translate to JP", "emoji": "🌏",  "say": "Translate the following to Japanese: "},
    {"name": "Random Password", "emoji": "🔐",  "say": "Generate a strong 20-character password."},
    {"name": "Roll Dice",       "emoji": "🎲",  "say": "Roll 2d6."},
    {"name": "Top Headlines",   "emoji": "📰",  "say": "Give me the top 5 news headlines."},
    {"name": "Wikipedia: ",     "emoji": "📚",  "say": "Look up Wikipedia for: "},
    {"name": "Clear Memory",    "emoji": "🧠",  "say": "Show me my memory stats."},
]


class MacrosPage(QWidget):
    fire = Signal(str)   # emits a phrase to send to the assistant

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("Macros"); t.setStyleSheet(TITLE_QSS)
        hdr.addWidget(t); hdr.addStretch(1)
        add_btn = QPushButton("＋ New macro")
        add_btn.setStyleSheet(primary_btn())
        add_btn.clicked.connect(self._add)
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        sub = QLabel("One-tap phrases sent to the assistant. Edit by clicking a macro.")
        sub.setStyleSheet(SUBTLE_QSS)
        lay.addWidget(sub)

        # scroll area with grid
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border:none;")
        body = QWidget(); self.grid = QGridLayout(body); self.grid.setSpacing(12)
        scroll.setWidget(body); lay.addWidget(scroll, 1)

        self.macros = self._load()
        self._render()

    def _load(self):
        if MACROS_FILE.exists():
            try: return json.loads(MACROS_FILE.read_text())
            except Exception: pass
        return list(DEFAULT_MACROS)

    def _save(self):
        MACROS_FILE.write_text(json.dumps(self.macros, indent=2))

    def _render(self):
        # clear
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        cols = 4
        for i, m in enumerate(self.macros):
            r, c = divmod(i, cols)
            tile = self._tile(m, i)
            self.grid.addWidget(tile, r, c)

    def _tile(self, m: dict, idx: int) -> QWidget:
        w = QFrame()
        w.setMinimumSize(180, 110)
        w.setStyleSheet(f"""
            QFrame {{ background: {PANEL}; border: 1.5px solid {BORDER}; border-radius: 14px; }}
            QFrame:hover {{ border-color: {ACCENT}; }}
        """)
        v = QVBoxLayout(w); v.setContentsMargins(14, 10, 14, 10)
        emoji = QLabel(m.get("emoji", "✨")); emoji.setStyleSheet("font-size: 28px; border: none;")
        v.addWidget(emoji)
        name = QLabel(m["name"]); name.setStyleSheet("font-weight: 700; font-size: 13px; border: none;")
        v.addWidget(name)
        say = QLabel(m["say"][:40] + ("…" if len(m["say"]) > 40 else ""))
        say.setStyleSheet(f"color: {MUTED}; font-size: 10px; border: none;"); say.setWordWrap(True)
        v.addWidget(say); v.addStretch(1)

        btn_row = QHBoxLayout()
        run = QPushButton("Run"); run.setStyleSheet(primary_btn())
        run.clicked.connect(lambda: self.fire.emit(m["say"]))
        edit = QPushButton("Edit"); edit.setStyleSheet(muted_btn())
        edit.clicked.connect(lambda: self._edit(idx))
        btn_row.addWidget(run); btn_row.addWidget(edit)
        v.addLayout(btn_row)
        return w

    def _add(self):
        self.macros.append({"name": "New macro", "emoji": "✨", "say": "Hello!"})
        self._save(); self._render()
        self._edit(len(self.macros) - 1)

    def _edit(self, idx: int):
        dlg = MacroEditDialog(self.macros[idx], self)
        if dlg.exec():
            self.macros[idx] = dlg.value()
            self._save(); self._render()
        elif dlg.deleted:
            del self.macros[idx]; self._save(); self._render()


class MacroEditDialog(QDialog):
    def __init__(self, macro: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Macro")
        self.deleted = False
        form = QFormLayout(self)
        self.name = QLineEdit(macro["name"])
        self.emoji = QLineEdit(macro.get("emoji", "✨"))
        self.say = QTextEdit(macro["say"]); self.say.setFixedHeight(80)
        form.addRow("Name:", self.name)
        form.addRow("Emoji:", self.emoji)
        form.addRow("Phrase:", self.say)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.Discard)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Discard).setText("Delete")
        bb.button(QDialogButtonBox.Discard).clicked.connect(self._del)
        form.addRow(bb)

    def _del(self): self.deleted = True; self.reject()
    def value(self):
        return {"name": self.name.text(), "emoji": self.emoji.text(), "say": self.say.toPlainText()}


# ============================================================ #
#  3. APPS  — quick-launch grid
# ============================================================ #

def _default_apps():
    sysname = platform.system()
    base = [
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
    return base



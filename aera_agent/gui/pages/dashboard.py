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



class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(14)

        title = QLabel("Dashboard")
        title.setStyleSheet(TITLE_QSS)
        lay.addWidget(title)

        # Top row: 4 stat pills
        row = QHBoxLayout(); row.setSpacing(12)
        self.s_cpu  = StatPill("CPU",    ACCENT)
        self.s_ram  = StatPill("MEMORY", ORANGE)
        self.s_net  = StatPill("NETWORK", GREEN)
        self.s_calls= StatPill("TOOL CALLS", RED)
        for s in (self.s_cpu, self.s_ram, self.s_net, self.s_calls):
            row.addWidget(s)
        lay.addLayout(row)

        # Middle: charts
        mid = QHBoxLayout(); mid.setSpacing(12)
        c1 = Card("CPU Usage")
        self.cpu_chart = Sparkline(ACCENT); c1.lay.addWidget(self.cpu_chart, 1)
        c2 = Card("Memory Usage")
        self.ram_chart = Sparkline(ORANGE); c2.lay.addWidget(self.ram_chart, 1)
        mid.addWidget(c1, 1); mid.addWidget(c2, 1)
        lay.addLayout(mid, 1)

        # Bottom: recent activity
        bot = Card("Recent Activity")
        self.activity = QListWidget()
        self.activity.setStyleSheet(LIST_QSS)
        bot.lay.addWidget(self.activity, 1)
        lay.addWidget(bot, 1)

        # state
        self.tool_calls = 0
        self._last_net = 0
        t = QTimer(self); t.timeout.connect(self._refresh); t.start(1200); self._t = t
        self._refresh()

    def log_event(self, text: str, kind: str = "info"):
        icon = {"user": "🗣", "aera": "🤖", "tool": "🔧", "info": "•", "error": "⚠"}.get(kind, "•")
        item = QListWidgetItem(f"  {icon}   {time.strftime('%H:%M:%S')}   {text}")
        if kind == "tool": self.tool_calls += 1; self.s_calls.set(str(self.tool_calls))
        self.activity.insertItem(0, item)
        if self.activity.count() > 200:
            self.activity.takeItem(self.activity.count() - 1)

    def _refresh(self):
        if psutil is None:
            self.s_cpu.set("—"); return
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.s_cpu.set(f"{cpu:.0f}%"); self.cpu_chart.push(cpu)
        self.s_ram.set(f"{ram:.0f}%"); self.ram_chart.push(ram)
        try:
            n = psutil.net_io_counters().bytes_recv
            kbs = max(0, (n - self._last_net) / 1024) if self._last_net else 0
            self._last_net = n
            self.s_net.set(f"{kbs:.0f} K/s")
        except Exception:
            pass

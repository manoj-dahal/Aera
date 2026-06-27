"""
Reusable GUI widgets for the AERA Agent main window:
  - ParticleOrb         (the animated centerpiece)
  - HoloIndicator       (top-left hologram card)
  - PCInfoCard          (live psutil readout)
  - WorkspacePanel      (file tree)
  - StatusFrame         (red sci-fi corner frame)
  - TranscriptPhone     (right-side phone-shaped scrolling text)
  - TopBar              (the navigation row)
  - HomePage            (orb + TAP TO SPEAK)
  - placeholder()       (loading-page factory)
"""

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal, QSizeF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QHBoxLayout, QTextEdit, QTreeView,
    QFileSystemModel,
)

try:
    import psutil
except ImportError:
    psutil = None

from ..theme import ACCENT, ACCENT_DK, ORANGE, RED, INK, MUTED
from ..paths import WORKSPACE_DIR


# ─────────────────────────────────────────────────────────────────── #
#  Particle orb
# ─────────────────────────────────────────────────────────────────── #
@dataclass
class Particle:
    angle: float
    radius: float
    speed: float
    size: float
    phase: float


class ParticleOrb(QWidget):
    """Animated particle sphere + wave underneath. 3 visual states."""

    STATE_IDLE      = 0
    STATE_LISTENING = 1
    STATE_SPEAKING  = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.state = self.STATE_IDLE
        self.t = 0.0
        self.intensity = 0.6
        self.target_intensity = 0.6

        self.particles: list[Particle] = [
            Particle(
                angle=random.uniform(0, math.tau),
                radius=random.uniform(80, 130),
                speed=random.uniform(0.002, 0.012),
                size=random.uniform(0.8, 2.4),
                phase=random.uniform(0, math.tau),
            )
            for _ in range(600)
        ]
        self.wave_dots = [(random.uniform(0, 1), random.uniform(-1, 1),
                           random.uniform(0.6, 1.8)) for _ in range(220)]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_state(self, s: int) -> None:
        self.state = s
        self.target_intensity = {0: 0.55, 1: 1.0, 2: 0.85}[s]

    def _tick(self) -> None:
        self.t += 0.03
        self.intensity += (self.target_intensity - self.intensity) * 0.08
        scale = 1 + (self.intensity - 0.5) * 1.5
        for p in self.particles:
            p.angle += p.speed * scale
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 30

        for pt in self.particles:
            x3 = math.cos(pt.angle) * pt.radius
            z3 = math.sin(pt.angle) * pt.radius
            y3 = math.sin(pt.angle * 2 + pt.phase) * pt.radius * 0.35
            depth = (z3 + 130) / 260
            size = pt.size * (0.4 + depth)
            alpha = int(40 + depth * 180 * self.intensity)
            p.setPen(Qt.NoPen); p.setBrush(QColor(20, 20, 20, alpha))
            p.drawEllipse(QPointF(cx + x3, cy + y3), size, size)

        if self.state != self.STATE_IDLE:
            g = QRadialGradient(QPointF(cx, cy), 150)
            tint = QColor(ACCENT); tint.setAlpha(int(40 * self.intensity))
            g.setColorAt(0, tint); g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), 160, 160)

        wave_y = cy + 180
        for (rx, ry, sz) in self.wave_dots:
            x = rx * w
            phase = self.t * 1.2 + rx * 6
            amp = 40 * (0.5 + 0.5 * math.sin(phase * 0.5))
            y = wave_y + math.sin(phase) * amp * ry * 0.8
            a = int(30 + 90 * (0.5 + 0.5 * math.sin(phase)))
            p.setPen(Qt.NoPen); p.setBrush(QColor(40, 40, 40, a))
            p.drawEllipse(QPointF(x, y), sz, sz)


# ─────────────────────────────────────────────────────────────────── #
#  Left-column panels
# ─────────────────────────────────────────────────────────────────── #
class HoloIndicator(QFrame):
    """Top-left hologram-style indicator (animated cone of light)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("softCard")
        self.setFixedSize(170, 150)
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignCenter)
        self.canvas = _HoloCanvas()
        lay.addWidget(self.canvas, 1)
        label = QLabel("Hologram")
        label.setAlignment(Qt.AlignCenter); label.setObjectName("panelTitle")
        lay.addWidget(label)


class _HoloCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.t = 0.0
        self.setMinimumSize(120, 90)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(60); self._t = t

    def _tick(self):
        self.t += 0.05; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); cx = w / 2

        path = QPainterPath()
        path.moveTo(cx, 10)
        path.lineTo(cx - 35, h - 25)
        path.lineTo(cx + 35, h - 25)
        path.closeSubpath()
        g = QLinearGradient(cx, 10, cx, h - 25)
        g.setColorAt(0, QColor(ACCENT).lighter(140))
        c2 = QColor(ACCENT); c2.setAlpha(10); g.setColorAt(1, c2)
        p.fillPath(path, g)

        for i, ry in enumerate([h - 26, h - 18, h - 10]):
            p.setPen(QPen(QColor(ACCENT_DK), 1.5)); p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, ry), 38 + i * 4, 3 + i * 0.5)


class PCInfoCard(QFrame):
    """Live CPU / RAM / disk / network readout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("softCard")
        self.setFixedSize(170, 160)
        lay = QVBoxLayout(self); lay.setContentsMargins(10, 8, 10, 8)
        title = QLabel("pc system info"); title.setObjectName("panelTitle")
        lay.addWidget(title)
        self.cpu  = QLabel("CPU  —")
        self.ram  = QLabel("RAM  —")
        self.disk = QLabel("Disk —")
        self.net  = QLabel("Net  —")
        for l in (self.cpu, self.ram, self.disk, self.net):
            l.setStyleSheet("font-size:12px; color:#222;")
            lay.addWidget(l)
        lay.addStretch(1)
        t = QTimer(self); t.timeout.connect(self.refresh); t.start(1500); self._t = t
        self.refresh()

    def refresh(self):
        if psutil is None:
            self.cpu.setText("CPU  (psutil missing)"); return
        self.cpu.setText(f"CPU   {psutil.cpu_percent():>5.1f} %")
        self.ram.setText(f"RAM   {psutil.virtual_memory().percent:>5.1f} %")
        try:
            self.disk.setText(f"Disk  {psutil.disk_usage('/').percent:>5.1f} %")
        except Exception:
            self.disk.setText("Disk  —")
        try:
            self.net.setText(f"Net   {psutil.net_io_counters().bytes_recv//1024:>5} K↓")
        except Exception:
            pass


class WorkspacePanel(QFrame):
    """Bottom-left workspace file tree."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("softCard")
        self.setMinimumWidth(170)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 6, 8, 6)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("📁 WORKSPACE"))
        hdr.addStretch(1)
        plus = QPushButton("＋"); plus.setFlat(True); plus.setFixedSize(22, 22)
        hdr.addWidget(plus)
        lay.addLayout(hdr)

        (WORKSPACE_DIR / "Default").mkdir(exist_ok=True)
        self.model = QFileSystemModel()
        self.model.setRootPath(str(WORKSPACE_DIR))
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(WORKSPACE_DIR)))
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.setHeaderHidden(True)
        lay.addWidget(self.tree, 1)


class StatusFrame(QFrame):
    """Red sci-fi frame showing current assistant state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80); self.setFixedWidth(220)
        self.label = QLabel("● IDLE", self)
        self.label.setStyleSheet(f"color:{RED}; font-weight:800; "
                                 "letter-spacing:1px; font-size:13px;")
        self.detail = QLabel("ready", self)
        self.detail.setStyleSheet("color:#444; font-size:11px;")
        self.label.move(28, 18)
        self.detail.move(28, 42)

    def set(self, head: str, sub: str = ""):
        self.label.setText(head)
        self.detail.setText(sub)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor(RED), 2)); p.setBrush(Qt.NoBrush)
        path = QPainterPath()
        k = 14
        path.moveTo(k, 0); path.lineTo(w - 2, 0)
        path.lineTo(w - 2, h - k); path.lineTo(w - k - 2, h - 2)
        path.lineTo(0, h - 2); path.lineTo(0, k); path.lineTo(k, 0)
        p.drawPath(path)
        p.setPen(QPen(QColor(RED), 3))
        p.drawLine(4, 4, 18, 4); p.drawLine(4, 4, 4, 18)
        p.drawLine(w - 18, h - 6, w - 6, h - 6); p.drawLine(w - 6, h - 18, w - 6, h - 6)


# ─────────────────────────────────────────────────────────────────── #
#  Right column — transcript phone
# ─────────────────────────────────────────────────────────────────── #
class TranscriptPhone(QFrame):
    """Right-side phone-shaped scrolling transcript panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280); self.setMinimumHeight(560)
        lay = QVBoxLayout(self); lay.setContentsMargins(22, 36, 22, 36)
        title = QLabel("Transcript")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:white; font-size:14px; font-weight:700;")
        lay.addWidget(title)

        self.text = QTextEdit(); self.text.setObjectName("transcript")
        self.text.setReadOnly(True)
        self.text.setStyleSheet("background:transparent; color:#dff1ff; font-size:13px;")
        lay.addWidget(self.text, 1)

    def append(self, who: str, msg: str):
        color = "#9be3ff" if who == "you" else "#ffffff"
        prefix = "🗣 You" if who == "you" else "🤖 AERA"
        html = (f'<div style="margin-bottom:10px">'
                f'<span style="color:{color}; font-weight:700">{prefix}:</span>'
                f' <span style="color:#e6f3ff">{msg}</span></div>')
        self.text.append(html)
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        body = QRectF(2, 2, w - 4, h - 4)
        p.setPen(QPen(QColor(ACCENT), 4))
        p.setBrush(QBrush(QColor("#234b73")))
        p.drawRoundedRect(body, 30, 30)
        screen = QRectF(14, 24, w - 28, h - 48)
        p.setBrush(QBrush(QColor("#2a5a87")))
        p.setPen(QPen(QColor(ACCENT_DK), 1.5))
        p.drawRoundedRect(screen, 22, 22)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for x in range(int(screen.left()), int(screen.right()), 16):
            p.drawLine(x, int(screen.top()), x, int(screen.bottom()))
        for y in range(int(screen.top()), int(screen.bottom()), 16):
            p.drawLine(int(screen.left()), y, int(screen.right()), y)
        p.setBrush(QBrush(QColor(ORANGE))); p.setPen(Qt.NoPen)
        p.drawRect(QRectF(w - 8,  40, 6, 26))
        p.drawRect(QRectF(w - 8,  h - 90, 6, 50))
        p.drawRect(QRectF(2,      h - 140, 6, 60))
        p.setBrush(QBrush(QColor(255, 255, 255, 180)))
        for i in range(3):
            p.drawEllipse(QPointF(28 + i * 6, 40), 1.6, 1.6)


# ─────────────────────────────────────────────────────────────────── #
#  Top navigation bar
# ─────────────────────────────────────────────────────────────────── #
def make_icon_label(emoji: str, text: str) -> QPushButton:
    btn = QPushButton(f"  {emoji}   {text}")
    btn.setObjectName("navBtn")
    btn.setCheckable(True)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


class TopBar(QWidget):
    nav = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 8, 10, 8); lay.setSpacing(8)

        burger = QPushButton("☰"); burger.setFixedSize(34, 34)
        burger.setStyleSheet(f"background:{INK}; color:white; border-radius:6px; font-size:18px;")
        lay.addWidget(burger)

        logo = QPushButton("AERA Agent"); logo.setObjectName("logo")
        lay.addWidget(logo); lay.addStretch(1)

        self._buttons: dict[str, QPushButton] = {}
        for emoji, name in [("⌂", "Home"), ("▦", "Dashboard"),
                            ("🧠", "Macros"), ("📂", "Apps")]:
            b = make_icon_label(emoji, name)
            b.clicked.connect(lambda _=False, n=name: self._select(n))
            lay.addWidget(b); self._buttons[name] = b

        lay.addSpacing(40)

        for emoji, name in [("🎙", "Studio"), ("🖼", "Gallery"),
                            ("📞", "Phone"), ("⚙", "Settings")]:
            b = make_icon_label(emoji, name)
            b.clicked.connect(lambda _=False, n=name: self._select(n))
            lay.addWidget(b); self._buttons[name] = b

        lay.addStretch(1)

        for sym, obj in [("—", "winBtn"), ("▢", "winBtn"), ("✕", "closeBtn")]:
            b = QPushButton(sym); b.setObjectName(obj); b.setFixedSize(32, 28)
            lay.addWidget(b)
            if sym == "—":  b.clicked.connect(lambda: self.window().showMinimized())
            if sym == "▢":  b.clicked.connect(self._toggle_max)
            if sym == "✕":  b.clicked.connect(lambda: self.window().close())

        self._buttons["Home"].setChecked(True)

    def _toggle_max(self):
        w = self.window()
        if w.isMaximized(): w.showNormal()
        else: w.showMaximized()

    def _select(self, name: str):
        for n, b in self._buttons.items():
            b.setChecked(n == name)
        self.nav.emit(name)


# ─────────────────────────────────────────────────────────────────── #
#  Home page — particle orb + TAP TO SPEAK
# ─────────────────────────────────────────────────────────────────── #
class HomePage(QWidget):
    tap = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 10, 20, 30); lay.setSpacing(10)

        self.orb = ParticleOrb()
        lay.addWidget(self.orb, 1)

        btn_row = QHBoxLayout(); btn_row.addStretch(1)
        self.tap_btn = QPushButton("🎙  TAP TO SPEAK")
        self.tap_btn.setObjectName("tapBtn")
        self.tap_btn.setCursor(Qt.PointingHandCursor)
        self.tap_btn.clicked.connect(self.tap.emit)
        btn_row.addWidget(self.tap_btn); btn_row.addStretch(1)
        lay.addLayout(btn_row)


def placeholder(title: str, subtitle: str = "") -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignCenter)
    t = QLabel(title); t.setObjectName("bigTitle"); t.setAlignment(Qt.AlignCenter)
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle); s.setStyleSheet("color:#666;"); s.setAlignment(Qt.AlignCenter)
        lay.addWidget(s)
    return w

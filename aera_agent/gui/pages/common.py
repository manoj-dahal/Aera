"""Shared mini-widgets used by all pages."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ...theme import (
    ACCENT, ACCENT_DK, ORANGE, RED, PANEL, INK, MUTED, BORDER,
    CARD_QSS,
)

class Card(QFrame):
    """Standard panel card with optional uppercase title."""
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_QSS)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 12, 14, 12)
        self.lay.setSpacing(8)
        if title:
            t = QLabel(title.upper())
            t.setObjectName("cardTitle")
            self.lay.addWidget(t)


class StatPill(QFrame):
    """Big number with label underneath, for the dashboard."""
    _BASE_QSS = (
        f"QFrame {{ background:{PANEL}; border:1px solid {BORDER};"
        f" border-radius:14px; }} QLabel {{ border:none; }}"
    )
    _LABEL_QSS = f"color:{MUTED}; font-size:10px; letter-spacing:1px; font-weight:700;"

    def __init__(self, label: str, color: str = ACCENT):
        super().__init__()
        self.setMinimumHeight(90)
        self.setStyleSheet(self._BASE_QSS)
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 10, 14, 10)
        self.value = QLabel("—")
        self.value.setStyleSheet(f"font-size:26px; font-weight:800; color:{color};")
        self.label = QLabel(label.upper())
        self.label.setStyleSheet(self._LABEL_QSS)
        lay.addWidget(self.value); lay.addWidget(self.label); lay.addStretch(1)

    def set(self, text: str):
        self.value.setText(text)


class Sparkline(QWidget):
    """Tiny rolling line chart."""
    def __init__(self, color=ACCENT, max_points=60):
        super().__init__()
        self.color = QColor(color)
        self.max_points = max_points
        self.points: list[float] = []
        self.setMinimumHeight(60)

    def push(self, v: float):
        self.points.append(v)
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]
        self.update()

    def paintEvent(self, _):
        if not self.points: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        mx = max(self.points) or 1
        step = w / max(len(self.points) - 1, 1)
        path = QPainterPath()
        for i, v in enumerate(self.points):
            x = i * step
            y = h - (v / mx) * (h - 6) - 3
            if i == 0: path.moveTo(x, y)
            else:      path.lineTo(x, y)
        # fill
        fill = QPainterPath(path); fill.lineTo(w, h); fill.lineTo(0, h); fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        c1 = QColor(self.color); c1.setAlpha(80); grad.setColorAt(0, c1)
        c2 = QColor(self.color); c2.setAlpha(0);  grad.setColorAt(1, c2)
        p.fillPath(fill, QBrush(grad))
        p.setPen(QPen(self.color, 2)); p.drawPath(path)


# ============================================================ #
#  1. DASHBOARD  — live system + assistant stats
# ============================================================ #



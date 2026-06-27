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



class PhonePage(QWidget):
    fire = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(14)

        # left: contact list
        left = Card("Contacts")
        self.list = QListWidget()
        self.list.setStyleSheet(LIST_QSS)
        self.list.itemClicked.connect(self._select)
        left.lay.addWidget(self.list, 1)
        add = QPushButton("＋ Add contact"); add.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: white; border: none;"
            f"border-radius: 10px; padding: 8px 16px; font-weight: 700; }}")
        add.clicked.connect(self._add)
        left.lay.addWidget(add)
        lay.addWidget(left, 1)

        # right: dialer + actions
        right = QVBoxLayout(); right.setSpacing(12)
        title = QLabel("Phone"); title.setStyleSheet(TITLE_QSS)
        right.addWidget(title)

        self.detail = Card("Selected")
        self.detail_name = QLabel("(no contact)")
        self.detail_name.setStyleSheet("font-size: 18px; font-weight: 700; border: none;")
        self.detail_num = QLabel("—"); self.detail_num.setStyleSheet(f"color: {MUTED}; border: none;")
        self.detail.lay.addWidget(self.detail_name); self.detail.lay.addWidget(self.detail_num)
        btns = QHBoxLayout()
        for label, kind in [("📞 Call", "call"), ("💬 Message", "msg"), ("📧 Email", "mail")]:
            b = QPushButton(label); b.setStyleSheet(
                f"QPushButton {{ background: {PANEL}; border: 1.5px solid {ACCENT}; color: {ACCENT_DK};"
                f"padding: 10px; border-radius: 10px; font-weight: 700; }}"
                f"QPushButton:hover {{ background: {ACCENT}; color: white; }}")
            b.clicked.connect(lambda _=False, k=kind: self._action(k))
            btns.addWidget(b)
        self.detail.lay.addLayout(btns)
        right.addWidget(self.detail)

        dialer = Card("Dial Pad")
        grid = QGridLayout(); grid.setSpacing(6)
        keys = ["1","2","3","4","5","6","7","8","9","*","0","#"]
        self.dialed = QLineEdit()
        self.dialed.setStyleSheet(f"font-size: 22px; padding: 10px; border: 1px solid {BORDER}; border-radius: 8px;")
        dialer.lay.addWidget(self.dialed)
        for i, k in enumerate(keys):
            r, c = divmod(i, 3)
            b = QPushButton(k); b.setFixedHeight(40)
            b.setStyleSheet(f"QPushButton {{ background: {PANEL}; border: 1px solid {BORDER};"
                            f"border-radius: 10px; font-size: 16px; font-weight: 700; }}"
                            f"QPushButton:hover {{ background: #eaf3ff; }}")
            b.clicked.connect(lambda _=False, key=k: self.dialed.setText(self.dialed.text() + key))
            grid.addWidget(b, r, c)
        dialer.lay.addLayout(grid)
        right.addWidget(dialer)
        right.addStretch(1)

        rw = QWidget(); rw.setLayout(right); rw.setFixedWidth(380)
        lay.addWidget(rw)

        self.contacts = self._load()
        self._render()
        self.selected_idx = None

    def _load(self):
        if CONTACTS_FILE.exists():
            try: return json.loads(CONTACTS_FILE.read_text())
            except Exception: pass
        return [{"name": "AERA Voicemail", "number": "+1-555-AERA", "email": ""}]

    def _save(self): CONTACTS_FILE.write_text(json.dumps(self.contacts, indent=2))

    def _render(self):
        self.list.clear()
        for c in self.contacts:
            self.list.addItem(f"{c['name']}    {c['number']}")

    def _select(self, _item):
        i = self.list.currentRow()
        if i < 0: return
        self.selected_idx = i
        c = self.contacts[i]
        self.detail_name.setText(c["name"])
        self.detail_num.setText(c["number"])

    def _action(self, kind: str):
        if self.selected_idx is None: return
        c = self.contacts[self.selected_idx]
        if kind == "call":
            self.fire.emit(f"Call {c['name']} at {c['number']}.")
        elif kind == "msg":
            self.fire.emit(f"Send a message to {c['name']}.")
        elif kind == "mail":
            self.fire.emit(f"Compose an email to {c['name']} at {c.get('email','')}.")

    def _add(self):
        dlg = ContactDialog({"name": "", "number": "", "email": ""}, self)
        if dlg.exec():
            self.contacts.append(dlg.value()); self._save(); self._render()


class ContactDialog(QDialog):
    def __init__(self, c, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Contact")
        f = QFormLayout(self)
        self.n = QLineEdit(c["name"]); self.p = QLineEdit(c["number"]); self.e = QLineEdit(c["email"])
        f.addRow("Name:", self.n); f.addRow("Number:", self.p); f.addRow("Email:", self.e)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def value(self):
        return {"name": self.n.text(), "number": self.p.text(), "email": self.e.text()}


# ============================================================ #
#  6. SETTINGS  — providers, voice, STT, wake-word, memory
# ============================================================ #



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



class GalleryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dir = GALLERY_DIR

        lay = QVBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("Gallery"); t.setStyleSheet(TITLE_QSS)
        hdr.addWidget(t); hdr.addStretch(1)
        refresh = QPushButton("⟳ Refresh"); refresh.setStyleSheet(primary_btn())
        refresh.clicked.connect(self.refresh); hdr.addWidget(refresh)
        add = QPushButton("＋ Import"); add.setStyleSheet(primary_btn())
        add.clicked.connect(self._import); hdr.addWidget(add)
        lay.addLayout(hdr)

        sub = QLabel(f"Folder: {self.dir}")
        sub.setStyleSheet(HINT_QSS)
        lay.addWidget(sub)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border:none;")
        body = QWidget(); self.grid = QGridLayout(body); self.grid.setSpacing(10)
        scroll.setWidget(body); lay.addWidget(scroll, 1)
        self.refresh()

    def refresh(self):
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
        imgs = sorted([p for p in self.dir.iterdir() if p.suffix.lower() in exts])
        if not imgs:
            l = QLabel("No images yet. Drop files into workspace/gallery/ or click Import.")
            l.setStyleSheet(f"color: {MUTED}; padding: 20px;")
            self.grid.addWidget(l, 0, 0); return
        cols = 4
        for i, p in enumerate(imgs):
            r, c = divmod(i, cols)
            self.grid.addWidget(self._thumb(p), r, c)

    def _thumb(self, path: Path):
        w = QFrame(); w.setFixedSize(220, 200)
        w.setStyleSheet(f"QFrame {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius:12px; }}"
                        f"QFrame:hover {{ border-color: {ACCENT}; }}")
        v = QVBoxLayout(w); v.setContentsMargins(8, 8, 8, 8)
        img = QLabel(); img.setAlignment(Qt.AlignCenter); img.setStyleSheet("border:none;")
        pm = QPixmap(str(path))
        if not pm.isNull():
            pm = pm.scaled(QSize(200, 150), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img.setPixmap(pm)
        v.addWidget(img, 1)
        nm = QLabel(path.name); nm.setAlignment(Qt.AlignCenter); nm.setStyleSheet("font-size:11px; border:none;")
        nm.setWordWrap(True)
        v.addWidget(nm)
        return w

    def _import(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import images", "",
                                                 "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)")
        import shutil
        for f in files:
            try: shutil.copy(f, self.dir / Path(f).name)
            except Exception as e: print(e)
        self.refresh()

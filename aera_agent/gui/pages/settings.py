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
from ...memory import graph as _memory_graph
from ...paths import MEMORY_FILE



class SettingsPage(QWidget):
    config_changed = Signal()

    def __init__(self, cfg_obj, parent=None):
        super().__init__(parent)
        self.cfg = cfg_obj                # voice_assistant.Config instance
        lay = QHBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(14)

        # nav (left)
        nav = QVBoxLayout(); nav.setSpacing(6)
        title = QLabel("Settings"); title.setStyleSheet(TITLE_QSS)
        nav.addWidget(title); nav.addSpacing(10)
        self.nav_buttons = {}
        for label in ("Provider", "Voice", "Speech", "Wake word", "Memory", "About"):
            b = QPushButton(label); b.setCheckable(True)
            b.setStyleSheet(f"""
                QPushButton {{ text-align: left; padding: 10px 14px; border: none;
                               border-radius: 10px; font-size: 13px; }}
                QPushButton:hover {{ background: #eaf3ff; }}
                QPushButton:checked {{ background: {ACCENT}; color: white; font-weight: 700; }}
            """)
            b.clicked.connect(lambda _=False, n=label: self._show(n))
            nav.addWidget(b)
            self.nav_buttons[label] = b
        nav.addStretch(1)
        navw = QWidget(); navw.setLayout(nav); navw.setFixedWidth(180)
        lay.addWidget(navw)

        # pages
        self.stack = QStackedWidget()
        self.pages_map = {
            "Provider":  self._page_provider(),
            "Voice":     self._page_voice(),
            "Speech":    self._page_speech(),
            "Wake word": self._page_wake(),
            "Memory":    self._page_memory(),
            "About":     self._page_about(),
        }
        for w in self.pages_map.values(): self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)
        self._show("Provider")

    def _show(self, name: str):
        for n, b in self.nav_buttons.items(): b.setChecked(n == name)
        self.stack.setCurrentWidget(self.pages_map[name])

    # ---------- pages ----------
    def _page_provider(self):
        w = Card("LLM Provider")
        d = self.cfg.data
        self.prov_combo = QComboBox(); self.prov_combo.addItems(list(d["providers"].keys()))
        self.prov_combo.setCurrentText(d["active_provider"])
        self.prov_combo.currentTextChanged.connect(self._load_provider)
        self.base_url = QLineEdit(); self.api_key = QLineEdit(); self.model_name = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Active provider:", self.prov_combo)
        form.addRow("Base URL:", self.base_url)
        form.addRow("API key:", self.api_key)
        form.addRow("Model name:", self.model_name)

        btns = QHBoxLayout()
        save = QPushButton("Save"); save.setStyleSheet(primary_btn())
        save.clicked.connect(self._save_provider)
        addp = QPushButton("＋ Add provider"); addp.setStyleSheet(primary_btn())
        addp.clicked.connect(self._add_provider)
        btns.addWidget(save); btns.addWidget(addp); btns.addStretch(1)

        w.lay.addLayout(form); w.lay.addLayout(btns); w.lay.addStretch(1)
        self._load_provider(self.prov_combo.currentText())
        return w

    def _load_provider(self, name: str):
        p = self.cfg.data["providers"].get(name, {})
        self.base_url.setText(p.get("base_url", ""))
        self.api_key.setText(p.get("api_key", ""))
        self.model_name.setText(p.get("model", ""))

    def _save_provider(self):
        name = self.prov_combo.currentText()
        self.cfg.data["providers"][name] = {
            "base_url": self.base_url.text(),
            "api_key":  self.api_key.text(),
            "model":    self.model_name.text(),
        }
        self.cfg.data["active_provider"] = name
        self.cfg.save()
        self.config_changed.emit()
        QMessageBox.information(self, "Saved", "Provider settings saved. Restart for full effect.")

    def _add_provider(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New provider", "Name (e.g. mycloud):")
        if ok and name:
            self.cfg.data["providers"][name] = {
                "base_url": "https://api.example.com/v1",
                "api_key":  "YOUR_KEY",
                "model":    "model-name",
            }
            self.cfg.save()
            self.prov_combo.addItem(name); self.prov_combo.setCurrentText(name)

    def _page_voice(self):
        w = Card("Text-to-Speech")
        v = self.cfg.data["voice"]
        self.tts_engine = QComboBox()
        self.tts_engine.addItems(["pyttsx3", "piper", "omnivoice"])
        self.tts_engine.setCurrentText(v.get("engine", "pyttsx3"))
        self.piper_voice = QLineEdit(v.get("model", "en_US-lessac-medium"))
        self.omni_model = QLineEdit(v.get("model_id", "k2-fsa/OmniVoice-v0"))
        self.omni_device = QComboBox(); self.omni_device.addItems(["auto","cuda","mps","cpu"])
        self.omni_device.setCurrentText(v.get("device","auto"))
        self.omni_lang = QLineEdit(v.get("language","en"))
        self.omni_ref_audio = QLineEdit(v.get("ref_audio",""))
        self.omni_ref_text  = QLineEdit(v.get("ref_text",""))
        self.omni_design    = QLineEdit(v.get("voice_design",""))

        self.rate_slider = QSlider(Qt.Horizontal); self.rate_slider.setRange(80, 320)
        self.rate_slider.setValue(int(v.get("rate", 180)))
        self.rate_label = QLabel(f"{self.rate_slider.value()} wpm")
        self.rate_slider.valueChanged.connect(lambda val: self.rate_label.setText(f"{val} wpm"))

        self.vol_slider = QSlider(Qt.Horizontal); self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(v.get("volume", 1.0) * 100))
        self.vol_label = QLabel(f"{self.vol_slider.value()}%")
        self.vol_slider.valueChanged.connect(lambda val: self.vol_label.setText(f"{val}%"))

        form = QFormLayout()
        form.addRow("Engine:", self.tts_engine)
        rate_row = QHBoxLayout(); rate_row.addWidget(self.rate_slider); rate_row.addWidget(self.rate_label)
        form.addRow("Rate:", rate_row)
        vol_row = QHBoxLayout(); vol_row.addWidget(self.vol_slider); vol_row.addWidget(self.vol_label)
        form.addRow("Volume:", vol_row)
        form.addRow(QLabel("──── Piper ────"))
        form.addRow("Piper voice:", self.piper_voice)
        form.addRow(QLabel("──── OmniVoice ────"))
        form.addRow("Model id:", self.omni_model)
        form.addRow("Device:", self.omni_device)
        form.addRow("Language:", self.omni_lang)
        form.addRow("Clone ref audio (wav):", self.omni_ref_audio)
        form.addRow("Clone ref transcript:", self.omni_ref_text)
        form.addRow("Or voice design text:", self.omni_design)

        save = QPushButton("Save"); save.setStyleSheet(primary_btn())
        save.clicked.connect(self._save_voice)
        w.lay.addLayout(form); w.lay.addWidget(save); w.lay.addStretch(1)

        hint = QLabel(
            "Piper voices:  python -m piper.download_voices en_GB-jenny_dioco-medium\n"
            "OmniVoice:     auto-downloads on first run (~3-5 GB, needs CUDA for realtime).\n"
            "Voice clone:   put a 5-15 s wav in voices/ and paste exact transcript above.")
        hint.setStyleSheet(HINT_QSS)
        w.lay.addWidget(hint)
        return w

    def _save_voice(self):
        v = self.cfg.data["voice"]
        v["engine"]       = self.tts_engine.currentText()
        v["model"]        = self.piper_voice.text()
        v["rate"]         = self.rate_slider.value()
        v["volume"]       = self.vol_slider.value() / 100.0
        v["model_id"]     = self.omni_model.text()
        v["device"]       = self.omni_device.currentText()
        v["language"]     = self.omni_lang.text()
        v["ref_audio"]    = self.omni_ref_audio.text()
        v["ref_text"]     = self.omni_ref_text.text()
        v["voice_design"] = self.omni_design.text()
        self.cfg.save(); self.config_changed.emit()
        QMessageBox.information(self, "Saved", "Voice settings saved. Restart to apply.")

    def _page_speech(self):
        w = Card("Speech Recognition")
        s = self.cfg.data["speech"]
        self.stt_engine  = QComboBox(); self.stt_engine.addItems(["google", "sensevoice"])
        self.stt_engine.setCurrentText(s.get("engine", "google"))
        self.stt_lang    = QLineEdit(s.get("language", "en-US"))
        self.stt_device  = QComboBox(); self.stt_device.addItems(["auto","cuda","mps","cpu"])
        self.stt_device.setCurrentText(s.get("device","auto"))
        self.stt_timeout = QSpinBox(); self.stt_timeout.setRange(1, 30); self.stt_timeout.setValue(s.get("timeout", 5))
        self.stt_phrase  = QSpinBox(); self.stt_phrase.setRange(2, 60); self.stt_phrase.setValue(s.get("phrase_time_limit", 15))
        self.stt_energy  = QSpinBox(); self.stt_energy.setRange(50, 4000); self.stt_energy.setValue(s.get("energy_threshold", 300))
        self.stt_pause   = QDoubleSpinBox(); self.stt_pause.setRange(0.2, 3.0); self.stt_pause.setSingleStep(0.1)
        self.stt_pause.setValue(s.get("pause_threshold", 0.8))
        self.stt_silence = QSpinBox(); self.stt_silence.setRange(200, 3000); self.stt_silence.setValue(s.get("vad_silence_ms", 700))

        f = QFormLayout()
        f.addRow("Engine:", self.stt_engine)
        f.addRow("Language code:", self.stt_lang)
        f.addRow(QLabel("──── Google (SpeechRecognition) ────"))
        f.addRow("Listen timeout (s):", self.stt_timeout)
        f.addRow("Phrase time limit (s):", self.stt_phrase)
        f.addRow("Energy threshold:", self.stt_energy)
        f.addRow("Pause threshold (s):", self.stt_pause)
        f.addRow(QLabel("──── SenseVoice (offline, multilingual) ────"))
        f.addRow("Device:", self.stt_device)
        f.addRow("Silence to stop (ms):", self.stt_silence)
        hint = QLabel("SenseVoice languages: 'auto', 'en', 'zh', 'ja', 'ko', 'yue'.\n"
                      "Install:  pip install funasr soundfile sounddevice webrtcvad numpy")
        hint.setStyleSheet(HINT_QSS)
        save = QPushButton("Save"); save.setStyleSheet(primary_btn()); save.clicked.connect(self._save_speech)
        w.lay.addLayout(f); w.lay.addWidget(hint); w.lay.addWidget(save); w.lay.addStretch(1)
        return w

    def _save_speech(self):
        s = self.cfg.data["speech"]
        s["engine"]   = self.stt_engine.currentText()
        s["language"] = self.stt_lang.text()
        s["device"]   = self.stt_device.currentText()
        s["timeout"] = self.stt_timeout.value()
        s["phrase_time_limit"] = self.stt_phrase.value()
        s["energy_threshold"] = self.stt_energy.value()
        s["pause_threshold"] = self.stt_pause.value()
        s["vad_silence_ms"] = self.stt_silence.value()
        self.cfg.save(); self.config_changed.emit()
        QMessageBox.information(self, "Saved", "Speech settings saved. Restart to apply.")

    def _page_wake(self):
        w = Card("Wake Word")
        wake = self.cfg.data.get("wake", {"enabled": False, "phrase": "hey aera"})
        self.wake_enabled = QCheckBox("Enable always-listening wake-word detector")
        self.wake_enabled.setChecked(wake.get("enabled", False))
        self.wake_phrase = QLineEdit(wake.get("phrase", "hey aera"))

        f = QFormLayout()
        f.addRow(self.wake_enabled)
        f.addRow("Wake phrase:", self.wake_phrase)
        info = QLabel(
            "When enabled, the assistant runs a lightweight always-on\n"
            "speech recognizer in the background. When it hears the wake\n"
            "phrase, it triggers a normal listen cycle automatically.\n\n"
            "For higher accuracy & lower CPU, install pvporcupine and set\n"
            "phrase to one of its built-in keywords (computer, terminator,\n"
            "blueberry, picovoice, etc.). 'AERA' isn't a built-in keyword —\n"
            "for a true 'Hey AERA' wake phrase, use the speech-recognition\n"
            "backend (slower but free and accepts any phrase)."
        )
        info.setStyleSheet(HINT_QSS)
        save = QPushButton("Save"); save.setStyleSheet(primary_btn()); save.clicked.connect(self._save_wake)
        w.lay.addLayout(f); w.lay.addWidget(info); w.lay.addWidget(save); w.lay.addStretch(1)
        return w

    def _save_wake(self):
        self.cfg.data["wake"] = {
            "enabled": self.wake_enabled.isChecked(),
            "phrase":  self.wake_phrase.text().lower().strip(),
        }
        self.cfg.save(); self.config_changed.emit()
        QMessageBox.information(self, "Saved", "Wake word settings saved. Restart to apply.")

    def _page_memory(self):
        w = Card("Long-term Memory")
        from ...memory import graph as _g
        self._mem = _g()
        self.mem_stats = QLabel(self._mem.stats())
        self.mem_stats.setStyleSheet("font-size: 13px;")
        self.mem_view = QTextEdit(); self.mem_view.setReadOnly(True)
        self.mem_view.setStyleSheet(f"background: #fafafa; border: 1px solid {BORDER}; border-radius:8px;"
                                    f"font-family: monospace; font-size: 11px;")
        self.mem_view.setPlainText(self._mem.about("user", depth=2))

        btns = QHBoxLayout()
        for label, fn in [("Refresh", self._mem_refresh),
                          ("Search…", self._mem_search),
                          ("Export JSON", self._mem_export),
                          ("Clear all", self._mem_clear)]:
            b = QPushButton(label); b.setStyleSheet(primary_btn())
            b.clicked.connect(fn); btns.addWidget(b)

        w.lay.addWidget(self.mem_stats); w.lay.addLayout(btns)
        w.lay.addWidget(self.mem_view, 1)
        return w

    def _mem_refresh(self):
        from ...memory import graph as _g
        g = _g()
        self.mem_stats.setText(g.stats())
        self.mem_view.setPlainText(g.about("user", depth=2))

    def _mem_search(self):
        from PySide6.QtWidgets import QInputDialog
        from ...memory import graph as _g
        q, ok = QInputDialog.getText(self, "Memory search", "Query:")
        if ok and q: self.mem_view.setPlainText(_g().search(q))

    def _mem_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export memory", "memory_export.json", "JSON (*.json)")
        if path:
            from ...paths import MEMORY_FILE as MEM_FILE
            Path(path).write_text(MEM_FILE.read_text() if MEM_FILE.exists() else "{}")
            QMessageBox.information(self, "Exported", path)

    def _mem_clear(self):
        if QMessageBox.question(self, "Confirm", "Wipe all long-term memory?") == QMessageBox.Yes:
            from ...memory import graph as _g
            _g().clear()
            self._mem_refresh()

    def _page_about(self):
        w = Card("About AERA Agent")
        txt = QLabel(
            "<h3>AERA Agent</h3>"
            "<p>A customizable voice AI assistant.</p>"
            "<p><b>Components:</b><br>"
            "• OpenAI-compatible LLM client (Groq / Gemini / OpenAI / Ollama / …)<br>"
            "• Speech-to-text via SpeechRecognition<br>"
            "• Text-to-speech via Piper (neural) or pyttsx3 (offline)<br>"
            "• 40+ agent tools (weather, web, timers, files, memory, …)<br>"
            "• Graph-based long-term memory<br>"
            "• Wake-word detection<br>"
            "• PySide6 desktop UI</p>"
            "<p style='color:#666'>Edit config.json directly for advanced options.</p>"
        )
        txt.setWordWrap(True); txt.setStyleSheet("border: none;")
        w.lay.addWidget(txt); w.lay.addStretch(1)
        return w



"""
First-run setup wizard.

Shown automatically the first time AERA launches (when no config.json
exists, or when the active provider's api_key is still a YOUR_*_API_KEY
placeholder). Lets the user pick a provider and paste their key without
ever editing JSON by hand.
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QDialog, QWidget, QLabel, QPushButton, QLineEdit, QComboBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QStackedWidget,
    QCheckBox, QMessageBox,
)

from ..paths import CONFIG_FILE, ASSETS_DIR
from ..theme import ACCENT, ACCENT_DK, INK, MUTED, BORDER, PANEL


# ── default config the wizard writes if config.json doesn't exist ── #
_BLANK_CONFIG = {
    "active_provider": "groq",
    "providers": {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "YOUR_GROQ_API_KEY",
            "model": "llama-3.3-70b-versatile",
        },
        "google": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": "YOUR_GOOGLE_API_KEY",
            "model": "gemini-2.0-flash",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "YOUR_OPENAI_API_KEY",
            "model": "gpt-4o-mini",
        },
        "ollama_local": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "model": "llama3.2",
        },
    },
    "system_prompt": "You are AERA, a helpful, concise voice assistant with access to tools "
                     "and a persistent long-term memory graph. Keep replies short and natural "
                     "since they will be spoken aloud. Avoid markdown, code blocks, and long "
                     "lists unless asked. Use tools whenever they would give a more accurate "
                     "or up-to-date answer.",
    "voice":  {"engine": "pyttsx3", "rate": 180, "volume": 1.0, "voice_index": 0,
               "model": "en_US-lessac-medium", "device": "auto",
               "language": "en", "ref_audio": "", "ref_text": "",
               "voice_design": "", "num_step": 32, "guidance_scale": 2.0,
               "model_id": "k2-fsa/OmniVoice-v0",
               "noise_scale": 0.667, "noise_w_scale": 0.8, "use_cuda": False},
    "speech": {"engine": "google", "language": "en-US",
               "timeout": 5, "phrase_time_limit": 15,
               "energy_threshold": 300, "pause_threshold": 0.8,
               "device": "auto", "vad_silence_ms": 700, "max_record_s": 15},
    "wake":   {"enabled": False, "phrase": "hey aera", "access_key": ""},
    "exit_phrases": ["exit", "quit", "goodbye", "stop assistant"],
}


# ─────────────────────────────────────────────────────────────── #
#  Provider catalog with how-to links
# ─────────────────────────────────────────────────────────────── #
_PROVIDERS = [
    {
        "key":   "groq",
        "label": "Groq  (free, fast — recommended)",
        "url":   "https://console.groq.com/keys",
        "blurb": "Free tier, no credit card. Llama 3.3 70B at lightning speed.",
        "model_default": "llama-3.3-70b-versatile",
        "model_options": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant",
                          "mixtral-8x7b-32768", "gemma2-9b-it"],
    },
    {
        "key":   "google",
        "label": "Google Gemini  (free tier)",
        "url":   "https://aistudio.google.com/apikey",
        "blurb": "Generous free tier. Gemini 2.0 Flash is fast and supports tools.",
        "model_default": "gemini-2.0-flash",
        "model_options": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    },
    {
        "key":   "openai",
        "label": "OpenAI  (paid)",
        "url":   "https://platform.openai.com/api-keys",
        "blurb": "Most polished but costs $. GPT-4o-mini is cheapest.",
        "model_default": "gpt-4o-mini",
        "model_options": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    },
    {
        "key":   "ollama_local",
        "label": "Ollama  (100% local, no API key)",
        "url":   "https://ollama.com",
        "blurb": "Runs Llama on your machine. Needs 8 GB+ RAM. `ollama pull llama3.2` first.",
        "model_default": "llama3.2",
        "model_options": ["llama3.2", "qwen2.5:7b", "mistral", "phi3"],
    },
]


# ─────────────────────────────────────────────────────────────── #
#  Wizard dialog
# ─────────────────────────────────────────────────────────────── #
class SetupWizard(QDialog):
    """Two-step wizard: pick provider → paste key + pick model."""

    finished_ok = Signal()

    def __init__(self, parent=None, initial_config: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to AERA Agent")
        self.setMinimumSize(640, 480)
        self.setStyleSheet(self._qss())
        self.config = initial_config or json.loads(json.dumps(_BLANK_CONFIG))
        self.selected_provider = "groq"

        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        # header banner
        header = QFrame(); header.setObjectName("header"); header.setFixedHeight(120)
        hlay = QHBoxLayout(header); hlay.setContentsMargins(28, 18, 28, 18)
        try:
            icon_path = ASSETS_DIR / "aera_icon.png"
            if icon_path.exists():
                icon = QLabel()
                icon.setPixmap(QPixmap(str(icon_path))
                               .scaledToHeight(80, Qt.SmoothTransformation))
                hlay.addWidget(icon)
        except Exception:
            pass
        title = QVBoxLayout()
        t = QLabel("AERA Agent"); t.setObjectName("hTitle")
        s = QLabel("Let's get you set up in under a minute."); s.setObjectName("hSub")
        title.addWidget(t); title.addWidget(s); title.addStretch(1)
        hlay.addLayout(title, 1)
        outer.addWidget(header)

        # body — stacked steps
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)
        self._build_step_provider()
        self._build_step_key()

        # footer buttons
        footer = QFrame(); footer.setObjectName("footer")
        flay = QHBoxLayout(footer); flay.setContentsMargins(20, 14, 20, 14)
        self.back_btn = QPushButton("← Back");   self.back_btn.setObjectName("ghost")
        self.next_btn = QPushButton("Continue →")
        self.skip_btn = QPushButton("Skip for now")
        self.skip_btn.setObjectName("ghost")
        self.back_btn.clicked.connect(self._back)
        self.next_btn.clicked.connect(self._next)
        self.skip_btn.clicked.connect(self._skip)
        flay.addWidget(self.skip_btn); flay.addStretch(1)
        flay.addWidget(self.back_btn); flay.addWidget(self.next_btn)
        outer.addWidget(footer)

        self._show_step(0)

    # ----------------------------------------------------- #
    #  Step 1 — pick provider
    # ----------------------------------------------------- #
    def _build_step_provider(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 24, 28, 24); lay.setSpacing(12)

        head = QLabel("Choose your LLM provider")
        head.setObjectName("stepTitle"); lay.addWidget(head)

        sub = QLabel("AERA talks to a large language model to think. Pick one — "
                     "you can change it later in Settings.")
        sub.setWordWrap(True); sub.setObjectName("stepSub"); lay.addWidget(sub)
        lay.addSpacing(6)

        self.provider_buttons: dict[str, QPushButton] = {}
        for p in _PROVIDERS:
            row = QPushButton(); row.setObjectName("provider")
            row.setCheckable(True); row.setCursor(Qt.PointingHandCursor)
            row.setMinimumHeight(68)
            row.setText(f"{p['label']}\n     {p['blurb']}")
            row.clicked.connect(lambda _=False, k=p['key']: self._pick_provider(k))
            lay.addWidget(row)
            self.provider_buttons[p["key"]] = row

        lay.addStretch(1)
        self.provider_buttons["groq"].setChecked(True)
        self.stack.addWidget(page)

    def _pick_provider(self, key: str):
        self.selected_provider = key
        for k, btn in self.provider_buttons.items():
            btn.setChecked(k == key)

    # ----------------------------------------------------- #
    #  Step 2 — paste key + choose model
    # ----------------------------------------------------- #
    def _build_step_key(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(28, 24, 28, 24); lay.setSpacing(12)

        self.key_title = QLabel(); self.key_title.setObjectName("stepTitle")
        lay.addWidget(self.key_title)
        self.key_hint = QLabel(); self.key_hint.setObjectName("stepSub")
        self.key_hint.setWordWrap(True); self.key_hint.setOpenExternalLinks(True)
        lay.addWidget(self.key_hint)
        lay.addSpacing(8)

        form = QFormLayout(); form.setSpacing(10)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Paste your API key here")
        self.show_key = QCheckBox("show")
        self.show_key.toggled.connect(
            lambda on: self.key_input.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        krow = QHBoxLayout(); krow.addWidget(self.key_input, 1); krow.addWidget(self.show_key)
        kwrap = QWidget(); kwrap.setLayout(krow)
        form.addRow("API key:", kwrap)

        self.model_combo = QComboBox(); self.model_combo.setEditable(True)
        form.addRow("Model:", self.model_combo)

        self.name_input = QLineEdit("You")
        form.addRow("Your name:", self.name_input)
        lay.addLayout(form)

        self.lower_hint = QLabel(
            "AERA will store this in <b>config.json</b> at the project root. "
            "You can change it anytime from <b>Settings → Provider</b>.")
        self.lower_hint.setObjectName("stepSub"); self.lower_hint.setWordWrap(True)
        lay.addWidget(self.lower_hint)
        lay.addStretch(1)
        self.stack.addWidget(page)

    def _refresh_key_step(self):
        p = next(p for p in _PROVIDERS if p["key"] == self.selected_provider)
        self.key_title.setText(f"Connect to {p['label'].split('  ')[0]}")
        if p["key"] == "ollama_local":
            self.key_hint.setText(
                f"Ollama runs locally so no real API key is needed.<br>"
                f"<b>Setup:</b> install from <a href='{p['url']}'>ollama.com</a>, "
                f"then run <code>ollama pull {p['model_default']}</code> in a terminal.<br>"
                f"Leave the API key as the word <i>ollama</i>.")
            self.key_input.setText("ollama")
        else:
            self.key_hint.setText(
                f"Get a free API key here: <a href='{p['url']}'>{p['url']}</a><br>"
                f"{p['blurb']}")
            if self.key_input.text() in ("ollama", ""):
                self.key_input.clear()
        self.model_combo.clear()
        self.model_combo.addItems(p["model_options"])
        self.model_combo.setCurrentText(p["model_default"])

    # ----------------------------------------------------- #
    #  Navigation
    # ----------------------------------------------------- #
    def _show_step(self, i: int):
        self.stack.setCurrentIndex(i)
        if i == 1: self._refresh_key_step()
        self.back_btn.setVisible(i > 0)
        self.next_btn.setText("Finish & launch AERA" if i == 1 else "Continue →")

    def _back(self): self._show_step(max(0, self.stack.currentIndex() - 1))

    def _next(self):
        i = self.stack.currentIndex()
        if i == 0:
            self._show_step(1); return
        # Final step — save and finish
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing key",
                                "Please paste your API key (or use Skip to do it later).")
            return
        # write into the config
        self.config["active_provider"] = self.selected_provider
        self.config["providers"][self.selected_provider]["api_key"] = key
        self.config["providers"][self.selected_provider]["model"] = \
            self.model_combo.currentText().strip()
        # personalize the system prompt
        name = self.name_input.text().strip() or "the user"
        self.config["system_prompt"] = (
            f"You are AERA, a helpful, concise voice assistant talking to {name}. "
            "Keep replies short and natural since they'll be spoken aloud. "
            "Avoid markdown, code blocks, and long lists unless asked. "
            "Use tools when they'd give a more accurate or up-to-date answer."
        )
        CONFIG_FILE.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        self.finished_ok.emit()
        self.accept()

    def _skip(self):
        # write a placeholder config so the app at least starts
        if not CONFIG_FILE.exists():
            CONFIG_FILE.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        self.reject()

    # ----------------------------------------------------- #
    def _qss(self) -> str:
        return f"""
            QDialog {{ background: white; }}
            QFrame#header {{ background: qlineargradient(
                x1:0 y1:0 x2:1 y2:0,
                stop:0 {ACCENT_DK}, stop:1 {ACCENT}); color:white; }}
            QLabel#hTitle {{ color:white; font-size:26px; font-weight:800; letter-spacing:1px; }}
            QLabel#hSub   {{ color:#dff1ff; font-size:13px; }}

            QFrame#footer {{ background:#f7f9fb; border-top:1px solid {BORDER}; }}

            QLabel#stepTitle {{ font-size:20px; font-weight:800; color:{INK}; }}
            QLabel#stepSub   {{ font-size:12px; color:{MUTED}; }}

            QPushButton#provider {{
                text-align:left; padding:14px 20px;
                background:white; border:1.5px solid {BORDER}; border-radius:12px;
                font-size:14px; font-weight:600; color:{INK};
            }}
            QPushButton#provider:hover  {{ background:#f3f9ff; border-color:{ACCENT}; }}
            QPushButton#provider:checked {{ background:#eaf6ff; border-color:{ACCENT_DK};
                                             color:{ACCENT_DK}; }}

            QPushButton {{ background:{ACCENT}; color:white; border:none;
                           border-radius:10px; padding:10px 22px;
                           font-weight:700; font-size:13px; }}
            QPushButton:hover {{ background:{ACCENT_DK}; }}
            QPushButton#ghost {{ background:transparent; color:{MUTED};
                                  border:1px solid {BORDER}; }}
            QPushButton#ghost:hover {{ background:#f3f6fb; color:{INK}; }}

            QLineEdit, QComboBox {{
                padding:8px 10px; border:1.5px solid {BORDER}; border-radius:8px;
                background:white; font-size:13px;
            }}
            QLineEdit:focus, QComboBox:focus {{ border-color:{ACCENT}; }}
            QCheckBox {{ font-size:12px; color:{MUTED}; }}
        """


# ─────────────────────────────────────────────────────────────── #
#  Helper used by gui/app.py at startup
# ─────────────────────────────────────────────────────────────── #
def needs_wizard() -> bool:
    """True if config.json is missing OR the active provider's key is a placeholder."""
    if not CONFIG_FILE.exists():
        return True
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        active = cfg["providers"][cfg["active_provider"]]
        key = active.get("api_key", "")
        return (not key) or key.startswith("YOUR_") or key == "PASTE_KEY_HERE"
    except Exception:
        return True


def run_wizard_if_needed(parent=None) -> bool:
    """Show the wizard if needed; return True if user completed it (or it was unnecessary)."""
    if not needs_wizard():
        return True
    dlg = SetupWizard(parent)
    result = dlg.exec()
    return result == QDialog.Accepted

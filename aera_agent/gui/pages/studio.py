"""
Voice Studio page — record, manage, and test voices for:
  • OmniVoice cloning (reference wav + transcript)
  • Speaker enrollment (biometric voice ID)
  • TTS voice preview

Self-contained PySide6 widget. Imported by gui.py.
"""

import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QInputDialog, QApplication,
)

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
except Exception:
    np = sd = sf = None

from ...theme import (
    ACCENT, ACCENT_DK, ORANGE, GREEN, RED, PANEL, INK, MUTED, BORDER,
    primary_btn, danger_btn, ghost_btn,
    TITLE_QSS, SUBTLE_QSS, LIST_QSS,
)
from .common import Card  # reuse the Card from pages.py — single source

from ...paths import VOICES_DIR


# ============================================================ #
#  Live waveform meter
# ============================================================ #
class WaveMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(60)
        self.levels: list[float] = [0.0] * 80
        self.recording = False
        self.t = QTimer(self); self.t.timeout.connect(self.update); self.t.start(50)

    def push(self, level: float):
        self.levels = self.levels[1:] + [min(1.0, level)]

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = w / len(self.levels)
        color = QColor(RED if self.recording else ACCENT)
        for i, lv in enumerate(self.levels):
            bar_h = max(2, lv * (h - 6))
            x = i * bar_w
            p.setBrush(color); p.setPen(Qt.NoPen)
            p.drawRoundedRect(x + 1, (h - bar_h) / 2, bar_w - 2, bar_h, 2, 2)


# ============================================================ #
#  Recorder worker (mic → wav + level callback)
# ============================================================ #
class Recorder:
    SR = 16000

    def __init__(self, on_level=None):
        self.on_level = on_level
        self._frames: list = []
        self._stop = threading.Event()
        self._stream = None
        self.recording = False

    def start(self):
        if sd is None or self.recording: return
        self._frames = []; self._stop.clear()
        def cb(indata, frames, t, status):
            if self._stop.is_set(): return
            chunk = indata[:, 0].copy()
            self._frames.append(chunk)
            if self.on_level:
                self.on_level(float(np.abs(chunk).mean()) * 8)
        try:
            self._stream = sd.InputStream(samplerate=self.SR, channels=1,
                                           dtype="float32", callback=cb)
            self._stream.start()
            self.recording = True
        except Exception as e:
            print(f"[recorder] {e}")

    def stop(self) -> Optional["np.ndarray"]:
        if not self.recording: return None
        self._stop.set()
        try:
            self._stream.stop(); self._stream.close()
        except Exception: pass
        self.recording = False
        if not self._frames: return None
        return np.concatenate(self._frames)

    def save(self, audio, path):
        sf.write(path, audio, self.SR)


# ============================================================ #
#  The page
# ============================================================ #
class VoiceStudioPage(QWidget):
    """Two columns: Cloned voices  |  Enrolled speakers."""

    voice_set = Signal(str, str)   # (ref_audio_path, ref_text) — pushed to config

    def __init__(self, cfg_obj, parent=None):
        super().__init__(parent)
        self.cfg = cfg_obj
        self.rec = Recorder(on_level=self._on_level)

        lay = QVBoxLayout(self); lay.setContentsMargins(20, 12, 20, 20); lay.setSpacing(12)
        title = QLabel("Voice Studio")
        title.setStyleSheet(TITLE_QSS)
        lay.addWidget(title)
        sub = QLabel("Record reference voices for OmniVoice cloning, "
                     "or enroll your voice for biometric verification.")
        sub.setStyleSheet(SUBTLE_QSS)
        lay.addWidget(sub)

        # ---- recorder strip ---- #
        rec_card = Card("Recorder")
        row = QHBoxLayout()
        self.btn_rec = QPushButton("● Record")
        self.btn_rec.setStyleSheet(danger_btn())
        self.btn_rec.clicked.connect(self._toggle_record)
        row.addWidget(self.btn_rec)
        self.meter = WaveMeter()
        row.addWidget(self.meter, 1)
        self.time_lbl = QLabel("00:00")
        self.time_lbl.setStyleSheet("font-family: monospace; font-size: 14px; color: #333;")
        row.addWidget(self.time_lbl)
        rec_card.lay.addLayout(row)

        # save buttons appear after recording
        actions = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play"); self.btn_play.setEnabled(False)
        self.btn_play.setStyleSheet(ghost_btn())
        self.btn_play.clicked.connect(self._play_buffer)
        self.btn_save_clone = QPushButton("Save as clone voice…"); self.btn_save_clone.setEnabled(False)
        self.btn_save_clone.setStyleSheet(primary_btn())
        self.btn_save_clone.clicked.connect(self._save_clone)
        self.btn_enroll = QPushButton("Enroll as speaker…"); self.btn_enroll.setEnabled(False)
        self.btn_enroll.setStyleSheet(primary_btn())
        self.btn_enroll.clicked.connect(self._enroll_speaker)
        actions.addWidget(self.btn_play); actions.addWidget(self.btn_save_clone)
        actions.addWidget(self.btn_enroll); actions.addStretch(1)
        rec_card.lay.addLayout(actions)
        lay.addWidget(rec_card)

        # ---- two columns ---- #
        cols = QHBoxLayout(); cols.setSpacing(14)
        cols.addWidget(self._build_clones(), 1)
        cols.addWidget(self._build_speakers(), 1)
        lay.addLayout(cols, 1)

        # state
        self.buffer = None       # np.ndarray of last recording
        self._t0 = 0
        self._tick = QTimer(self); self._tick.timeout.connect(self._update_timer)
        self.refresh()

    # ------------- left column: cloned voices ------------- #
    def _build_clones(self):
        c = Card("Cloned Voices  (for OmniVoice TTS)")
        self.clone_list = QListWidget()
        self.clone_list.setStyleSheet(LIST_QSS)
        self.clone_list.itemDoubleClicked.connect(self._activate_clone)
        c.lay.addWidget(self.clone_list, 1)

        btns = QHBoxLayout()
        b1 = QPushButton("Use as active voice"); b1.setStyleSheet(primary_btn())
        b1.clicked.connect(self._activate_clone)
        b2 = QPushButton("Preview"); b2.setStyleSheet(ghost_btn())
        b2.clicked.connect(self._preview_clone)
        b3 = QPushButton("Import wav…"); b3.setStyleSheet(ghost_btn())
        b3.clicked.connect(self._import_clone)
        b4 = QPushButton("Delete"); b4.setStyleSheet(ghost_btn())
        b4.clicked.connect(self._delete_clone)
        for b in (b1, b2, b3, b4): btns.addWidget(b)
        c.lay.addLayout(btns)
        return c

    # ------------- right column: enrolled speakers ------------- #
    def _build_speakers(self):
        c = Card("Enrolled Speakers  (voice biometric)")
        self.spk_list = QListWidget()
        self.spk_list.setStyleSheet(self.clone_list.styleSheet())
        c.lay.addWidget(self.spk_list, 1)

        btns = QHBoxLayout()
        bv = QPushButton("Verify (4 s)"); bv.setStyleSheet(primary_btn())
        bv.clicked.connect(self._verify)
        bi = QPushButton("Identify (4 s)"); bi.setStyleSheet(primary_btn())
        bi.clicked.connect(self._identify)
        bd = QPushButton("Delete"); bd.setStyleSheet(ghost_btn())
        bd.clicked.connect(self._delete_speaker)
        for b in (bv, bi, bd): btns.addWidget(b)
        c.lay.addLayout(btns)

        self.spk_result = QLabel(" ")
        self.spk_result.setStyleSheet(f"color: {MUTED}; font-size: 12px; padding-top: 4px;")
        self.spk_result.setWordWrap(True)
        c.lay.addWidget(self.spk_result)
        return c

    # ============================================================ #
    #  recording                                                    #
    # ============================================================ #
    def _on_level(self, level: float):
        self.meter.push(level)

    def _toggle_record(self):
        if self.rec.recording:
            self.buffer = self.rec.stop()
            self.meter.recording = False
            self.btn_rec.setText("● Record")
            self._tick.stop()
            if self.buffer is not None:
                self.btn_play.setEnabled(True)
                self.btn_save_clone.setEnabled(True)
                self.btn_enroll.setEnabled(True)
                dur = len(self.buffer) / Recorder.SR
                self.time_lbl.setText(f"{int(dur//60):02d}:{int(dur%60):02d}")
        else:
            if sd is None:
                QMessageBox.warning(self, "Missing dep", "pip install sounddevice soundfile numpy")
                return
            self.rec.start()
            self.meter.recording = True
            self.btn_rec.setText("■ Stop")
            self.btn_play.setEnabled(False)
            self.btn_save_clone.setEnabled(False)
            self.btn_enroll.setEnabled(False)
            self._t0 = time.time(); self._tick.start(100)

    def _update_timer(self):
        elapsed = time.time() - self._t0
        self.time_lbl.setText(f"{int(elapsed//60):02d}:{int(elapsed%60):02d}")

    def _play_buffer(self):
        if self.buffer is None or sd is None: return
        sd.play(self.buffer, Recorder.SR)

    # ============================================================ #
    #  clones                                                       #
    # ============================================================ #
    def _save_clone(self):
        if self.buffer is None: return
        name, ok = QInputDialog.getText(self, "Save clone voice", "Name (e.g. me, mom, aera):")
        if not ok or not name: return
        transcript, ok = QInputDialog.getMultiLineText(
            self, "Transcript", "Type the EXACT words spoken in the recording:")
        if not ok or not transcript.strip(): return
        wav_path = VOICES_DIR / f"{name}.wav"
        txt_path = VOICES_DIR / f"{name}.txt"
        self.rec.save(self.buffer, wav_path)
        txt_path.write_text(transcript.strip(), encoding="utf-8")
        self.refresh()
        QMessageBox.information(self, "Saved", f"Saved as voices/{name}.wav")

    def _import_clone(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import wav", "", "Audio (*.wav *.mp3 *.flac *.ogg)")
        if not path: return
        name, ok = QInputDialog.getText(self, "Name", "Voice name:")
        if not ok or not name: return
        transcript, ok = QInputDialog.getMultiLineText(self, "Transcript", "Exact transcript:")
        if not ok or not transcript.strip(): return
        import shutil
        dest = VOICES_DIR / f"{name}.wav"
        shutil.copy(path, dest)
        (VOICES_DIR / f"{name}.txt").write_text(transcript.strip(), encoding="utf-8")
        self.refresh()

    def _selected_clone(self) -> Optional[str]:
        item = self.clone_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _activate_clone(self, *_):
        name = self._selected_clone()
        if not name: return
        wav = str(VOICES_DIR / f"{name}.wav")
        txt_path = VOICES_DIR / f"{name}.txt"
        text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else ""
        v = self.cfg.data["voice"]
        v["engine"] = "omnivoice"
        v["ref_audio"] = wav
        v["ref_text"] = text
        self.cfg.save()
        self.voice_set.emit(wav, text)
        QMessageBox.information(self, "Activated",
            f"OmniVoice will now clone '{name}'.\nRestart for it to take effect.")

    def _preview_clone(self):
        name = self._selected_clone()
        if not name or sd is None: return
        try:
            wav, sr = sf.read(VOICES_DIR / f"{name}.wav")
            sd.play(wav, sr)
        except Exception as e:
            QMessageBox.warning(self, "Play failed", str(e))

    def _delete_clone(self):
        name = self._selected_clone()
        if not name: return
        if QMessageBox.question(self, "Confirm", f"Delete clone '{name}'?") != QMessageBox.Yes: return
        for ext in (".wav", ".txt"):
            p = VOICES_DIR / f"{name}{ext}"
            if p.exists(): p.unlink()
        self.refresh()

    # ============================================================ #
    #  enrolled speakers                                            #
    # ============================================================ #
    def _enroll_speaker(self):
        if self.buffer is None: return
        name, ok = QInputDialog.getText(self, "Enroll speaker", "Profile name (e.g. owner, alice):")
        if not ok or not name: return
        try:
            from ...audio.speaker_id import service
            svc = service(); svc._load()
            if not svc.enabled:
                QMessageBox.warning(self, "Missing model",
                    "Speaker ID backend not installed.\npip install speechbrain torch torchaudio")
                return
            import numpy as np
            emb = svc._embed_fn(self.buffer.astype(np.float32), Recorder.SR)
            svc.store.add(name, emb)
            self.refresh()
            QMessageBox.information(self, "Enrolled",
                f"'{name}' now has {svc.store.data[name]['samples']} sample(s).")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _selected_speaker(self) -> Optional[str]:
        item = self.spk_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _verify(self):
        name = self._selected_speaker()
        if not name:
            self.spk_result.setText("Select a speaker first."); return
        self.spk_result.setText(f"Verifying '{name}' — speak for 4 seconds…")
        QApplication.processEvents()
        threading.Thread(target=self._verify_thread, args=(name,), daemon=True).start()

    def _verify_thread(self, name: str):
        from ...audio.speaker_id import service
        r = service().verify(name)
        if not r.get("ok") and "reason" in r:
            self.spk_result.setText(f"❌ {r['reason']}"); return
        sim = r["similarity"]
        if r["verdict"] == "match":
            self.spk_result.setText(f"✅ MATCH — similarity {sim:.3f}  (threshold {r['threshold']:.2f})")
            self.spk_result.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: 700;")
        else:
            self.spk_result.setText(f"❌ REJECT — similarity {sim:.3f}  (threshold {r['threshold']:.2f})")
            self.spk_result.setStyleSheet(f"color: {RED}; font-size: 13px; font-weight: 700;")

    def _identify(self):
        self.spk_result.setText("Identifying speaker — speak for 4 seconds…")
        threading.Thread(target=self._identify_thread, daemon=True).start()

    def _identify_thread(self):
        from ...audio.speaker_id import service
        r = service().identify()
        if not r.get("ok"):
            self.spk_result.setText(f"❌ {r['reason']}"); return
        rows = "  |  ".join(f"{n}={s:.2f}" for n, s in r["ranking"])
        self.spk_result.setText(f"🎯 Best: {r['best']}  ({r['similarity']:.3f})\n{rows}")
        self.spk_result.setStyleSheet(f"color: {INK}; font-size: 12px;")

    def _delete_speaker(self):
        name = self._selected_speaker()
        if not name: return
        if QMessageBox.question(self, "Confirm", f"Delete speaker '{name}'?") != QMessageBox.Yes: return
        from ...audio.speaker_id import service
        service().store.remove(name)
        self.refresh()

    # ============================================================ #
    #  refresh                                                      #
    # ============================================================ #
    def refresh(self):
        # clones
        self.clone_list.clear()
        for wav in sorted(VOICES_DIR.glob("*.wav")):
            name = wav.stem
            if name == "ecapa": continue  # speechbrain cache dir
            txt = VOICES_DIR / f"{name}.txt"
            preview = ""
            if txt.exists():
                preview = txt.read_text(encoding="utf-8")[:60]
                if len(preview) == 60: preview += "…"
            try: size_kb = wav.stat().st_size // 1024
            except Exception: size_kb = 0
            label = f"🎤  {name}    ({size_kb} KB)\n      {preview}"
            it = QListWidgetItem(label); it.setData(Qt.UserRole, name)
            self.clone_list.addItem(it)
        if self.clone_list.count() == 0:
            self.clone_list.addItem("(no cloned voices yet — record one above)")

        # speakers
        self.spk_list.clear()
        try:
            from ...audio.speaker_id import service
            for n in service().store.names():
                e = service().store.data[n]
                lbl = f"👤  {n}    ({e['samples']} sample(s))\n      enrolled {e.get('enrolled','?')[:10]}"
                it = QListWidgetItem(lbl); it.setData(Qt.UserRole, n)
                self.spk_list.addItem(it)
        except Exception:
            pass
        if self.spk_list.count() == 0:
            self.spk_list.addItem("(no speakers enrolled — record + click Enroll)")



"""
Piper TTS backend for the Voice Assistant.

Piper is a fast, neural, fully-offline TTS engine. It sounds natural —
nothing like the robotic pyttsx3 / SAPI / espeak voices.

Install:
    pip install piper-tts sounddevice numpy
    python -m piper.download_voices en_US-lessac-medium

Then in config.json set:
    "tts": { "engine": "piper", "model": "en_US-lessac-medium", ... }

Voice models are downloaded once and cached in ~/.local/share/piper/voices
(or current directory). Browse all voices:
    https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md
"""

import queue
import subprocess
import sys
import threading
from pathlib import Path

from ..paths import VOICES_DIR

try:
    from piper import PiperVoice, SynthesisConfig
except Exception:
    PiperVoice = None
    SynthesisConfig = None

try:
    import sounddevice as sd
    import numpy as np
except Exception:
    sd = None
    np = None


# Standard voice download locations (Piper searches CWD + these by default)
_VOICE_DIRS = [
    Path.cwd(),
    Path.home() / ".local" / "share" / "piper" / "voices",
    Path.home() / "piper-voices",
    Path(__file__).parent / "voices",
]


def _find_voice(name: str) -> Path | None:
    """Locate <name>.onnx in any known voice directory."""
    if name.endswith(".onnx") and Path(name).exists():
        return Path(name)
    fname = name if name.endswith(".onnx") else f"{name}.onnx"
    for d in _VOICE_DIRS:
        p = d / fname
        if p.exists():
            return p
    return None


def _try_download(name: str) -> Path | None:
    """Call `python -m piper.download_voices <name>` to fetch a voice."""
    target_dir = VOICES_DIR
    target_dir.mkdir(exist_ok=True)
    print(f"📥 Downloading Piper voice '{name}' …")
    try:
        subprocess.run(
            [sys.executable, "-m", "piper.download_voices", name],
            cwd=target_dir, check=True,
        )
    except Exception as e:
        print(f"   download failed: {e}")
        return None
    return _find_voice(name)


class PiperSpeaker:
    """
    Drop-in replacement for the pyttsx3 Speaker class.
    Same interface:  .say(text), .shutdown(), .enabled
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = False
        self.q: queue.Queue[str | None] = queue.Queue()

        if PiperVoice is None:
            print("[warn] piper-tts not installed. `pip install piper-tts sounddevice numpy`")
            return
        if sd is None:
            print("[warn] sounddevice/numpy not installed — required for Piper audio playback.")
            return

        model_name = cfg.get("model", "en_US-lessac-medium")
        path = _find_voice(model_name) or _try_download(model_name)
        if path is None:
            print(f"[warn] Could not locate or download Piper voice '{model_name}'.")
            return

        use_cuda = bool(cfg.get("use_cuda", False))
        try:
            self.voice = PiperVoice.load(str(path), use_cuda=use_cuda)
        except Exception as e:
            print(f"[warn] Piper failed to load model: {e}")
            return

        # build synthesis config (length_scale 1.0 = normal, lower = faster)
        rate_wpm = cfg.get("rate", 180)              # words per minute target
        length_scale = max(0.5, min(2.0, 180.0 / max(rate_wpm, 60)))
        self.syn_cfg = SynthesisConfig(
            volume=float(cfg.get("volume", 1.0)),
            length_scale=length_scale,
            noise_scale=float(cfg.get("noise_scale", 0.667)),
            noise_w_scale=float(cfg.get("noise_w_scale", 0.8)),
            normalize_audio=True,
        )

        self.enabled = True
        self._stop_current = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        print(f"🔊 Piper TTS ready  (voice: {path.name})")

    # --------------------------------------------------------- #
    def _worker(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break
            try:
                self._speak(item)
            except Exception as e:
                print(f"[piper warn] {e}")

    def _speak(self, text: str) -> None:
        """Synthesize and play, streaming chunk-by-chunk for low latency."""
        self._stop_current.clear()
        stream = None
        try:
            for chunk in self.voice.synthesize(text, syn_config=self.syn_cfg):
                if self._stop_current.is_set():
                    break
                pcm = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
                if stream is None:
                    stream = sd.OutputStream(
                        samplerate=chunk.sample_rate,
                        channels=chunk.sample_channels,
                        dtype="int16",
                    )
                    stream.start()
                stream.write(pcm)
        finally:
            if stream is not None:
                stream.stop()
                stream.close()

    # --------------------------------------------------------- #
    # Public API (matches pyttsx3 Speaker)
    # --------------------------------------------------------- #
    def say(self, text: str) -> None:
        text = (text or "").strip()
        if text and self.enabled:
            self.q.put(text)

    def stop(self) -> None:
        """Interrupt currently-speaking sentence and clear queue (barge-in)."""
        self._stop_current.set()
        try:
            while True:
                self.q.get_nowait()
        except queue.Empty:
            pass

    def shutdown(self) -> None:
        if self.enabled:
            self.stop()
            self.q.put(None)

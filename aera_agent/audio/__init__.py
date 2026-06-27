"""
Audio subsystem — TTS, STT, wake-word, and speaker biometric.

Public factories used by both the CLI and the GUI worker:

    build_speaker(cfg["voice"])   → object with .say() .stop() .shutdown()
    build_listener(cfg["speech"]) → object with .listen() → str | None

Both auto-fall-back through the engine chain if the preferred one fails.
"""

import queue
import threading

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


# ─────────────────────────────────────────────────────────── #
#  Optional backends (lazy + safe to fail at import time)
# ─────────────────────────────────────────────────────────── #
try:
    from .tts_piper import PiperSpeaker
except Exception:
    PiperSpeaker = None

try:
    from .tts_omnivoice import OmniVoiceSpeaker
except Exception:
    OmniVoiceSpeaker = None

try:
    from .stt_sensevoice import SenseVoiceListener
except Exception:
    SenseVoiceListener = None


# ─────────────────────────────────────────────────────────── #
#  pyttsx3 — the always-available offline fallback
# ─────────────────────────────────────────────────────────── #
class Pyttsx3Speaker:
    """Cross-platform offline TTS using pyttsx3 (SAPI/NSSpeechSynthesizer/espeak)."""

    def __init__(self, cfg: dict):
        self.enabled = False
        self.engine = None
        self.q: queue.Queue = queue.Queue()
        if pyttsx3 is None:
            print("[warn] pyttsx3 not installed – TTS disabled.")
            return
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", cfg.get("rate", 180))
            self.engine.setProperty("volume", cfg.get("volume", 1.0))
            voices = self.engine.getProperty("voices") or []
            idx = cfg.get("voice_index", 0)
            if voices and 0 <= idx < len(voices):
                self.engine.setProperty("voice", voices[idx].id)
        except Exception as e:
            # Headless server, no audio device, missing espeak, etc.
            # We log once and run silently — the rest of AERA still works.
            print(f"[warn] pyttsx3 init failed ({e}) – TTS disabled.")
            return
        self.enabled = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break
            try:
                self.engine.say(item)
                self.engine.runAndWait()
            except RuntimeError:
                pass

    def say(self, text: str) -> None:
        text = text.strip()
        if text and self.enabled:
            self.q.put(text)

    def stop(self) -> None:
        try: self.engine.stop()
        except Exception: pass
        try:
            while True: self.q.get_nowait()
        except queue.Empty: pass

    def shutdown(self) -> None:
        if self.enabled:
            self.q.put(None)


# ─────────────────────────────────────────────────────────── #
#  Google STT (SpeechRecognition wrapper)
# ─────────────────────────────────────────────────────────── #
class GoogleListener:
    """Default STT: SpeechRecognition library with Google Web Speech API (free)."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = sr is not None
        if not self.enabled:
            print("[warn] SpeechRecognition not installed – text mode only.")
            return
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = cfg.get("energy_threshold", 300)
        self.recognizer.pause_threshold = cfg.get("pause_threshold", 0.8)
        self.recognizer.dynamic_energy_threshold = True
        try:
            self.mic = sr.Microphone()
            with self.mic as src:
                print("Calibrating mic for ambient noise… (1s)")
                self.recognizer.adjust_for_ambient_noise(src, duration=1.0)
        except Exception as e:
            print(f"[warn] Microphone unavailable ({e}) – text mode only.")
            self.enabled = False

    def listen(self) -> str | None:
        if not self.enabled:
            return None
        try:
            with self.mic as src:
                print("🎤 Listening…", end="", flush=True)
                audio = self.recognizer.listen(
                    src,
                    timeout=self.cfg.get("timeout", 5),
                    phrase_time_limit=self.cfg.get("phrase_time_limit", 15),
                )
            print(" processing…", end="", flush=True)
            text = self.recognizer.recognize_google(
                audio, language=self.cfg.get("language", "en-US"))
            print(f"\r🗣  You: {text}{' ' * 20}")
            return text
        except sr.WaitTimeoutError:
            print("\r(no speech detected)            "); return None
        except sr.UnknownValueError:
            print("\r(couldn't understand audio)     "); return None
        except sr.RequestError as e:
            print(f"\r[STT error] {e}"); return None


# Re-export with a friendlier name (CLI/GUI used to import `Listener`)
Listener = GoogleListener


# ─────────────────────────────────────────────────────────── #
#  Factories
# ─────────────────────────────────────────────────────────── #
_TTS_ENGINES = {
    # name        class-getter                    fallback chain
    "omnivoice": (lambda: OmniVoiceSpeaker, ("piper", "pyttsx3")),
    "piper":     (lambda: PiperSpeaker,     ("pyttsx3",)),
    "pyttsx3":   (lambda: Pyttsx3Speaker,   ()),
}


def build_speaker(cfg: dict):
    """Pick TTS engine from cfg.engine, gracefully falling back on init failure."""
    requested = cfg.get("engine", "pyttsx3").lower()
    if requested not in _TTS_ENGINES:
        print(f"[warn] unknown TTS engine {requested!r} — using pyttsx3")
        requested = "pyttsx3"

    chain = [requested] + list(_TTS_ENGINES[requested][1])
    for name in chain:
        cls = _TTS_ENGINES[name][0]()
        if cls is None:
            print(f"[warn] TTS backend {name!r} unavailable — trying next.")
            continue
        sp = cls(cfg)
        if getattr(sp, "enabled", False):
            return sp
        print(f"[warn] TTS backend {name!r} init failed — trying next.")
    return Pyttsx3Speaker(cfg)


def build_listener(cfg: dict):
    """Pick STT engine; auto-fall back to Google SpeechRecognition."""
    engine = cfg.get("engine", "google").lower()
    if engine == "sensevoice":
        if SenseVoiceListener is None:
            print("[warn] SenseVoice not installed — falling back to Google STT.")
        else:
            li = SenseVoiceListener(cfg)
            if li.enabled:
                return li
            print("[warn] SenseVoice init failed — falling back to Google STT.")
    return GoogleListener(cfg)


__all__ = [
    "build_speaker", "build_listener",
    "Pyttsx3Speaker", "GoogleListener", "Listener",
    "PiperSpeaker", "OmniVoiceSpeaker", "SenseVoiceListener",
]

"""
Wake-word detector for AERA Agent.

Two backends, tried in order:
  1. pvporcupine (Picovoice) — high accuracy, low CPU, free for personal use.
     Needs PV_ACCESS_KEY env var or `access_key` in config.
  2. SpeechRecognition fallback — captures short audio windows and runs
     Google STT, then string-matches the phrase. Free, no key, but heavier.

API:
    wake = WakeWordDetector(cfg)
    wake.on_detected = lambda: print("triggered!")
    wake.start()    # background thread
    wake.stop()
"""

import os
import threading
import time
from typing import Callable


class WakeWordDetector:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = cfg.get("enabled", False)
        self.phrase = cfg.get("phrase", "hey aera").lower().strip()
        self.access_key = cfg.get("access_key", "") or os.environ.get("PV_ACCESS_KEY", "")
        self.on_detected: Callable[[], None] | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._backend = None

    # ---------- public ----------
    def start(self) -> bool:
        if not self.enabled or self._thread is not None:
            return False
        backend = self._init_porcupine() or self._init_speechrec()
        if not backend:
            print("[wake] no backend available — wake word disabled.")
            return False
        self._backend = backend
        self._stop.clear()
        self._thread = threading.Thread(target=backend, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        self._thread = None

    # ---------- backends ----------
    def _init_porcupine(self):
        try:
            import pvporcupine, pyaudio, struct
        except ImportError:
            return None
        if not self.access_key:
            return None
        try:
            # Porcupine ships a fixed set of built-in keywords. We try to
            # match the user's phrase to one; if no match, default to a
            # neutral built-in. "AERA" isn't a Porcupine keyword, so users
            # who want a true "Hey AERA" wake-word should fall back to the
            # speech-recognition backend (see _init_speechrec below).
            builtin = pvporcupine.KEYWORDS
            kw = self.phrase.replace("hey ", "").replace(" ", "")
            if kw not in builtin:
                kw = "computer"  # neutral fallback
            porc = pvporcupine.create(access_key=self.access_key, keywords=[kw])
        except Exception as e:
            print(f"[wake] porcupine init failed: {e}")
            return None

        def loop():
            pa = pyaudio.PyAudio()
            stream = pa.open(rate=porc.sample_rate, channels=1, format=pyaudio.paInt16,
                             input=True, frames_per_buffer=porc.frame_length)
            print(f"[wake] porcupine listening for '{kw}'…")
            try:
                while not self._stop.is_set():
                    pcm = stream.read(porc.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * porc.frame_length, pcm)
                    if porc.process(pcm) >= 0:
                        print("[wake] triggered (porcupine)")
                        if self.on_detected: self.on_detected()
                        time.sleep(2.0)   # debounce
            finally:
                stream.close(); pa.terminate(); porc.delete()
        return loop

    def _init_speechrec(self):
        try:
            import speech_recognition as sr
        except ImportError:
            return None
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 400
        recognizer.dynamic_energy_threshold = True
        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"[wake] no microphone: {e}")
            return None

        phrase = self.phrase

        def loop():
            print(f"[wake] speech-recognition listening for '{phrase}'…")
            with mic as src:
                recognizer.adjust_for_ambient_noise(src, duration=0.8)
            while not self._stop.is_set():
                try:
                    with mic as src:
                        audio = recognizer.listen(src, timeout=3, phrase_time_limit=3)
                    try:
                        heard = recognizer.recognize_google(audio).lower()
                    except Exception:
                        continue
                    if phrase in heard or _fuzzy(phrase, heard):
                        print(f"[wake] triggered (heard: '{heard}')")
                        if self.on_detected: self.on_detected()
                        time.sleep(3.0)  # debounce — let main listen cycle take over
                except Exception:
                    time.sleep(0.2)
        return loop


def _fuzzy(target: str, heard: str) -> bool:
    """Allow 1-edit fuzz: 'hey era' should trigger 'hey aera'."""
    if len(target) > 4 and target[:4] in heard: return True
    parts = target.split()
    return all(p[:3] in heard for p in parts if len(p) >= 3)

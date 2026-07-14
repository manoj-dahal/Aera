"""
SenseVoice STT backend for AERA Agent.

Wraps Alibaba's SenseVoiceSmall (via funasr.AutoModel) to look like the
existing `Listener` class. SenseVoice is fully offline once downloaded,
supports zh / en / ja / ko / yue (Cantonese) auto-detection, and is much
more accurate than free Google Web Speech.

Install:
    pip install funasr soundfile sounddevice numpy webrtcvad
    # first run will auto-download ~1GB model from ModelScope

Hardware:
    CUDA GPU       → fast (~1× realtime on a 3060)
    Apple Silicon  → mps, works but slow
    CPU only       → works but 3-5× realtime; use language="auto" off,
                     pick smaller chunks, or fall back to whisper.cpp.

Config (config.json → speech):
    {
      "engine": "sensevoice",
      "language": "auto",        // or "en", "zh", "ja", "ko", "yue"
      "device":   "auto",        // "auto" | "cuda" | "cpu" | "mps"
      "vad_silence_ms": 700,     // stop after this much silence
      "max_record_s":   15
    }
"""

import os
import re
import tempfile

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
except Exception:
    np = sd = sf = None

try:
    import webrtcvad
except Exception:
    webrtcvad = None

# Stripped at module init for speed
_TAG_RE = re.compile(r"<\|[^|]*\|>")


def _pick_device(want: str) -> str:
    if want and want != "auto":
        return want
    try:
        import torch
        if torch.cuda.is_available(): return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


class SenseVoiceListener:
    """
    Drop-in replacement for assistant.Listener.

    Public API matches: `enabled`, `listen() -> str | None`.
    """

    SR = 16000

    def __init__(self, cfg: dict):
        self.cfg  = cfg
        self.lang = cfg.get("language", "auto")
        self.silence_ms   = int(cfg.get("vad_silence_ms", 700))
        self.max_record_s = float(cfg.get("max_record_s", 15))
        self.device       = _pick_device(cfg.get("device", "auto"))
        self.enabled      = False
        self.model        = None

        if np is None or sd is None:
            print("[sensevoice] missing deps: pip install sounddevice soundfile numpy")
            return
        try:
            from funasr import AutoModel
        except ImportError:
            print("[sensevoice] funasr not installed: pip install funasr")
            return

        print(f"[sensevoice] loading SenseVoiceSmall on {self.device} … (first time ≈ 1GB download)")
        try:
            # Suppress noisy logs
            import logging
            prev = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
            try:
                self.model = AutoModel(
                    model="iic/SenseVoiceSmall",
                    device=self.device,
                    disable_update=True,
                    disable_pbar=True,
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": int(self.max_record_s * 1000)},
                )
            finally:
                logging.disable(prev)
            self.enabled = True
            print(f"[sensevoice] ready ({self.device})")
        except Exception as e:
            print(f"[sensevoice] load failed: {e}")

        # voice-activity detector for "stop talking" detection
        self._vad = None
        if webrtcvad is not None:
            self._vad = webrtcvad.Vad(2)        # aggressiveness 0-3

    # ----------------------------------------------------------- #
    def listen(self) -> str | None:
        """Block until speech is heard, return the transcribed string."""
        if not self.enabled:
            return None
        try:
            audio = self._record_until_silence()
            if audio is None or len(audio) < self.SR // 2:
                return None
            return self._transcribe(audio)
        except Exception as e:
            print(f"[sensevoice] error: {e}")
            return None

    # ----------------------------------------------------------- #
    def _record_until_silence(self) -> np.ndarray | None:
        """Mic capture: keep recording until VAD says we've stopped talking."""
        print("🎤 Listening…", end="", flush=True)
        frames = []
        frame_ms = 30
        frame_len = int(self.SR * frame_ms / 1000)
        silence_frames_needed = max(1, self.silence_ms // frame_ms)
        max_frames = int(self.max_record_s * 1000 / frame_ms)

        silent_run = 0
        spoke_once = False
        with sd.InputStream(samplerate=self.SR, channels=1, dtype="int16",
                            blocksize=frame_len) as stream:
            for _ in range(max_frames):
                data, _ = stream.read(frame_len)
                pcm = data[:, 0]
                frames.append(pcm.copy())

                if self._vad is not None:
                    is_speech = self._vad.is_speech(pcm.tobytes(), self.SR)
                else:
                    is_speech = float(np.abs(pcm).mean()) > 300

                if is_speech:
                    spoke_once = True
                    silent_run = 0
                else:
                    silent_run += 1
                    if spoke_once and silent_run >= silence_frames_needed:
                        break

        print(" processing…", end="", flush=True)
        if not spoke_once:
            print("\r(no speech detected)            ")
            return None
        return np.concatenate(frames).astype(np.float32) / 32768.0

    # ----------------------------------------------------------- #
    def _transcribe(self, audio) -> str:
        # SenseVoice's funasr API accepts a file path or numpy array depending
        # on version. Temp wav is the universal path.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, self.SR)
            path = tmp.name
        try:
            res = self.model.generate(
                input=path, language=self.lang, use_itn=True,
                batch_size=1, disable_pbar=True,
            )
        finally:
            try: os.remove(path)
            except OSError: pass

        if not res:
            return ""
        # SenseVoice prepends meta-tags like <|en|><|NEUTRAL|><|Speech|>
        text = _TAG_RE.sub("", res[0].get("text", "")).strip()
        print(f"\r🗣  You: {text}{' ' * 20}")
        return text

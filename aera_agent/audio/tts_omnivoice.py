"""
OmniVoice TTS backend for AERA Agent.

Wraps Xiaomi's OmniVoice multilingual TTS model — supports voice cloning
(give it 5-15s of any voice + transcript, it speaks anything in that voice)
and voice design (describe a voice in text, it generates one).

Install:
    pip install transformers torch torchaudio
    pip install sounddevice numpy

First run downloads ~3-5 GB from HuggingFace (model + audio tokenizer).

Hardware (recommended in order):
    CUDA 12 GB+   →  realtime, recommended
    CUDA 8 GB     →  works, slightly slower
    Apple Silicon →  fp32 only, ~3× realtime
    CPU only      →  works but slow (~10× realtime). Use Piper instead.

Config (config.json → voice):
    {
      "engine":         "omnivoice",
      "model_id":       "k2-fsa/OmniVoice-v0",
      "device":         "auto",          // auto | cuda | cpu | mps
      "language":       "en",            // en | zh | ja | ko | yue | …
      "ref_audio":      "voices/me.wav", // optional voice clone reference
      "ref_text":       "Hello, this is a sample of my voice.",
      "voice_design":   "",              // OR a text description
      "num_step":       32,              // diffusion steps
      "guidance_scale": 2.0
    }
"""

"""OmniVoice TTS adapter — see module docstring above for setup."""

import queue
import threading
import time
from pathlib import Path

# Lightweight imports first — heavy deps loaded only inside the constructor
# so importing this module is cheap even when the user picks a different TTS.
try:
    import numpy as np
except ImportError:
    np = None
try:
    import sounddevice as sd
except ImportError:
    sd = None


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


class OmniVoiceSpeaker:
    """
    Drop-in replacement for the pyttsx3/Piper Speaker class.
    API:  .say(text), .stop(), .shutdown(), .enabled
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = False
        self.q: queue.Queue = queue.Queue()
        self._stop_current = threading.Event()

        if np is None or sd is None:
            print("[omnivoice] missing deps: pip install sounddevice numpy")
            return
        try:
            import torch  # heavy — only needed here
        except ImportError:
            print("[omnivoice] missing deps: pip install torch torchaudio")
            return

        self.device = _pick_device(cfg.get("device", "auto"))
        model_id = cfg.get("model_id", "k2-fsa/OmniVoice-v0")

        print(f"[omnivoice] loading {model_id} on {self.device} … (first run = large download)")
        try:
            from omnivoice.omnivoice_model import OmniVoice
            self.model = OmniVoice.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device,
            )
            self.model.eval()
        except Exception as e:
            print(f"[omnivoice] load failed: {e}")
            return

        # Build a reusable voice-clone prompt once if ref provided
        self.voice_prompt = None
        ref_audio = cfg.get("ref_audio", "")
        ref_text  = cfg.get("ref_text", "")
        if ref_audio and Path(ref_audio).exists() and ref_text:
            try:
                self.voice_prompt = self.model.create_voice_clone_prompt(
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                )
                print(f"[omnivoice] voice clone prompt cached from {ref_audio}")
            except Exception as e:
                print(f"[omnivoice] voice clone build failed: {e}")

        # generation params
        self.lang = cfg.get("language", "en")
        self.voice_design = cfg.get("voice_design", "")
        self.gen_kwargs = {
            "num_step":       int(cfg.get("num_step", 32)),
            "guidance_scale": float(cfg.get("guidance_scale", 2.0)),
        }

        self.enabled = True
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        print(f"[omnivoice] ready ({self.device})")

    # ----------------------------------------------------------- #
    def _worker(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                break
            try:
                self._speak(item)
            except Exception as e:
                print(f"[omnivoice] synth error: {e}")

    def _speak(self, text: str) -> None:
        """Synthesize and play. Uses torch.inference_mode at call time to avoid
        depending on torch at import time."""
        import torch
        with torch.inference_mode():
            self._do_speak(text)

    def _do_speak(self, text: str) -> None:
        self._stop_current.clear()

        kwargs = dict(self.gen_kwargs)
        if self.voice_prompt is not None:
            kwargs["voice_clone_prompt"] = self.voice_prompt
        elif self.voice_design:
            kwargs["instruct"] = self.voice_design
        # else: auto voice — model chooses

        out = self.model.generate(
            text=text,
            language=self.lang,
            **kwargs,
        )
        # OmniVoice returns waveform tensor (1, T) or (T,) + sample_rate
        wav, sr = self._extract_wav(out)
        if wav is None or self._stop_current.is_set():
            return
        sd.play(wav, sr)
        # poll for barge-in
        while sd.get_stream().active:
            if self._stop_current.is_set():
                sd.stop()
                break
            time.sleep(0.05)

    def _extract_wav(self, out):
        """OmniVoice returns shapes vary — normalize to numpy float32."""
        sr = getattr(self.model, "sampling_rate", 24000)
        if isinstance(out, tuple):
            wav, sr = out
        elif hasattr(out, "audio"):
            wav = out.audio
        else:
            wav = out
        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().float().numpy()
        wav = np.asarray(wav).squeeze()
        if wav.ndim > 1:
            wav = wav[0]
        # ensure -1..1 range
        peak = float(np.abs(wav).max() or 1.0)
        if peak > 1.0:
            wav = wav / peak
        return wav.astype(np.float32), sr

    # ----------------------------------------------------------- #
    # Public API (matches Speaker)
    # ----------------------------------------------------------- #
    def say(self, text: str) -> None:
        text = (text or "").strip()
        if text and self.enabled:
            self.q.put(text)

    def stop(self) -> None:
        self._stop_current.set()
        try:
            while True: self.q.get_nowait()
        except queue.Empty:
            pass
        try: sd.stop()
        except Exception: pass

    def shutdown(self) -> None:
        if self.enabled:
            self.stop()
            self.q.put(None)

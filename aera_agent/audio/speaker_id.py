"""
Speaker identification & verification for AERA Agent.

Uses ECAPA-TDNN embeddings to:
  • Enroll one or more speakers (record 3-10 s, save embedding)
  • Verify "is the speaker who just spoke really <name>?" (cosine similarity)
  • Identify "which enrolled speaker is this?" (1-vs-all)

Tries backends in order:
  1. SpeechBrain (`speechbrain/spkrec-ecapa-voxceleb`) — easiest, pip-installable.
  2. pyannote/embedding (HF) — fallback.
  3. None → graceful disable.

Persisted to: voice_assistant/speakers.json
  {
    "owner": {"embedding": [..256..], "samples": 3, "enrolled": "2026-06-27"},
    "alice": {...}
  }

Threshold (cosine):
    > 0.70   = strong match (same speaker)
    > 0.55   = probable match
    < 0.55   = different speaker
"""

import datetime as dt
import json
import os
import tempfile
import threading
from typing import Optional

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
except Exception:
    np = sd = sf = None

from ..paths import SPEAKERS_FILE as SPK_FILE, VOICES_DIR


# ============================================================ #
#  Backend loaders
# ============================================================ #
def _load_speechbrain():
    try:
        from speechbrain.inference.speaker import EncoderClassifier
        import torch
    except ImportError:
        return None
    try:
        model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            savedir=str(VOICES_DIR / "ecapa"),
        )
        def embed(wav_np: "np.ndarray", sr: int) -> "np.ndarray":
            import torch
            t = torch.from_numpy(wav_np).float().unsqueeze(0)
            if sr != 16000:
                import torchaudio
                t = torchaudio.functional.resample(t, sr, 16000)
            with torch.no_grad():
                v = model.encode_batch(t).squeeze().cpu().numpy()
            return v / (np.linalg.norm(v) + 1e-9)
        return embed
    except Exception as e:
        print(f"[speaker_id] speechbrain load failed: {e}")
        return None


def _load_pyannote():
    try:
        from pyannote.audio import Model
        from pyannote.audio import Inference
        import torch
    except ImportError:
        return None
    try:
        tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        model = Model.from_pretrained("pyannote/embedding", use_auth_token=tok)
        inference = Inference(model, window="whole")
        def embed(wav_np, sr):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, wav_np, sr); p = f.name
            try:
                v = inference(p)
                return v / (np.linalg.norm(v) + 1e-9)
            finally:
                os.remove(p)
        return embed
    except Exception as e:
        print(f"[speaker_id] pyannote load failed: {e}")
        return None


# ============================================================ #
#  Store
# ============================================================ #
class SpeakerStore:
    def __init__(self):
        self.data: dict = {}
        if SPK_FILE.exists():
            try: self.data = json.loads(SPK_FILE.read_text())
            except Exception: self.data = {}

    def save(self):
        SPK_FILE.write_text(json.dumps(self.data, indent=2))

    def add(self, name: str, embedding: "np.ndarray"):
        e = self.data.get(name, {"embeddings": [], "samples": 0})
        e["embeddings"].append(embedding.tolist())
        e["samples"] = len(e["embeddings"])
        e["enrolled"] = dt.datetime.now().isoformat(timespec="seconds")
        self.data[name] = e
        self.save()

    def remove(self, name: str) -> bool:
        if name in self.data:
            del self.data[name]; self.save(); return True
        return False

    def names(self) -> list[str]:
        return list(self.data.keys())

    def mean_embedding(self, name: str) -> Optional["np.ndarray"]:
        e = self.data.get(name)
        if not e or not e.get("embeddings"): return None
        arr = np.array(e["embeddings"])
        m = arr.mean(axis=0)
        return m / (np.linalg.norm(m) + 1e-9)


# ============================================================ #
#  Main service
# ============================================================ #
class SpeakerID:
    SR = 16000

    def __init__(self):
        self.store = SpeakerStore()
        self._embed_fn = None
        self.enabled = False
        self._lock = threading.Lock()

        if np is None or sd is None or sf is None:
            print("[speaker_id] missing audio deps: pip install sounddevice soundfile numpy")
            return

    def _load(self):
        """Lazy-load the heavy embedding model on first use."""
        if self._embed_fn is not None or self.enabled: return
        for loader, label in [(_load_speechbrain, "SpeechBrain ECAPA-TDNN"),
                              (_load_pyannote,   "pyannote embedding")]:
            fn = loader()
            if fn:
                self._embed_fn = fn
                self.enabled = True
                print(f"[speaker_id] using {label}")
                return
        print("[speaker_id] no backend available. "
              "Install:  pip install speechbrain torch torchaudio")

    # -------------------- core operations -------------------- #
    def record(self, seconds: float = 5.0) -> "np.ndarray | None":
        """Capture a fixed-length sample from the mic."""
        if sd is None: return None
        print(f"🎤 Recording {seconds:.0f}s …", flush=True)
        try:
            audio = sd.rec(int(seconds * self.SR), samplerate=self.SR,
                           channels=1, dtype="float32")
            sd.wait()
            return audio.squeeze()
        except Exception as e:
            print(f"[speaker_id] mic error: {e}")
            return None

    def enroll(self, name: str, seconds: float = 5.0) -> str:
        """Record a sample and add it to a speaker profile."""
        self._load()
        if not self.enabled: return "speaker model not available"
        with self._lock:
            wav = self.record(seconds)
            if wav is None: return "recording failed"
            emb = self._embed_fn(wav, self.SR)
            self.store.add(name, emb)
            return f"enrolled '{name}' (now has {self.store.data[name]['samples']} sample(s))"

    def enroll_from_file(self, name: str, path: str) -> str:
        self._load()
        if not self.enabled: return "speaker model not available"
        try:
            wav, sr = sf.read(path)
            if wav.ndim > 1: wav = wav.mean(axis=1)
            wav = wav.astype("float32")
            emb = self._embed_fn(wav, sr)
            self.store.add(name, emb)
            return f"enrolled '{name}' from file ({self.store.data[name]['samples']} sample(s))"
        except Exception as e:
            return f"failed to enroll from file: {e}"

    def verify(self, name: str, seconds: float = 4.0, threshold: float = 0.55) -> dict:
        """Record and check if it's the named speaker."""
        self._load()
        if not self.enabled: return {"ok": False, "reason": "no backend"}
        ref = self.store.mean_embedding(name)
        if ref is None: return {"ok": False, "reason": f"'{name}' not enrolled"}
        wav = self.record(seconds)
        if wav is None: return {"ok": False, "reason": "recording failed"}
        v = self._embed_fn(wav, self.SR)
        sim = float(np.dot(ref, v))
        return {"ok": sim >= threshold, "similarity": sim, "threshold": threshold,
                "name": name, "verdict": ("match" if sim >= threshold else "reject")}

    def identify(self, seconds: float = 4.0, top_k: int = 3) -> dict:
        """Record and identify which enrolled speaker it most resembles."""
        self._load()
        if not self.enabled: return {"ok": False, "reason": "no backend"}
        names = self.store.names()
        if not names: return {"ok": False, "reason": "no speakers enrolled"}
        wav = self.record(seconds)
        if wav is None: return {"ok": False, "reason": "recording failed"}
        v = self._embed_fn(wav, self.SR)
        scores = []
        for n in names:
            ref = self.store.mean_embedding(n)
            scores.append((n, float(np.dot(ref, v))))
        scores.sort(key=lambda x: x[1], reverse=True)
        return {"ok": True, "best": scores[0][0],
                "similarity": scores[0][1],
                "ranking": scores[:top_k]}

    def compare_files(self, path_a: str, path_b: str) -> float:
        """Cosine similarity between two wav files — useful for TTS eval."""
        self._load()
        if not self.enabled: return -1.0
        def emb(p):
            w, sr = sf.read(p)
            if w.ndim > 1: w = w.mean(axis=1)
            return self._embed_fn(w.astype("float32"), sr)
        a, b = emb(path_a), emb(path_b)
        return float(np.dot(a, b))


# ============================================================ #
#  Singleton + tool helpers (imported by tools.py)
# ============================================================ #
_SVC: SpeakerID | None = None

def service() -> SpeakerID:
    global _SVC
    if _SVC is None: _SVC = SpeakerID()
    return _SVC

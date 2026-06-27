"""LLM-callable wrappers around voice biometric (speaker verification)."""

from . import tool
from ..audio.speaker_id import service as _spk


@tool(
    description="Enroll a speaker's voice by recording 5 seconds from the microphone. "
                "Use when the user says 'enroll my voice as <name>' or 'remember my voice'.",
    parameters={
        "type": "object",
        "properties": {
            "name":    {"type": "string", "description": "Profile name, e.g. 'owner'"},
            "seconds": {"type": "number", "default": 5},
        },
        "required": ["name"],
    },
    confirm=True,
)
def enroll_voice(name: str, seconds: float = 5.0) -> str:
    return _spk().enroll(name, seconds)


@tool(
    description="Verify the live speaker is the named enrolled person.",
    parameters={
        "type": "object",
        "properties": {
            "name":      {"type": "string", "default": "owner"},
            "seconds":   {"type": "number", "default": 4},
            "threshold": {"type": "number", "default": 0.55},
        },
    },
)
def verify_voice(name: str = "owner", seconds: float = 4.0, threshold: float = 0.55) -> str:
    r = _spk().verify(name, seconds, threshold)
    if not r.get("ok") and "reason" in r:
        return f"verification failed: {r['reason']}"
    sim = r["similarity"]
    return f"{r['verdict'].upper()} — similarity {sim:.3f} (threshold {threshold:.2f})"


@tool(
    description="Identify which enrolled speaker is talking right now.",
    parameters={"type": "object",
                "properties": {"seconds": {"type": "number", "default": 4}}},
)
def identify_speaker(seconds: float = 4.0) -> str:
    r = _spk().identify(seconds)
    if not r.get("ok"):
        return r.get("reason", "unknown error")
    rows = "\n".join(f"  {n:<12s}  similarity {s:.3f}" for n, s in r["ranking"])
    return f"Best match: {r['best']} (sim {r['similarity']:.3f})\n{rows}"


@tool(
    description="List all enrolled speaker profiles.",
    parameters={"type": "object", "properties": {}},
)
def list_speakers() -> str:
    svc = _spk()
    names = svc.store.names()
    if not names:
        return "(no speakers enrolled)"
    out = []
    for n in names:
        e = svc.store.data[n]
        out.append(f"• {n}  — {e['samples']} sample(s), enrolled {e.get('enrolled','?')[:10]}")
    return "\n".join(out)


@tool(
    description="Remove an enrolled speaker profile.",
    parameters={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
    confirm=True,
)
def delete_speaker(name: str) -> str:
    return "removed" if _spk().store.remove(name) else f"no speaker '{name}'"


@tool(
    description="Compare two audio files for speaker similarity (0..1, higher = closer). "
                "Useful for verifying a cloned TTS voice matches the reference.",
    parameters={
        "type": "object",
        "properties": {
            "file_a": {"type": "string"},
            "file_b": {"type": "string"},
        },
        "required": ["file_a", "file_b"],
    },
)
def voice_similarity(file_a: str, file_b: str) -> str:
    sim = _spk().compare_files(file_a, file_b)
    if sim < 0:
        return "Speaker model not available."
    verdict = ("very high" if sim > 0.85 else "high" if sim > 0.7
               else "moderate" if sim > 0.55 else "low")
    return f"cosine similarity = {sim:.3f}  ({verdict})"

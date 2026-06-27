"""Personal notes + fun random utilities."""

import datetime as dt
import random
import re
import secrets
import string

from . import tool
from ..paths import NOTES_FILE


# ─────────────────────────── notes ─────────────────────────── #
@tool(
    description="Append a quick note to the notes file.",
    parameters={"type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]},
)
def add_note(text: str) -> str:
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {text}\n")
    return "Noted."


@tool(description="Read all saved notes.",
      parameters={"type": "object", "properties": {}})
def read_notes() -> str:
    if not NOTES_FILE.exists():
        return "No notes yet."
    return NOTES_FILE.read_text(encoding="utf-8")[-4000:]


# ─────────────────────────── fun ─────────────────────────── #
_DICE_RE = re.compile(r"(\d+)d(\d+)")


@tool(
    description="Roll dice in NdM notation, e.g. '2d6'.",
    parameters={"type": "object",
                "properties": {"dice": {"type": "string", "default": "1d6"}}},
)
def roll_dice(dice: str = "1d6") -> str:
    m = _DICE_RE.match(dice.lower())
    if not m:
        return "use NdM, e.g. 2d6"
    n, sides = m.groups()
    rolls = [random.randint(1, int(sides)) for _ in range(int(n))]
    return f"{dice} → {rolls}  (total {sum(rolls)})"


@tool(description="Flip a coin.",
      parameters={"type": "object", "properties": {}})
def flip_coin() -> str:
    return random.choice(["heads", "tails"])


@tool(
    description="Pick a random item from a list.",
    parameters={
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
        "required": ["items"],
    },
)
def pick_random(items: list[str]) -> str:
    return random.choice(items) if items else "(empty list)"


@tool(
    description="Generate a strong random password.",
    parameters={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "default": 16, "minimum": 4, "maximum": 128},
            "symbols": {"type": "boolean", "default": True},
        },
    },
)
def password(length: int = 16, symbols: bool = True) -> str:
    chars = string.ascii_letters + string.digits + (string.punctuation if symbols else "")
    return "".join(secrets.choice(chars) for _ in range(length))

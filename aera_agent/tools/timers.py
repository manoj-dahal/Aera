"""Timers, alarms, and persistent reminders."""

import datetime as dt
import json
import re
import threading
import time

from . import tool
from ..paths import REMINDERS_FILE


# ─────────────────────────────────────────────────────────────── #
#  Timer state
# ─────────────────────────────────────────────────────────────── #
_TIMERS: dict[str, threading.Timer] = {}
_NOTIFICATIONS: list[str] = []


def _notify(msg: str) -> None:
    _NOTIFICATIONS.append(msg)
    print(f"\n🔔 {msg}\n", flush=True)


def pop_notifications() -> list[str]:
    out, _NOTIFICATIONS[:] = _NOTIFICATIONS[:], []
    return out


_DUR_RE = re.compile(r"(\d+)\s*([hms])")


def _parse_duration(s: str) -> int:
    """Parse '90', '90s', '5m', '1h30m', '2h' → seconds."""
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    total = sum(int(num) * {"h": 3600, "m": 60, "s": 1}[unit]
                for num, unit in _DUR_RE.findall(s))
    if total == 0:
        raise ValueError(f"can't parse duration: {s}")
    return total


# ─────────────────────────────────────────────────────────────── #
#  Timer tools
# ─────────────────────────────────────────────────────────────── #
@tool(
    description="Set a timer that rings after a duration. "
                "Examples of duration: '90', '30s', '5m', '1h30m'.",
    parameters={
        "type": "object",
        "properties": {
            "duration": {"type": "string", "description": "e.g. '5m', '1h30m', '90s'"},
            "label":    {"type": "string", "default": ""},
        },
        "required": ["duration"],
    },
)
def set_timer(duration: str, label: str = "") -> str:
    secs = _parse_duration(duration)
    tid = f"t{int(time.time())}"
    msg = f"Timer{' ' + label if label else ''} ({duration}) finished!"
    t = threading.Timer(secs, _notify, args=[msg])
    t.daemon = True; t.start()
    _TIMERS[tid] = t
    return f"Timer set for {secs} seconds (id={tid})."


@tool(
    description="Set an alarm at a specific time today (HH:MM, 24h).",
    parameters={
        "type": "object",
        "properties": {
            "time":  {"type": "string", "description": "HH:MM 24h, e.g. '07:30'"},
            "label": {"type": "string", "default": ""},
        },
        "required": ["time"],
    },
)
def set_alarm(time: str, label: str = "") -> str:
    h, m = [int(x) for x in time.split(":")]
    now = dt.datetime.now()
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    secs = int((target - now).total_seconds())
    return set_timer(str(secs), label or f"Alarm {time}")


@tool(
    description="List active timers.",
    parameters={"type": "object", "properties": {}},
)
def list_timers() -> str:
    alive = [tid for tid, t in _TIMERS.items() if t.is_alive()]
    return f"{len(alive)} active: {', '.join(alive) or 'none'}"


@tool(
    description="Cancel a timer by id (or 'all').",
    parameters={
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
)
def cancel_timer(id: str) -> str:
    if id == "all":
        for t in _TIMERS.values():
            t.cancel()
        _TIMERS.clear()
        return "All timers cancelled."
    t = _TIMERS.pop(id, None)
    if not t:
        return f"No timer {id}."
    t.cancel()
    return f"Cancelled {id}."


# ─────────────────────────────────────────────────────────────── #
#  Reminders (persisted)
# ─────────────────────────────────────────────────────────────── #
def _load_reminders() -> list[dict]:
    if REMINDERS_FILE.exists():
        return json.loads(REMINDERS_FILE.read_text())
    return []


def _save_reminders(rs: list[dict]) -> None:
    REMINDERS_FILE.write_text(json.dumps(rs, indent=2))


@tool(
    description="Add a persistent reminder (saved to disk, survives restarts).",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "due":  {"type": "string", "description": "Optional ISO datetime, e.g. '2026-07-01T09:00'"},
        },
        "required": ["text"],
    },
)
def add_reminder(text: str, due: str = "") -> str:
    rs = _load_reminders()
    rs.append({"text": text, "due": due, "created": dt.datetime.now().isoformat()})
    _save_reminders(rs)
    return f"Reminder saved ({len(rs)} total)."


@tool(
    description="List all saved reminders.",
    parameters={"type": "object", "properties": {}},
)
def list_reminders() -> str:
    rs = _load_reminders()
    if not rs:
        return "No reminders."
    return "\n".join(f"{i+1}. {r['text']}" + (f"  (due {r['due']})" if r.get('due') else "")
                     for i, r in enumerate(rs))


@tool(
    description="Delete a reminder by 1-based index, or 'all'.",
    parameters={
        "type": "object",
        "properties": {"index": {"type": "string"}},
        "required": ["index"],
    },
)
def delete_reminder(index: str) -> str:
    rs = _load_reminders()
    if index == "all":
        _save_reminders([]); return "All reminders deleted."
    i = int(index) - 1
    if not 0 <= i < len(rs):
        return "Index out of range."
    removed = rs.pop(i); _save_reminders(rs)
    return f"Deleted: {removed['text']}"

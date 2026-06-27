"""Time & date tools."""

import datetime as dt

from . import tool


@tool(
    description="Get the current local date and time. Optionally for a given IANA timezone like 'Asia/Tokyo'.",
    parameters={
        "type": "object",
        "properties": {
            "timezone": {"type": "string",
                         "description": "IANA TZ name, e.g. 'Europe/London'. Omit for system local."},
        },
    },
)
def get_time(timezone: str | None = None) -> str:
    try:
        if timezone:
            from zoneinfo import ZoneInfo
            now = dt.datetime.now(ZoneInfo(timezone))
        else:
            now = dt.datetime.now().astimezone()
        return now.strftime("%A, %B %d %Y, %I:%M:%S %p %Z").strip()
    except Exception as e:
        return f"Couldn't get time: {e}"


@tool(
    description="Compute the difference between two dates/times. "
                "Examples: 'days until 2026-12-25', 'time between 09:00 and 17:30'.",
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "ISO date or datetime, or 'now'"},
            "end":   {"type": "string", "description": "ISO date or datetime"},
        },
        "required": ["start", "end"],
    },
)
def date_diff(start: str, end: str) -> str:
    def parse(s: str) -> dt.datetime:
        if s.lower() == "now":
            return dt.datetime.now()
        try:
            return dt.datetime.fromisoformat(s)
        except ValueError:
            return dt.datetime.strptime(s, "%Y-%m-%d")

    a, b = parse(start), parse(end)
    delta = b - a
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins = rem // 60
    return f"{days} days, {hours} hours, {mins} minutes between {a} and {b}"

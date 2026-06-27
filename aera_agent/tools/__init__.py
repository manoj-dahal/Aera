"""
Agent-tool registry.

Each tool is registered with @tool(...) and lives in one of the domain
modules below (time_date, weather, web, …). Importing this package
auto-imports them all so the @tool decorators populate _REGISTRY.

Public API:
    @tool(...)              decorator
    openai_schemas()        list[dict] in OpenAI chat-completions format
    dispatch(name, args)    run a tool by name with JSON-string args
    list_tools()            list[str] of registered names
    summary()               one-line "N tools: a, b, c, …"
"""

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]
    requires_confirm: bool = False


_REGISTRY: dict[str, Tool] = {}


def tool(description: str, parameters: dict, *, confirm: bool = False):
    """Decorator to register a function as an LLM-callable tool."""
    def deco(fn: Callable[..., Any]):
        _REGISTRY[fn.__name__] = Tool(
            name=fn.__name__,
            description=description,
            parameters=parameters,
            func=fn,
            requires_confirm=confirm,
        )
        return fn
    return deco


def openai_schemas() -> list[dict]:
    return [
        {"type": "function",
         "function": {"name": t.name, "description": t.description,
                      "parameters": t.parameters}}
        for t in _REGISTRY.values()
    ]


def dispatch(name: str, args_json: str) -> str:
    if name not in _REGISTRY:
        return f"[tool error] unknown tool: {name}"
    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        return f"[tool error] bad JSON args: {e}"
    try:
        result = _REGISTRY[name].func(**args)
        if not isinstance(result, str):
            result = json.dumps(result, default=str)
        return result[:4000]
    except Exception as e:
        return f"[tool error] {type(e).__name__}: {e}"


def list_tools() -> list[str]:
    return list(_REGISTRY.keys())


def summary() -> str:
    return f"{len(_REGISTRY)} tools registered: {', '.join(sorted(_REGISTRY))}"


# ─────────────────────────────────────────────────────────────────────
#  Import every domain module so its @tool decorators register on load.
#  Order doesn't matter; everything ends up in _REGISTRY.
# ─────────────────────────────────────────────────────────────────────
from . import (              # noqa: E402, F401
    time_date,
    weather,
    web,
    timers,
    launchers,
    math_units,
    clipboard_fs,
    system,
    notes_fun,
    translate,
    memory_tools,
    speaker_tools,
)


def pop_notifications() -> list[str]:
    """Re-export so callers don't need to know which module owns the queue."""
    from .timers import pop_notifications as _p
    return _p()

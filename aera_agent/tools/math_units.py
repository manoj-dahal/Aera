"""Math, units, currency."""

import math

from . import tool
from ._http import http_json


@tool(
    description="Evaluate a math expression safely. Supports +, -, *, /, **, parentheses, "
                "and functions: sqrt, sin, cos, tan, log, exp, pi, e.",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    allowed = {k: getattr(math, k) for k in
               ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan",
                "log", "log10", "log2", "exp", "pow",
                "pi", "e", "tau", "floor", "ceil")}
    allowed["abs"] = abs; allowed["round"] = round
    try:
        code = compile(expression, "<calc>", "eval")
        for name in code.co_names:
            if name not in allowed:
                return f"Disallowed name: {name}"
        return str(eval(code, {"__builtins__": {}}, allowed))
    except Exception as e:
        return f"Math error: {e}"


_LENGTH = {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001,
           "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144}
_MASS   = {"kg": 1, "g": 0.001, "lb": 0.45359237, "oz": 0.0283495}


@tool(
    description="Convert between units. Categories: length (m, km, mi, ft, in, cm), "
                "mass (kg, g, lb, oz), temperature (C, F, K).",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from":  {"type": "string"},
            "to":    {"type": "string"},
        },
        "required": ["value", "from", "to"],
    },
)
def convert_units(value: float, **kwargs) -> str:
    src = kwargs.get("from", "").lower()
    dst = kwargs.get("to", "").lower()
    if src in _LENGTH and dst in _LENGTH:
        return f"{value} {src} = {value * _LENGTH[src] / _LENGTH[dst]:.6g} {dst}"
    if src in _MASS and dst in _MASS:
        return f"{value} {src} = {value * _MASS[src] / _MASS[dst]:.6g} {dst}"
    if src in ("c", "f", "k") and dst in ("c", "f", "k"):
        c = value if src == "c" else (value - 32) * 5 / 9 if src == "f" else value - 273.15
        out = c if dst == "c" else c * 9 / 5 + 32 if dst == "f" else c + 273.15
        return f"{value}°{src.upper()} = {out:.4g}°{dst.upper()}"
    return f"Don't know how to convert {src} → {dst}"


@tool(
    description="Get the latest fiat currency exchange rate. Free, no API key.",
    parameters={
        "type": "object",
        "properties": {
            "amount": {"type": "number", "default": 1},
            "from":   {"type": "string", "description": "ISO code, e.g. USD"},
            "to":     {"type": "string", "description": "ISO code, e.g. EUR"},
        },
        "required": ["from", "to"],
    },
)
def currency(amount: float = 1, **kwargs) -> str:
    src = kwargs["from"].upper(); dst = kwargs["to"].upper()
    data = http_json(f"https://open.er-api.com/v6/latest/{src}")
    rate = data.get("rates", {}).get(dst)
    if rate is None:
        return f"No rate for {src}→{dst}"
    return f"{amount} {src} = {amount * rate:.4f} {dst}  (rate {rate})"

"""Clipboard read/write + sandboxed workspace file tools."""

import platform
import subprocess
from pathlib import Path

from . import tool
from ..paths import WORKSPACE_DIR


# ───────────── clipboard ───────────── #
def _clip_get() -> str:
    sysname = platform.system()
    if sysname == "Darwin":
        return subprocess.check_output(["pbpaste"], text=True)
    if sysname == "Windows":
        return subprocess.check_output(["powershell", "-command", "Get-Clipboard"], text=True)
    return subprocess.check_output(["xclip", "-selection", "clipboard", "-o"], text=True)


def _clip_set(text: str) -> None:
    sysname = platform.system()
    if sysname == "Darwin":
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE); p.communicate(text.encode())
    elif sysname == "Windows":
        p = subprocess.Popen(["clip"], stdin=subprocess.PIPE); p.communicate(text.encode("utf-16le"))
    else:
        p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        p.communicate(text.encode())


@tool(description="Read the system clipboard text.",
      parameters={"type": "object", "properties": {}})
def clipboard_read() -> str:
    try: return _clip_get() or "(empty)"
    except Exception as e: return f"Clipboard error: {e}"


@tool(
    description="Copy text to the system clipboard.",
    parameters={"type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]},
)
def clipboard_write(text: str) -> str:
    try:
        _clip_set(text)
        return f"Copied {len(text)} chars to clipboard."
    except Exception as e:
        return f"Clipboard error: {e}"


# ───────────── sandboxed file ops ───────────── #
def _safe_path(p: str) -> Path:
    full = (WORKSPACE_DIR / p).resolve()
    if WORKSPACE_DIR.resolve() not in full.parents and full != WORKSPACE_DIR.resolve():
        raise ValueError("Path escapes workspace.")
    return full


@tool(
    description="List files in the assistant's workspace folder (or a subdir).",
    parameters={"type": "object",
                "properties": {"path": {"type": "string", "default": "."}}},
)
def list_files(path: str = ".") -> str:
    p = _safe_path(path)
    if not p.exists(): return f"Not found: {path}"
    items = [f"{'[d] ' if x.is_dir() else '    '}{x.name}  ({x.stat().st_size} B)"
             for x in sorted(p.iterdir())]
    return "\n".join(items) or "(empty)"


@tool(
    description="Read a text file from the workspace (max 4000 chars returned).",
    parameters={"type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]},
)
def read_file(path: str) -> str:
    return _safe_path(path).read_text(encoding="utf-8", errors="replace")[:4000]


@tool(
    description="Write text to a file in the workspace (overwrites).",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    },
    confirm=True,
)
def write_file(path: str, content: str) -> str:
    p = _safe_path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {p.relative_to(WORKSPACE_DIR)}"

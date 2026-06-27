"""Browser / app launchers."""

import os
import platform
import subprocess
import urllib.parse
import webbrowser

from . import tool


@tool(
    description="Open a URL in the default browser.",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
)
def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"


@tool(
    description="Open an application by name (e.g. 'notepad', 'calc', 'Safari', 'firefox').",
    parameters={
        "type": "object",
        "properties": {"app": {"type": "string"}},
        "required": ["app"],
    },
    confirm=True,
)
def open_app(app: str) -> str:
    sysname = platform.system()
    try:
        if sysname == "Windows":
            os.startfile(app)              # type: ignore[attr-defined]
        elif sysname == "Darwin":
            subprocess.Popen(["open", "-a", app])
        else:
            subprocess.Popen([app])
        return f"Launched {app}"
    except Exception as e:
        return f"Couldn't launch {app}: {e}"


@tool(
    description="Search the web in the default browser (opens results page).",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
)
def open_search(query: str) -> str:
    return open_url("https://duckduckgo.com/?q=" + urllib.parse.quote(query))

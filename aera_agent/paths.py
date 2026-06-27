"""
Centralized filesystem paths for AERA Agent.

Works in three deployment modes:
  1. From source     (`python -m aera_agent`)        → ROOT = project folder
  2. pip-installed   (`pip install -e .`)            → ROOT = site-packages parent
  3. PyInstaller     (frozen bundle)                 → ROOT = folder next to AERA.exe

Writable state (config, data, voices, workspace) always lives next to the
executable / project root so users can find and edit it. Override the data
location with the AERA_DATA_DIR env var if you want (e.g. ~/.aera/).
"""

import os
import sys
from pathlib import Path


def _project_root() -> Path:
    """Resolve the writable project root for whatever environment we're in."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — sys.executable is .../AERA/AERA(.exe)
        # We want the writable folder *next to* that exe, not _internal/.
        return Path(sys.executable).resolve().parent
    # Running from source: this file is aera_agent/paths.py → go up two.
    return Path(__file__).resolve().parent.parent


ROOT = _project_root()

# ── runtime data dir (created on first import) ──
DATA_DIR = Path(os.environ.get("AERA_DATA_DIR") or (ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── config file (kept at project root for easy editing) ──
CONFIG_FILE = ROOT / "config.json"

# ── persisted JSON state files ──
MEMORY_FILE     = DATA_DIR / "memory.json"
MACROS_FILE     = DATA_DIR / "macros.json"
APPS_FILE       = DATA_DIR / "apps.json"
CONTACTS_FILE   = DATA_DIR / "contacts.json"
REMINDERS_FILE  = DATA_DIR / "reminders.json"
SPEAKERS_FILE   = DATA_DIR / "speakers.json"
HISTORY_FILE    = DATA_DIR / "history.json"
NOTES_FILE      = DATA_DIR / "notes.txt"

# ── voice / audio caches ──
VOICES_DIR = ROOT / "voices"
VOICES_DIR.mkdir(exist_ok=True)

# ── file-tool sandbox ──
WORKSPACE_DIR = ROOT / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

# ── gallery (subfolder of workspace) ──
GALLERY_DIR = WORKSPACE_DIR / "gallery"
GALLERY_DIR.mkdir(exist_ok=True)

# ── bundled read-only assets (icon, etc.) ──
# In a PyInstaller bundle these live inside sys._MEIPASS, not the writable root.
ASSETS_DIR = Path(getattr(sys, "_MEIPASS", str(ROOT))) / "assets"

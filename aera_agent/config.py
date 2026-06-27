"""Provider / voice / speech / wake / memory config loader."""

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .paths import CONFIG_FILE, ASSETS_DIR, ROOT


def _bundled_default() -> Path | None:
    """Find a default config.json shipped inside the bundle/source tree."""
    # PyInstaller bundles it into _MEIPASS/config.json (we declared that in
    # aera.spec datas).  Source tree has it at ROOT/config.json originally.
    for cand in (Path(getattr(sys, "_MEIPASS", "")) / "config.json",
                 ASSETS_DIR.parent / "config.json"):
        if cand.exists() and cand != CONFIG_FILE:
            return cand
    return None


@dataclass
class Config:
    """Wraps config.json with active-provider helpers."""

    data: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config":
        # If the writable config doesn't exist yet, seed it from the bundled
        # default. This makes a fresh PyInstaller install "just work".
        if not path.exists():
            default = _bundled_default()
            if default is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(default, path)
            else:
                sys.exit(f"Config file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return cls(data=json.load(f))

    def save(self, path: Path = CONFIG_FILE) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    # --- active LLM provider helpers --- #
    @property
    def active(self) -> dict:
        return self.data["providers"][self.data["active_provider"]]

    def set_active(self, name: str) -> None:
        if name not in self.data["providers"]:
            raise KeyError(f"Unknown provider: {name}")
        self.data["active_provider"] = name
        self.save()

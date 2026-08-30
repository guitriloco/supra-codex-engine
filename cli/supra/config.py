"""Config management for the Supra-Codex CLI.

Configuration lives at ``~/.supra-codex/config.json`` and is created on first
use with sensible defaults. Clients read it to discover the engine's API
base URL and any custom HTTP timeouts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_DIR = Path.home() / ".supra-codex"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

DEFAULTS: Dict[str, Any] = {
    "api_base_url": "http://localhost:8000",
    "timeout_seconds": 60.0,
}


class Config:
    """Thin wrapper around the JSON config file with defaults merged in."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.path = path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = dict(DEFAULTS)
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except (json.JSONDecodeError, OSError):
                # Fall back to defaults on a corrupt/unreadable config; don't crash.
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default if default is not None else DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def api_base_url(self) -> str:
        return str(self.get("api_base_url")).rstrip("/")

    @property
    def timeout_seconds(self) -> float:
        try:
            return float(self.get("timeout_seconds"))
        except (TypeError, ValueError):
            return float(DEFAULTS["timeout_seconds"])


def ensure_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Return a Config, initializing the directory if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return Config(path)

"""Configuration manager for unb-consultant.

Stores registered experts and global settings in ~/.unb-consultant/config.json.
"""

import json
import os
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".unb-consultant"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "version": 1,
    "lang": None,  # Auto-detect if None
    "tier": None,  # Auto-detect if None
    "experts": {},
}


class Config:
    """Global configuration for unb-consultant."""

    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @property
    def lang(self) -> str | None:
        return self._data.get("lang")

    @lang.setter
    def lang(self, value: str | None):
        self._data["lang"] = value
        self.save()

    @property
    def tier(self) -> str | None:
        return self._data.get("tier")

    @tier.setter
    def tier(self, value: str | None):
        self._data["tier"] = value
        self.save()

    # ─── Expert management ───

    def list_experts(self) -> dict:
        """Return all registered experts."""
        return dict(self._data.get("experts", {}))

    def get_expert(self, name: str) -> dict | None:
        """Get expert by name. Returns None if not found."""
        return self._data.get("experts", {}).get(name)

    def add_expert(self, name: str, data: dict):
        """Register a new expert."""
        if "experts" not in self._data:
            self._data["experts"] = {}
        self._data["experts"][name] = data
        self.save()

    def remove_expert(self, name: str) -> bool:
        """Remove an expert. Returns True if existed."""
        if name in self._data.get("experts", {}):
            del self._data["experts"][name]
            self.save()
            return True
        return False

    def update_expert(self, name: str, data: dict):
        """Update expert metadata (merge into existing)."""
        if "experts" not in self._data:
            self._data["experts"] = {}
        if name in self._data["experts"]:
            self._data["experts"][name].update(data)
        else:
            self._data["experts"][name] = data
        self.save()

    def expert_count(self) -> int:
        return len(self._data.get("experts", {}))


# Global singleton
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config():
    global _config
    _config = None
    import os as _os
    if CONFIG_PATH.exists():
        _os.remove(CONFIG_PATH)

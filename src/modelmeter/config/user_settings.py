"""File-based user settings store for runtime overrides."""

from __future__ import annotations

import json
from pathlib import Path

_USER_SETTINGS_PATH = Path.home() / ".local" / "share" / "modelmeter" / "user_settings.json"

_ALLOWED_KEYS = frozenset({"anthropic_api_key", "openai_api_key"})


def get_user_settings_path() -> Path:
    return _USER_SETTINGS_PATH


def load_user_settings() -> dict[str, str]:
    """Load persisted user settings from disk. Returns empty dict on any error."""
    path = get_user_settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return {k: v for k, v in data.items() if k in _ALLOWED_KEYS and isinstance(v, str) and v}
    except Exception:
        return {}


def save_user_settings(data: dict[str, str | None] | dict[str, str]) -> None:
    """Persist user settings to disk, omitting keys with None/empty values."""
    path = get_user_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = {k: v for k, v in data.items() if k in _ALLOWED_KEYS and v}
    path.write_text(json.dumps(cleaned, indent=2) + "\n")

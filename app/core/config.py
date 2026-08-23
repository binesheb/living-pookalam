"""Application configuration and showroom profile loading."""

from pathlib import Path
import json
import os
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_NAME = os.getenv("LIVING_POOKALAM_PROFILE", "template")
PROFILE_ROOT = ROOT / "profiles"
RUNTIME_CONFIG_PATH = ROOT / "data" / "runtime_config.json"


def profile_path() -> Path:
    """Return the selected profile directory."""
    showroom = PROFILE_ROOT / "showrooms" / PROFILE_NAME
    if showroom.is_dir():
        return showroom
    return PROFILE_ROOT / "template"


def load_profile() -> dict[str, Any]:
    """Load profile.json from the selected profile."""
    path = profile_path() / "profile.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_runtime_config() -> dict[str, Any]:
    if not RUNTIME_CONFIG_PATH.exists():
        return {"camera_index": 0}
    with RUNTIME_CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return {"camera_index": 0, **json.load(handle)}


def save_runtime_config(config: dict[str, Any]) -> None:
    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = RUNTIME_CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2), encoding="utf-8")
    temporary.replace(RUNTIME_CONFIG_PATH)

"""Application configuration and showroom profile loading."""

from pathlib import Path
import json
import os
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILE_NAME = os.getenv("LIVING_POOKALAM_PROFILE", "template")
PROFILE_ROOT = ROOT / "profiles"


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

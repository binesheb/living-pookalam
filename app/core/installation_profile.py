"""Portable installation profile for camera/projector geometry and colour."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from app.core.color_calibration import ColorProfile


@dataclass
class InstallationProfile:
    name: str = "default"
    projector_width: int = 1920
    projector_height: int = 1080
    projector_refresh_hz: float = 60.0
    camera_id: int = 0
    geometry_valid: bool = False
    colour_valid: bool = False
    calibration_revision: int = 0

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "InstallationProfile":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))

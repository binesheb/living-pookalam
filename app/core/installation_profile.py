"""Portable installation profile for camera/projector geometry and colour."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass
class InstallationProfile:
    name: str = "default"
    projector_width: int = 1920
    projector_height: int = 1080
    projector_refresh_hz: float = 60.0
    camera_id: int = 0
    geometry_valid: bool = False
    colour_valid: bool = False
    surface_valid: bool = False
    calibration_revision: int = 0
    surface_black_rgb: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    surface_white_rgb: list[float] = field(default_factory=lambda: [255.0, 255.0, 255.0])
    surface_brightness_headroom: float = 1.0
    surface_uniformity: float = 1.0

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "InstallationProfile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        # Keep older installation profiles compatible.
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

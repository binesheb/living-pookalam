"""Production pipeline contracts for Live Pookalam.

This module defines the release architecture without coupling UI, camera,
and renderer implementations. It is intentionally small and deterministic so
field components can be replaced independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SystemMode(str, Enum):
    SETUP = "setup"
    CALIBRATION = "calibration"
    ANALYSIS = "analysis"
    SHOW = "show"
    SAFE = "safe"


@dataclass(frozen=True)
class OutputSpec:
    width: int = 1920
    height: int = 1080
    target_fps: int = 60
    black_outside_mask: bool = True
    edge_margin_px: int = 12
    feather_px: int = 6


@dataclass
class PipelineHealth:
    camera_ok: bool = False
    projector_ok: bool = False
    calibration_ok: bool = False
    pattern_ok: bool = False
    mask_ok: bool = False
    fps: float = 0.0
    frame_time_ms: float = 0.0
    dropped_frames: int = 0
    messages: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return all((self.camera_ok, self.projector_ok, self.calibration_ok, self.pattern_ok, self.mask_ok))


@dataclass
class PookalamModel:
    """Normalized geometry shared by analysis, effects and compositor."""
    contour: Any = None
    centre: tuple[float, float] = (0.5, 0.5)
    radius: float = 0.4
    rings: tuple[float, ...] = ()
    regions: tuple[Any, ...] = ()
    dominant_colours: tuple[tuple[int, int, int], ...] = ()
    symmetry_order: int = 0
    confidence: float = 0.0
    width: int = 1
    height: int = 1


@dataclass(frozen=True)
class ShowScene:
    id: str
    name: str
    duration_s: float
    preset: str
    transition: str = "crossfade"
    interaction: bool = False


DEFAULT_SHOW: tuple[ShowScene, ...] = (
    ShowScene("welcome", "Welcome", 6, "REVEAL", "radial_reveal"),
    ShowScene("bloom", "Living Flower", 10, "LIVING_FLOWER", "flower_bloom"),
    ShowScene("gold", "Onam Gold", 12, "ONAM_GOLD", "golden_sweep"),
    ShowScene("interactive", "Magic Touch", 20, "MAGIC_TOUCH", "soft_dissolve", True),
    ShowScene("finale", "Mahabali Glow", 12, "MAHABALI_GLOW", "radial_reveal"),
)

"""Hardware capability abstraction for Windows projector/camera installations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplaySpec:
    width: int = 1920
    height: int = 1080
    refresh_hz: float = 60.0

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 0.0


@dataclass(frozen=True)
class CameraSpec:
    device_id: int = 0
    width: int = 1920
    height: int = 1080
    fps: float = 30.0


@dataclass(frozen=True)
class HardwareProfile:
    projector: DisplaySpec = DisplaySpec()
    camera: CameraSpec = CameraSpec()

    @property
    def native_output(self) -> tuple[int, int]:
        return self.projector.width, self.projector.height

    @property
    supports_baseline(self) -> bool:
        return self.projector.width >= 1920 and self.projector.height >= 1080 and self.projector.refresh_hz >= 30

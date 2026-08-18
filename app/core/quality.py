"""Runtime quality governor for the 1080p field projector.

The governor protects the installation from runaway particle/effect load.
It prefers degrading decorative effects over dropping the base projection.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QualityGovernor:
    target_fps: float = 60.0
    minimum_fps: float = 45.0
    level: int = 3  # 3=cinematic, 2=high, 1=balanced, 0=safe

    def update(self, fps: float) -> int:
        if fps < self.minimum_fps:
            self.level = max(0, self.level - 1)
        elif fps > self.target_fps * 0.97:
            self.level = min(3, self.level + 1)
        return self.level

    def particle_limit(self) -> int:
        return (250, 450, 700, 900)[self.level]

    def glow_layers(self) -> int:
        return (1, 2, 3, 4)[self.level]

    def allow_secondary_effects(self) -> bool:
        return self.level >= 1

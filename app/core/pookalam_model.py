"""Shared geometry model used by vision, effects, interaction and projection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class PookalamModel:
    """Canonical Pookalam-space representation.

    Coordinates are normalized to [0, 1] so the same model works at camera,
    preview and 1920x1080 projector resolutions.
    """

    boundary: np.ndarray | None = None
    edge_map: np.ndarray | None = None
    center: tuple[float, float] = (0.5, 0.5)
    radius: float = 0.45
    rings: list[float] = field(default_factory=list)
    regions: list[np.ndarray] = field(default_factory=list)
    dominant_colors: list[tuple[int, int, int]] = field(default_factory=list)
    symmetry_order: int = 0
    confidence: float = 0.0

    @classmethod
    def from_boundary(cls, points: Sequence[Sequence[float]], confidence: float = 1.0) -> "PookalamModel":
        pts = np.asarray(points, dtype=np.float32).reshape(-1, 2)
        if len(pts) < 3:
            raise ValueError("A Pookalam boundary requires at least three points")
        centre = tuple(np.mean(pts, axis=0).tolist())
        radius = float(np.max(np.linalg.norm(pts - np.asarray(centre), axis=1)))
        return cls(boundary=pts, center=centre, radius=radius, confidence=float(confidence))

    @property
    def valid(self) -> bool:
        return self.boundary is not None and len(self.boundary) >= 3 and self.confidence > 0

    def contains(self, point: tuple[float, float]) -> bool:
        if not self.valid:
            return False
        p = np.asarray(point, dtype=np.float32)
        # Ray casting without a dependency on a GUI/rendering framework.
        pts = self.boundary
        inside = False
        j = len(pts) - 1
        for i in range(len(pts)):
            xi, yi = pts[i]
            xj, yj = pts[j]
            crosses = ((yi > p[1]) != (yj > p[1]))
            if crosses:
                x_at_y = (xj - xi) * (p[1] - yi) / ((yj - yi) or 1e-9) + xi
                if p[0] < x_at_y:
                    inside = not inside
            j = i
        return inside

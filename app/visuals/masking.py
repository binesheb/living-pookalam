"""Projection-space masking for Live Pookalam.

All effect primitives are treated as light that must remain inside the detected
Pookalam footprint. The narrow edge band is the only intentional spill allowance.
"""
from __future__ import annotations

import math
from typing import Iterable

import cv2
import numpy as np


class ProjectionMask:
    """Conservative polygon mask in projector pixel coordinates."""

    def __init__(self, contour: np.ndarray | None, width: int, height: int, edge_margin: int = 8):
        self.width = int(width)
        self.height = int(height)
        self.contour = None if contour is None else np.asarray(contour, dtype=np.float32).reshape(-1, 2)
        self.edge_margin = max(0, int(edge_margin))

    def _distance(self, x: float, y: float) -> float:
        if self.contour is None or len(self.contour) < 3:
            return 0.0
        return float(cv2.pointPolygonTest(self.contour.reshape(-1, 1, 2), (float(x), float(y)), True))

    def inside(self, x: float, y: float, radius: float = 0.0, edge: bool = False) -> bool:
        if self.contour is None or len(self.contour) < 3:
            return False
        d = self._distance(x, y)
        if edge:
            return d >= -self.edge_margin
        return d >= max(0.0, float(radius))

    def line_segments(self, points: Iterable[tuple[float, float]], edge: bool = False, clearance: float = 0.0) -> list[list[tuple[float, float]]]:
        pts = list(points)
        if len(pts) < 2:
            return []
        out: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for p in pts:
            ok = self.inside(p[0], p[1], radius=clearance, edge=edge)
            if ok:
                current.append((float(p[0]), float(p[1])))
            elif current:
                if len(current) >= 2:
                    out.append(current)
                current = []
        if len(current) >= 2:
            out.append(current)
        return out


class MaskedDrawAdapter:
    """Canvas adapter that clips effect primitives to the Pookalam mask."""

    def __init__(self, draw, mask: ProjectionMask):
        self.draw = draw
        self.mask = mask

    def circle(self, x, y, r, fill, width=0, edge=False):
        r = float(r)
        if self.mask.inside(x, y, r if not edge else 0, edge=edge):
            self.draw.circle(x, y, r, fill, width=width)
        elif self.mask.inside(x, y, edge=True) and r <= self.mask.edge_margin * 1.5:
            # Small edge markers are allowed in the narrow band even when the
            # caller does not explicitly pass edge=True.
            self.draw.circle(x, y, min(r, self.mask.edge_margin), fill, width=width)

    def ellipse(self, rect, fill, width=0, edge=False):
        x1, y1, x2, y2 = map(float, rect)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        r = max(abs(x2 - x1), abs(y2 - y1)) / 2
        if self.mask.inside(cx, cy, r if not edge else 0, edge=edge):
            self.draw.ellipse(rect, fill, width=width)

    def line(self, points, fill, width=1, edge=False):
        pts = [(float(p[0]), float(p[1])) for p in points]
        if len(pts) < 2:
            return
        sampled: list[tuple[float, float]] = []
        for a, b in zip(pts, pts[1:]):
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            steps = max(1, int(d / 6.0))
            for i in range(steps):
                q = i / steps
                sampled.append((a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q))
        sampled.append(pts[-1])
        clearance = max(0.0, float(width) * 0.5)
        segments = self.mask.line_segments(sampled, edge=edge, clearance=clearance)
        if not segments:
            # Permit only the narrow edge band as a fallback for contour FX.
            segments = self.mask.line_segments(sampled, edge=True, clearance=0.0)
        for segment in segments:
            self.draw.line(segment, fill, width=width)

    def polygon(self, points, fill, edge=False):
        pts = [(float(p[0]), float(p[1])) for p in points]
        if pts and all(self.mask.inside(x, y, edge=edge) for x, y in pts):
            self.draw.polygon(pts, fill)

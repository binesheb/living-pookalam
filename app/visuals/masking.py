"""Projection-space masking for Live Pookalam.

Effects are rendered to a black projector surface. This adapter prevents effect
primitives from being drawn outside the detected Pookalam footprint, so the
projector does not illuminate the surrounding rectangular floor area.
"""
from __future__ import annotations

import math
from typing import Iterable

import cv2
import numpy as np


class ProjectionMask:
    """Conservative polygon mask in projector pixel coordinates."""

    def __init__(self, contour: np.ndarray | None, width: int, height: int, edge_margin: int = 10):
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
            return True
        d = self._distance(x, y)
        if edge:
            return d >= -self.edge_margin
        return d >= max(0.0, float(radius))

    def line_segments(self, points: Iterable[tuple[float, float]], edge: bool = False) -> list[list[tuple[float, float]]]:
        pts = list(points)
        if len(pts) < 2:
            return []
        out: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for p in pts:
            ok = self.inside(p[0], p[1], edge=edge)
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
    """Wrap a canvas-style draw adapter and suppress out-of-mask primitives."""

    def __init__(self, draw, mask: ProjectionMask):
        self.draw = draw
        self.mask = mask

    def circle(self, x, y, r, fill, width=0, edge=False):
        r = float(r)
        if self.mask.inside(x, y, r if not edge else 0, edge=edge):
            self.draw.circle(x, y, r, fill, width=width)
        elif self.mask.inside(x, y, edge=True) and r <= self.mask.edge_margin * 1.5:
            # Preserve narrow edge highlights without allowing large glows to spill.
            self.draw.circle(x, y, min(r, self.mask.edge_margin), fill, width=width)

    def ellipse(self, rect, fill, width=0, edge=False):
        x1, y1, x2, y2 = map(float, rect)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        r = max(abs(x2 - x1), abs(y2 - y1)) / 2
        if self.mask.inside(cx, cy, r if not edge else 0, edge=edge):
            self.draw.ellipse(rect, fill, width=width)

    def line(self, points, fill, width=1, edge=False):
        pts = [(float(p[0]), float(p[1])) for p in points]
        sampled: list[tuple[float, float]] = []
        for a, b in zip(pts, pts[1:]):
            d = math.hypot(b[0] - a[0], b[1] - a[1])
            steps = max(1, int(d / 6.0))
            for i in range(steps):
                q = i / steps
                sampled.append((a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q))
        sampled.append(pts[-1])
        segments = self.mask.line_segments(sampled, edge=edge)
        if not segments:
            # Edge FX may occupy a narrow band around the detected contour.
            segments = self.mask.line_segments(sampled, edge=True)
        for segment in segments:
            self.draw.line(segment, fill, width=width)

    def polygon(self, points, fill, edge=False):
        pts = [(float(p[0]), float(p[1])) for p in points]
        if pts and all(self.mask.inside(x, y, edge=edge) for x, y in pts):
            self.draw.polygon(pts, fill)

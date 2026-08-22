"""Map renderer primitives from physical floor millimetres to projector pixels."""
from __future__ import annotations

import cv2
import numpy as np


class FloorProjectorDrawAdapter:
    """DrawAdapter-compatible facade with a floor-mm -> projector-pixel map."""

    def __init__(self, canvas, floor_to_projector: np.ndarray):
        self.canvas = canvas
        self.homography = np.asarray(floor_to_projector, dtype=np.float32)

    def _map(self, points):
        pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
        mapped = cv2.perspectiveTransform(pts, self.homography).reshape(-1, 2)
        return [(float(x), float(y)) for x, y in mapped]

    def circle(self, x, y, r, fill, width=0):
        angles = np.linspace(0.0, np.pi * 2.0, 65, dtype=np.float32)[:-1]
        points = [(x + r * float(np.cos(a)), y + r * float(np.sin(a))) for a in angles]
        mapped = self._map(points)
        flat = [v for p in mapped for v in p]
        if width == 0:
            self.canvas.create_polygon(*flat, fill=fill, outline=fill)
        else:
            self.canvas.create_line(*flat, flat[0], flat[1], fill=fill, width=max(1, width), smooth=True)

    def ellipse(self, rect, fill, width=0):
        x0, y0, x1, y1 = map(float, rect)
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        rx, ry = abs(x1 - x0) * 0.5, abs(y1 - y0) * 0.5
        angles = np.linspace(0.0, np.pi * 2.0, 65, dtype=np.float32)[:-1]
        points = [(cx + rx * float(np.cos(a)), cy + ry * float(np.sin(a))) for a in angles]
        mapped = self._map(points)
        flat = [v for p in mapped for v in p]
        if width == 0:
            self.canvas.create_polygon(*flat, fill=fill, outline=fill)
        else:
            self.canvas.create_line(*flat, flat[0], flat[1], fill=fill, width=max(1, width), smooth=True)

    def line(self, points, fill, width=1):
        mapped = self._map(points)
        self.canvas.create_line(*[v for p in mapped for v in p], fill=fill,
                                width=width, smooth=True)

    def polygon(self, points, fill):
        mapped = self._map(points)
        self.canvas.create_polygon(*[v for p in mapped for v in p], fill=fill)

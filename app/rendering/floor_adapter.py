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
        edge = self._map([(x-r, y), (x+r, y), (x, y-r), (x, y+r)])
        left, right, top, bottom = edge
        self.canvas.create_oval(left[0], top[1], right[0], bottom[1],
                                fill=fill if width == 0 else "", outline=fill,
                                width=max(1, width))

    def ellipse(self, rect, fill, width=0):
        x0, y0, x1, y1 = rect
        mapped = self._map([(x0, y0), (x1, y1)])
        self.canvas.create_oval(mapped[0][0], mapped[0][1], mapped[1][0], mapped[1][1],
                                fill=fill if width == 0 else "", outline=fill,
                                width=max(1, width))

    def line(self, points, fill, width=1):
        mapped = self._map(points)
        self.canvas.create_line(*[v for p in mapped for v in p], fill=fill,
                                width=width, smooth=True)

    def polygon(self, points, fill):
        mapped = self._map(points)
        self.canvas.create_polygon(*[v for p in mapped for v in p], fill=fill)

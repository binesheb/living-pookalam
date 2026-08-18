"""Projection-safe alpha masks for 1920x1080 output."""
from __future__ import annotations

import cv2
import numpy as np

from app.core.pookalam_model import PookalamModel

OUTPUT_SIZE = (1920, 1080)


def polygon_mask(model: PookalamModel, size: tuple[int, int] = OUTPUT_SIZE, feather_px: int = 4) -> np.ndarray:
    """Return an 8-bit alpha mask in projector coordinates.

    The caller supplies a boundary already transformed into projector-normalized
    coordinates. Everything outside the polygon is transparent/black.
    """
    width, height = size
    mask = np.zeros((height, width), dtype=np.uint8)
    if not model.valid:
        return mask
    points = np.asarray(model.boundary, dtype=np.float32).copy()
    points[:, 0] *= width - 1
    points[:, 1] *= height - 1
    points = np.round(points).astype(np.int32)
    cv2.fillPoly(mask, [points], 255)
    if feather_px > 0:
        k = max(3, feather_px * 2 + 1)
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def composite_rgba(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Create a BGR frame with black outside the supplied alpha."""
    if rgb.shape[:2] != alpha.shape:
        raise ValueError("RGB frame and alpha mask dimensions must match")
    out = rgb.copy()
    out[alpha == 0] = 0
    return out

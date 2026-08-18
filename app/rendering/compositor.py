"""Projection compositor helpers for Live Pookalam.

The field projector is a black canvas. This module prepares only the pixels that
belong to the Pookalam and keeps the visual-effects pass separate from the base
image. It is deliberately Tk/PIL friendly so the current Windows field console
can use it without adding another GUI framework.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.visuals.masking import ProjectionMask


def _fit_transform(src_w: int, src_h: int, out_w: int, out_h: int, fraction: float = 0.78):
    scale = min(out_w / max(1, src_w), out_h / max(1, src_h)) * float(fraction)
    nw = max(1, int(round(src_w * scale)))
    nh = max(1, int(round(src_h * scale)))
    ox = (out_w - nw) / 2.0
    oy = (out_h - nh) / 2.0
    return scale, ox, oy, nw, nh


def map_contour_to_projector(contour: np.ndarray | None, source_shape, out_size: tuple[int, int],
                             homography: np.ndarray | None = None, fraction: float = 0.78) -> np.ndarray | None:
    """Map a source contour into projector pixels.

    Physical source contours use the calibrated camera->projector homography.
    Digital source contours use the same deterministic fit used for the masked
    source image, so the mask and image cannot drift apart.
    """
    if contour is None or len(contour) < 3:
        return None
    out_w, out_h = map(int, out_size)
    pts = np.asarray(contour, dtype=np.float32).reshape(-1, 1, 2)
    if homography is not None:
        mapped = cv2.perspectiveTransform(pts, np.asarray(homography, dtype=np.float32)).reshape(-1, 2)
        return mapped
    src_h, src_w = source_shape[:2]
    scale, ox, oy, _, _ = _fit_transform(src_w, src_h, out_w, out_h, fraction)
    mapped = pts.reshape(-1, 2).copy()
    mapped[:, 0] = mapped[:, 0] * scale + ox
    mapped[:, 1] = mapped[:, 1] * scale + oy
    return mapped


def prepare_digital_layer(image_bgr: np.ndarray, contour: np.ndarray | None,
                          out_size: tuple[int, int], fraction: float = 0.78):
    """Return a transparent RGBA PIL layer containing only the detected Pookalam.

    If a reliable contour is unavailable, returns ``None`` rather than projecting
    the rectangular source image. This is a safety feature for the floor.
    """
    if image_bgr is None or image_bgr.size == 0 or contour is None or len(contour) < 3:
        return None
    out_w, out_h = map(int, out_size)
    src_h, src_w = image_bgr.shape[:2]
    scale, ox, oy, nw, nh = _fit_transform(src_w, src_h, out_w, out_h, fraction)
    resized = cv2.resize(image_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    rgba = cv2.cvtColor(resized, cv2.COLOR_BGR2RGBA)
    mask = np.zeros((nh, nw), dtype=np.uint8)
    pts = np.asarray(contour, dtype=np.float32).reshape(-1, 2)
    pts[:, 0] = pts[:, 0] * scale
    pts[:, 1] = pts[:, 1] * scale
    cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 255)
    rgba[:, :, 3] = mask
    layer = Image.fromarray(rgba, mode="RGBA")
    return layer, (float(ox + nw / 2), float(oy + nh / 2))


def build_projection_mask(contour_projector: np.ndarray | None, out_size: tuple[int, int], edge_margin: int = 8) -> ProjectionMask | None:
    """Create the conservative projector-space mask used by all effects."""
    if contour_projector is None or len(contour_projector) < 3:
        return None
    return ProjectionMask(np.asarray(contour_projector, dtype=np.float32), int(out_size[0]), int(out_size[1]), edge_margin=edge_margin)

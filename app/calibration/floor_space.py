"""Shared physical-floor coordinate calibration for camera and projector.

The floor is the canonical 2-D plane. Camera pixels and projector pixels are
only device-specific observations of that plane. Keeping both transforms makes
calibration explainable, testable, and reusable by rendering and perception.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np


DEFAULT_ERROR_LIMIT_MM = 12.0


@dataclass(frozen=True)
class FloorCalibrationResult:
    """Complete camera/projector calibration around one physical floor plane."""

    camera_to_floor: np.ndarray
    floor_to_camera: np.ndarray
    projector_to_floor: np.ndarray
    floor_to_projector: np.ndarray
    camera_to_projector: np.ndarray
    projector_to_camera: np.ndarray
    camera_error_mm: float
    projector_error_mm: float
    physical_width_mm: float
    physical_height_mm: float

    @property
    def max_error_mm(self) -> float:
        return max(self.camera_error_mm, self.projector_error_mm)

    @property
    def valid(self) -> bool:
        return bool(np.isfinite(self.max_error_mm))


def _points(points: Iterable[Iterable[float]]) -> np.ndarray:
    pts = np.asarray(list(points), dtype=np.float32)
    if pts.shape != (4, 2):
        raise ValueError("exactly four 2-D points are required")
    return pts


def _homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    h, _ = cv2.findHomography(src, dst, method=0)
    if h is None:
        raise ValueError("unable to compute homography from four points")
    return h.astype(np.float32)


def _invert(h: np.ndarray) -> np.ndarray:
    inv = np.linalg.inv(np.asarray(h, dtype=np.float64))
    inv /= inv[2, 2]
    return inv.astype(np.float32)


def transform(points: Iterable[Iterable[float]], homography: np.ndarray) -> np.ndarray:
    pts = np.asarray(list(points), dtype=np.float32).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, np.asarray(homography, dtype=np.float32)).reshape(-1, 2)


def reprojection_error_mm(observed: Iterable[Iterable[float]], expected: Iterable[Iterable[float]], homography: np.ndarray) -> float:
    expected_pts = _points(expected)
    mapped = transform(observed, homography)
    return float(np.mean(np.linalg.norm(mapped - expected_pts, axis=1)))


def build_floor_calibration(
    camera_points: Iterable[Iterable[float]],
    projector_points: Iterable[Iterable[float]],
    physical_width_mm: float,
    physical_height_mm: float,
) -> FloorCalibrationResult:
    """Build both device-to-floor maps from four corresponding floor corners.

    Floor coordinates are ordered clockwise from top-left and expressed in mm.
    """
    width = float(physical_width_mm)
    height = float(physical_height_mm)
    if width <= 0 or height <= 0:
        raise ValueError("physical floor dimensions must be positive")

    camera = _points(camera_points)
    projector = _points(projector_points)
    floor = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

    camera_to_floor = _homography(camera, floor)
    floor_to_camera = _invert(camera_to_floor)
    projector_to_floor = _homography(projector, floor)
    floor_to_projector = _invert(projector_to_floor)
    camera_to_projector = _homography(camera, projector)
    projector_to_camera = _invert(camera_to_projector)

    return FloorCalibrationResult(
        camera_to_floor=camera_to_floor,
        floor_to_camera=floor_to_camera,
        projector_to_floor=projector_to_floor,
        floor_to_projector=floor_to_projector,
        camera_to_projector=camera_to_projector,
        projector_to_camera=projector_to_camera,
        camera_error_mm=reprojection_error_mm(camera, floor, camera_to_floor),
        projector_error_mm=reprojection_error_mm(projector, floor, projector_to_floor),
        physical_width_mm=width,
        physical_height_mm=height,
    )


def normalized_floor_corners() -> np.ndarray:
    """Return canonical floor corners in normalized 0..1 coordinates."""
    return np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])

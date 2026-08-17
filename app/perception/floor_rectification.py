"""Perspective correction for an angled camera observing a planar floor."""

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

Point = tuple[float, float]


@dataclass(frozen=True)
class FloorCalibration:
    """A camera-to-floor homography and its canonical output size."""

    homography: np.ndarray
    width: int
    height: int

    def camera_to_floor(self, points: np.ndarray) -> np.ndarray:
        """Transform Nx2 camera points into the rectified floor coordinate system."""
        pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, self.homography).reshape(-1, 2)

    def floor_to_camera(self, points: np.ndarray) -> np.ndarray:
        """Transform Nx2 floor points back into camera coordinates."""
        inverse = np.linalg.inv(self.homography)
        pts = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, inverse).reshape(-1, 2)


class FloorRectifier:
    """Build and apply a planar perspective transform.

    The camera does not need to see the Pookalam as a circle. Four known
    floor-plane reference points define a projective mapping that turns the
    oblique camera view into a virtual top-down floor view.
    """

    @staticmethod
    def _order(points: Sequence[Point]) -> np.ndarray:
        pts = np.asarray(points, dtype=np.float32)
        if pts.shape != (4, 2):
            raise ValueError("Exactly four 2D points are required")
        sums = pts.sum(axis=1)
        diffs = np.diff(pts, axis=1).reshape(-1)
        return np.array(
            [
                pts[np.argmin(sums)],      # top-left
                pts[np.argmin(diffs)],     # top-right
                pts[np.argmax(sums)],      # bottom-right
                pts[np.argmax(diffs)],      # bottom-left
            ],
            dtype=np.float32,
        )

    @classmethod
    def calibrate(
        cls,
        camera_points: Sequence[Point],
        floor_width: int,
        floor_height: int,
        margin: int = 0,
    ) -> FloorCalibration:
        """Create a camera -> rectified floor transform from four points."""
        if floor_width <= 0 or floor_height <= 0:
            raise ValueError("Floor output dimensions must be positive")
        src = cls._order(camera_points)
        m = float(margin)
        dst = np.array(
            [
                [m, m],
                [floor_width - m, m],
                [floor_width - m, floor_height - m],
                [m, floor_height - m],
            ],
            dtype=np.float32,
        )
        h, status = cv2.findHomography(src, dst, method=0)
        if h is None or status is None:
            raise ValueError("Unable to calculate floor homography")
        return FloorCalibration(h.astype(np.float32), floor_width, floor_height)

    @staticmethod
    def warp(frame: np.ndarray, calibration: FloorCalibration) -> np.ndarray:
        """Return a top-down/rectified view of the floor."""
        return cv2.warpPerspective(
            frame,
            calibration.homography,
            (calibration.width, calibration.height),
            flags=cv2.INTER_LINEAR,
        )

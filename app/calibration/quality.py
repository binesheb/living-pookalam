"""Quality metrics for projector/camera calibration."""
from __future__ import annotations

import cv2
import numpy as np


def homography_reprojection_error(observed, expected) -> float:
    """Return mean pixel reprojection error for corresponding point pairs.

    ``observed`` contains camera-space points and ``expected`` contains their
    projector-space destinations. A low value means the four-point mapping is
    internally consistent; a high value indicates that calibration should be
    retried rather than accepted silently.
    """
    src = np.asarray(observed, dtype=np.float32).reshape(-1, 2)
    dst = np.asarray(expected, dtype=np.float32).reshape(-1, 2)
    if len(src) != len(dst) or len(src) < 4:
        return float("inf")

    homography, _ = cv2.findHomography(src, dst, 0)
    if homography is None:
        return float("inf")

    projected = cv2.perspectiveTransform(src.reshape(-1, 1, 2), homography).reshape(-1, 2)
    errors = np.linalg.norm(projected - dst, axis=1)
    return float(np.mean(errors))

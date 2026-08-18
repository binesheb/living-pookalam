import cv2
import numpy as np

from app.calibration.black_dot_stage import _detect_black_dot, _projector_points


def test_black_dot_detector_finds_target_inside_white_field():
    frame = np.full((480, 640, 3), 245, dtype=np.uint8)
    cx, cy = 320, 240
    cv2.circle(frame, (cx, cy), 42, (0, 0, 0), -1)
    point = _detect_black_dot(frame, (cx, cy), 150)
    assert point is not None
    assert np.linalg.norm(np.asarray(point) - np.array([cx, cy])) < 3.0


def test_black_dot_detector_ignores_unrelated_dark_object_outside_roi():
    frame = np.full((480, 640, 3), 245, dtype=np.uint8)
    cv2.circle(frame, (100, 100), 45, (0, 0, 0), -1)
    point = _detect_black_dot(frame, (500, 380), 100)
    assert point is None


def test_projector_geometry_points_are_inside_field():
    class Projector:
        w = 1920
        h = 1080

    pts = _projector_points(Projector())
    assert pts.shape == (4, 2)
    assert np.all(pts[:, 0] > 0)
    assert np.all(pts[:, 1] > 0)
    assert np.all(pts[:, 0] < Projector.w)
    assert np.all(pts[:, 1] < Projector.h)

import cv2
import numpy as np

from app.calibration.staged import (
    _detect_black_dot,
    _detect_projector_rectangle,
    _homography_reprojection_error,
    _white_model,
    _order_quad,
)


def test_white_frame_detects_projector_rectangle():
    baseline = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = baseline.copy()
    cv2.fillConvexPoly(frame, np.array([[80, 60], [560, 85], [535, 410], [105, 390]], np.int32), (245, 245, 245))
    quad = _detect_projector_rectangle(frame, baseline)
    assert quad is not None
    assert quad.shape == (4, 2)


def test_white_frame_detects_saturated_flat_rectangle():
    baseline = np.zeros((300, 500, 3), dtype=np.uint8)
    frame = baseline.copy()
    cv2.rectangle(frame, (60, 40), (440, 260), (255, 255, 255), -1)
    quad = _detect_projector_rectangle(frame, baseline)
    assert quad is not None
    assert quad.shape == (4, 2)


def test_white_frame_without_baseline_can_find_large_projection():
    frame = np.zeros((300, 500, 3), dtype=np.uint8)
    cv2.rectangle(frame, (70, 50), (430, 250), (220, 220, 220), -1)
    quad = _detect_projector_rectangle(frame, None)
    assert quad is not None
    assert quad.shape == (4, 2)


def test_white_model_builds_camera_response():
    frame = np.zeros((400, 600, 3), dtype=np.uint8)
    cv2.rectangle(frame, (80, 60), (520, 340), (180, 210, 240), -1)
    quad = _order_quad(np.array([[80, 60], [520, 60], [520, 340], [80, 340]], np.float32))
    model = _white_model(frame, quad)
    assert model is not None
    assert len(model["observed_white_bgr"]) == 3
    assert len(model["white_balance_gains_bgr"]) == 3
    assert model["brightness"] > 0


def test_black_dot_detects_dark_circle_on_white_field():
    frame = np.full((480, 640, 3), 245, dtype=np.uint8)
    cv2.circle(frame, (350, 150), 34, (12, 12, 12), -1)
    point = _detect_black_dot(frame, (350, 150), 90)
    assert point is not None
    assert np.linalg.norm(np.array(point) - np.array([350, 150])) < 3.0


def test_black_dot_ignores_dark_area_far_from_expected_location():
    frame = np.full((480, 640, 3), 245, dtype=np.uint8)
    cv2.circle(frame, (100, 100), 40, (10, 10, 10), -1)
    point = _detect_black_dot(frame, (500, 350), 70)
    assert point is None


def test_homography_reprojection_error_is_low_for_consistent_points():
    observed = np.float32([[100, 100], [540, 110], [530, 390], [90, 380]])
    expected = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
    error = _homography_reprojection_error(observed, expected)
    assert error < 0.01


def test_homography_reprojection_error_detects_bad_point():
    observed = np.float32([[100, 100], [540, 110], [530, 390], [90, 380]])
    expected = np.float32([[0, 0], [1920, 0], [1920, 1080], [0, 1080]])
    noisy = observed.copy()
    noisy[2] += np.array([30, -25], np.float32)
    error = _homography_reprojection_error(noisy, expected)
    assert error > 1.0

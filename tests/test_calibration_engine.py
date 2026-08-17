import cv2
import numpy as np

from app.calibration.engine import LiveCalibrator


def _frame_for(color_bgr, center=(640, 360), radius=45):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(frame, center, radius, color_bgr, -1)
    return frame


def test_active_target_rejects_unrelated_wallpaper_shapes():
    calibrator = LiveCalibrator(1920, 1080)
    calibrator.begin()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(frame, (200, 200), 80, (255, 255, 255), -1)
    assert calibrator.detect_active(frame) is None


def test_target_requires_stable_observation():
    calibrator = LiveCalibrator(1920, 1080)
    calibrator.begin()
    color = calibrator.active_target().color_bgr
    obs = calibrator.detect_active(_frame_for(color))
    assert obs is not None
    for _ in range(7):
        assert calibrator.accept_observation(obs) is False
    assert calibrator.accept_observation(obs) is True
    assert 0 in calibrator.observations


def test_build_result_after_four_stable_points():
    calibrator = LiveCalibrator(1920, 1080)
    calibrator.begin()
    positions = [(120, 100), (1160, 115), (1170, 610), (110, 600)]
    for idx, pos in enumerate(positions):
        calibrator.active_index = idx
        color = calibrator.targets[idx].color_bgr
        obs = calibrator.detect_active(_frame_for(color, pos))
        assert obs is not None
        for _ in range(8):
            calibrator.accept_observation(obs)
        assert idx in calibrator.observations
    result = calibrator.build_result()
    assert result is not None
    assert result.reprojection_error < 1e-3

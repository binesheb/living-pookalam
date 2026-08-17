import cv2
import numpy as np

from app.perception.floor_rectification import FloorRectifier


def test_four_point_calibration_rectifies_quadrilateral():
    camera = [(100, 80), (900, 120), (820, 650), (120, 600)]
    calibration = FloorRectifier.calibrate(camera, 1000, 800)
    points = np.float32(camera)
    mapped = calibration.camera_to_floor(points)
    expected = np.float32([[0, 0], [1000, 0], [1000, 800], [0, 800]])
    assert np.allclose(mapped, expected, atol=2.0)


def test_warp_returns_requested_floor_dimensions():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    calibration = FloorRectifier.calibrate(
        [(100, 100), (1100, 120), (1050, 650), (120, 640)], 800, 600
    )
    warped = FloorRectifier.warp(frame, calibration)
    assert warped.shape == (600, 800, 3)

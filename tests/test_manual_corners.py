import numpy as np
import pytest

from app.calibration.manual_corners import calibrate_manual_corners, map_floor_points, validate_corners


def test_manual_corners_map_floor_corners_back_to_camera_points():
    camera = [[100, 80], [900, 120], [860, 620], [130, 590]]
    calibration = calibrate_manual_corners(camera, 2000, 1500)
    mapped = map_floor_points([[0, 0], [2000, 0], [2000, 1500], [0, 1500]], calibration)
    assert np.allclose(mapped, np.asarray(camera, dtype=np.float32), atol=0.01)


def test_manual_corners_reject_invalid_shape():
    with pytest.raises(ValueError):
        validate_corners([[0, 0], [1, 1], [2, 2]])


def test_manual_corners_reject_zero_area():
    with pytest.raises(ValueError):
        validate_corners([[0, 0], [1, 0], [2, 0], [3, 0]])

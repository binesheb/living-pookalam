import numpy as np

from app.core.color_calibration import ColorProfile, measure_surface_response


def test_surface_response_measures_black_white_and_uniformity():
    black = np.array([[10, 12, 14], [11, 12, 13]], dtype=np.float32)
    white = np.array([[210, 220, 230], [205, 215, 225]], dtype=np.float32)
    profile = measure_surface_response(black, white)
    assert np.allclose(profile.black_rgb, [10.5, 12.0, 13.5])
    assert 0 < profile.brightness_headroom < 1
    assert 0 < profile.uniformity <= 1


def test_surface_normalization_removes_black_floor():
    profile = measure_surface_response(
        np.array([10, 20, 30]), np.array([210, 220, 230])
    )
    normalized = profile.normalize_observed(np.array([110, 120, 130]))
    assert np.allclose(normalized, 0.5, atol=0.01)


def test_surface_compensation_is_bounded():
    profile = ColorProfile(
        surface=measure_surface_response(
            np.array([20, 20, 20]), np.array([120, 120, 120])
        )
    )
    result = profile.compensate_surface(np.array([255, 128, 0]))
    assert result.dtype == np.uint8
    assert np.all(result <= 255)
    assert np.all(result >= 0)

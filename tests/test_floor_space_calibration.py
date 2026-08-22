import numpy as np

from app.calibration.floor_space import build_floor_calibration, transform


def test_camera_and_projector_share_physical_floor_space():
    floor = np.float32([[0, 0], [2000, 0], [2000, 1500], [0, 1500]])
    camera = np.float32([[100, 80], [1100, 60], [1140, 900], [70, 930]])
    projector = np.float32([[192, 104], [1728, 86], [1760, 972], [160, 990]])

    result = build_floor_calibration(camera, projector, 2000, 1500)

    np.testing.assert_allclose(transform(camera, result.camera_to_floor), floor, atol=1e-2)
    np.testing.assert_allclose(transform(projector, result.projector_to_floor), floor, atol=1e-2)
    np.testing.assert_allclose(
        transform(camera, result.camera_to_projector), projector, atol=1e-2
    )
    assert result.camera_error_mm < 0.01
    assert result.projector_error_mm < 0.01
    assert result.max_error_mm < 0.01


def test_floor_point_can_be_projected_to_projector_and_back():
    camera = np.float32([[100, 80], [1100, 60], [1140, 900], [70, 930]])
    projector = np.float32([[192, 104], [1728, 86], [1760, 972], [160, 990]])
    result = build_floor_calibration(camera, projector, 2000, 1500)

    floor_point = np.float32([[1000, 750]])
    projector_point = transform(floor_point, result.floor_to_projector)
    round_trip = transform(projector_point, result.projector_to_floor)
    np.testing.assert_allclose(round_trip, floor_point, atol=1e-2)

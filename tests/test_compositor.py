import cv2
import numpy as np

from app.rendering.compositor import map_contour_to_projector, prepare_digital_layer


def circle_contour(w=100, h=100):
    return np.array([[[50, 10]], [[90, 50]], [[50, 90]], [[10, 50]]], dtype=np.float32)


def test_digital_contour_fit_is_deterministic():
    mapped = map_contour_to_projector(circle_contour(), (100, 100, 3), (1000, 800), None)
    assert mapped.shape == (4, 2)
    assert np.all(mapped[:, 0] >= 0) and np.all(mapped[:, 0] <= 1000)
    assert np.all(mapped[:, 1] >= 0) and np.all(mapped[:, 1] <= 800)


def test_digital_layer_has_transparent_rectangle_outside_pookalam():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[:, :] = (20, 40, 60)
    contour = circle_contour()
    prepared = prepare_digital_layer(image, contour, (1000, 800))
    assert prepared is not None
    layer, centre = prepared
    alpha = np.asarray(layer)[:, :, 3]
    assert alpha.max() == 255
    assert alpha.min() == 0


def test_physical_homography_maps_contour_to_projector():
    contour = circle_contour()
    H = np.float32([[2, 0, 100], [0, 2, 50], [0, 0, 1]])
    mapped = map_contour_to_projector(contour, (100, 100, 3), (400, 300), H)
    expected = cv2.perspectiveTransform(contour.reshape(-1, 1, 2), H).reshape(-1, 2)
    np.testing.assert_allclose(mapped, expected, atol=1e-5)

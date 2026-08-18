import cv2
import numpy as np

from app.calibration.staged import _detect_projector_rectangle, _white_model, _order_quad


def test_white_frame_detects_projector_rectangle():
    baseline = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = baseline.copy()
    cv2.fillConvexPoly(frame, np.array([[80, 60], [560, 85], [535, 410], [105, 390]], np.int32), (245, 245, 245))
    quad = _detect_projector_rectangle(frame, baseline)
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

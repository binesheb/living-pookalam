import cv2
import numpy as np

from app.vision.pattern_analyzer import analyze


def test_analyze_detects_colourful_pookalam_geometry():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(img, (320, 240), 150, (0, 120, 255), -1)
    cv2.circle(img, (320, 240), 95, (0, 255, 120), -1)
    result = analyze(img)
    assert result.confidence > 0.1
    assert result.contour is not None
    assert result.radius > 100
    assert len(result.rings) == 5
    assert result.edge_map.shape == img.shape[:2]


def test_empty_frame_is_rejected():
    try:
        analyze(np.empty((0, 0, 3), dtype=np.uint8))
    except ValueError:
        return
    assert False, "empty frame should raise ValueError"

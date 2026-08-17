import cv2
import numpy as np

from app.perception.pookalam_segmentation import PookalamSegmenter


def test_segmenter_detects_colored_irregular_region():
    image = np.zeros((500, 700, 3), dtype=np.uint8)
    # Simulated irregular floral region: orange + yellow lobes.
    pts = np.array([[210, 170], [360, 120], [510, 180], [555, 300],
                    [470, 390], [300, 410], [175, 315]], dtype=np.int32)
    cv2.fillPoly(image, [pts], (0, 150, 230))
    cv2.circle(image, (350, 260), 70, (0, 220, 255), -1)

    detection = PookalamSegmenter().detect(image)
    assert detection is not None
    assert detection.area > 10_000
    assert detection.mask.shape == image.shape[:2]
    assert 0.0 <= detection.confidence <= 1.0


def test_empty_floor_returns_none():
    image = np.zeros((500, 700, 3), dtype=np.uint8)
    assert PookalamSegmenter().detect(image) is None

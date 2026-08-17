"""Assisted segmentation of a physical Pookalam in a rectified floor view."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class PookalamDetection:
    """Detected floor-plane Pookalam geometry."""

    mask: np.ndarray
    contour: np.ndarray
    center: tuple[float, float]
    area: float
    confidence: float

    @property
    def bounding_box(self) -> tuple[int, int, int, int]:
        return tuple(int(v) for v in cv2.boundingRect(self.contour))


class PookalamSegmenter:
    """Find a likely floral region without assuming it is a perfect circle.

    The segmenter works on a rectified top-down image. It deliberately returns
    a contour/mask as the primary geometry; centre and area are derived values.
    This allows irregular, oval and asymmetric Pookalams to be supported.
    """

    def __init__(self, min_area_ratio: float = 0.02, max_area_ratio: float = 0.90):
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio

    def detect(self, floor_image: np.ndarray) -> PookalamDetection | None:
        if floor_image is None or floor_image.size == 0:
            return None
        h, w = floor_image.shape[:2]
        hsv = cv2.cvtColor(floor_image, cv2.COLOR_BGR2HSV)

        # Flowers/leaves generally provide more chroma than the surrounding
        # showroom floor. This is an initial detector, not the final AI model.
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        mask = ((saturation >= 55) & (value >= 45)).astype(np.uint8) * 255

        kernel = np.ones((11, 11), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.GaussianBlur(mask, (7, 7), 0)
        _, mask = cv2.threshold(mask, 80, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        image_area = float(w * h)
        candidates: list[tuple[float, np.ndarray]] = []

        for contour in contours:
            area = float(cv2.contourArea(contour))
            ratio = area / image_area
            if not self.min_area_ratio <= ratio <= self.max_area_ratio:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter <= 0:
                continue
            circularity = float(4.0 * np.pi * area / (perimeter * perimeter))

            # Pookalam layouts are usually compact. Circularity is only a
            # ranking signal, never a hard requirement.
            x, y, bw, bh = cv2.boundingRect(contour)
            compactness = area / max(1.0, float(bw * bh))
            score = area * (0.55 + 0.25 * min(1.0, circularity) + 0.20 * compactness)
            candidates.append((score, contour))

        if not candidates:
            return None

        _, contour = max(candidates, key=lambda item: item[0])
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(clean_mask, [contour], -1, 255, thickness=-1)

        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            return None
        center = (
            float(moments["m10"] / moments["m00"]),
            float(moments["m01"] / moments["m00"]),
        )

        area = float(cv2.contourArea(contour))
        confidence = self._confidence(contour, w, h)
        return PookalamDetection(clean_mask, contour, center, area, confidence)

    @staticmethod
    def _confidence(contour: np.ndarray, width: int, height: int) -> float:
        area = cv2.contourArea(contour)
        image_area = float(width * height)
        x, y, w, h = cv2.boundingRect(contour)
        box_area = max(1.0, float(w * h))
        fill = min(1.0, area / box_area)
        coverage = min(1.0, area / (image_area * 0.30))
        perimeter = cv2.arcLength(contour, True)
        circularity = 0.0 if perimeter == 0 else min(1.0, 4*np.pi*area/(perimeter*perimeter))
        # Keep irregular designs viable: circularity contributes only 20%.
        score = 0.50 * fill + 0.30 * coverage + 0.20 * circularity
        return float(max(0.0, min(1.0, score)))

"""Robust projector/camera calibration primitives for Live Pookalam."""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class CalibrationTarget:
    index: int
    projector_xy: tuple[float, float]
    color_bgr: tuple[int, int, int]
    name: str


@dataclass
class CalibrationObservation:
    index: int
    camera_xy: tuple[float, float]
    area: float
    circularity: float
    score: float


@dataclass
class CalibrationResult:
    homography: np.ndarray
    reprojection_error: float


class LiveCalibrator:
    """Four-target calibration using one uniquely colored target at a time."""

    COLORS = (
        (255, 0, 255),
        (255, 255, 0),
        (0, 255, 255),
        (0, 255, 0),
    )

    def __init__(self, projector_width: int, projector_height: int):
        self.width = int(projector_width)
        self.height = int(projector_height)
        self.margin_x = 0.12
        self.margin_y = 0.12
        self.targets = self._build_targets()
        self.observations: dict[int, CalibrationObservation] = {}
        self.active_index: Optional[int] = None
        self.candidate_history: list[tuple[float, float]] = []
        self.started_at = 0.0

    def _build_targets(self) -> tuple[CalibrationTarget, ...]:
        mx, my = self.margin_x, self.margin_y
        xy = (
            (self.width * mx, self.height * my),
            (self.width * (1 - mx), self.height * my),
            (self.width * (1 - mx), self.height * (1 - my)),
            (self.width * mx, self.height * (1 - my)),
        )
        names = ("TOP LEFT", "TOP RIGHT", "BOTTOM RIGHT", "BOTTOM LEFT")
        return tuple(
            CalibrationTarget(i, xy[i], self.COLORS[i], names[i]) for i in range(4)
        )

    def reset(self) -> None:
        self.observations.clear()
        self.active_index = 0
        self.candidate_history.clear()
        self.started_at = time.monotonic()

    def begin(self) -> None:
        self.reset()

    def active_target(self) -> Optional[CalibrationTarget]:
        if self.active_index is None or self.active_index >= len(self.targets):
            return None
        return self.targets[self.active_index]

    @staticmethod
    def _hsv_color_mask(hsv: np.ndarray, bgr: tuple[int, int, int]) -> np.ndarray:
        color = np.uint8([[bgr]])
        chsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)[0, 0]
        h = int(chsv[0])
        hue_delta = 12
        if h <= hue_delta:
            m1 = cv2.inRange(hsv, np.array([0, 150, 120]), np.array([h + hue_delta, 255, 255]))
            m2 = cv2.inRange(hsv, np.array([179 - (hue_delta - h), 150, 120]), np.array([179, 255, 255]))
            return cv2.bitwise_or(m1, m2)
        return cv2.inRange(hsv, np.array([h - hue_delta, 150, 120]), np.array([min(179, h + hue_delta), 255, 255]))

    def detect_active(self, frame_bgr: np.ndarray) -> Optional[CalibrationObservation]:
        target = self.active_target()
        if target is None or frame_bgr is None or frame_bgr.size == 0:
            return None
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = self._hsv_color_mask(hsv, target.color_bgr)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = mask.shape
        min_area = max(80.0, 0.0004 * w * h)
        candidates: list[CalibrationObservation] = []
        for c in contours:
            area = float(cv2.contourArea(c))
            if area < min_area:
                continue
            perimeter = float(cv2.arcLength(c, True))
            if perimeter <= 0:
                continue
            circularity = min(1.0, 4.0 * np.pi * area / (perimeter * perimeter))
            x, y, bw, bh = cv2.boundingRect(c)
            aspect = min(bw, bh) / max(bw, bh)
            if aspect < 0.55:
                continue
            moments = cv2.moments(c)
            if abs(moments["m00"]) < 1e-6:
                continue
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            score = 0.5 * min(1.0, area / (w * h * 0.04)) + 0.3 * circularity + 0.2 * aspect
            candidates.append(CalibrationObservation(target.index, (cx, cy), area, circularity, float(score)))
        if not candidates:
            return None
        return max(candidates, key=lambda o: o.score)

    def accept_observation(self, observation: CalibrationObservation, stable_frames: int = 8) -> bool:
        self.candidate_history.append(observation.camera_xy)
        if len(self.candidate_history) > stable_frames:
            self.candidate_history.pop(0)
        if len(self.candidate_history) < stable_frames:
            return False
        pts = np.asarray(self.candidate_history, dtype=np.float32)
        spread = float(np.max(np.ptp(pts, axis=0)))
        if spread > 8.0:
            return False
        mean_xy = tuple(np.mean(pts, axis=0).tolist())
        self.observations[observation.index] = CalibrationObservation(
            observation.index, mean_xy, observation.area, observation.circularity, observation.score
        )
        self.candidate_history.clear()
        self.active_index = observation.index + 1
        return True

    def finished(self) -> bool:
        return len(self.observations) == 4

    def build_result(self) -> Optional[CalibrationResult]:
        if not self.finished():
            return None
        cam = np.float32([self.observations[i].camera_xy for i in range(4)])
        proj = np.float32([self.targets[i].projector_xy for i in range(4)])
        H, _ = cv2.findHomography(cam, proj, method=0)
        if H is None:
            return None
        mapped = cv2.perspectiveTransform(cam.reshape(-1, 1, 2), H).reshape(-1, 2)
        error = float(np.mean(np.linalg.norm(mapped - proj, axis=1)))
        return CalibrationResult(H.astype(np.float32), error)

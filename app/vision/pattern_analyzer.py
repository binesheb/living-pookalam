"""Pattern analysis for Live Pookalam.

This module deliberately stays deterministic and lightweight for Windows field
machines. It extracts geometry that effects can safely use: boundary, centre,
radial rings, edges, dominant colours and a confidence score. It does not try
to identify every flower semantically; that can be added later without changing
the effect API.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import cv2
import numpy as np


@dataclass
class PatternAnalysis:
    width: int
    height: int
    confidence: float
    centre: tuple[float, float]
    radius: float
    contour: np.ndarray | None
    edge_map: np.ndarray
    mask: np.ndarray
    rings: tuple[float, ...]
    dominant_colours: tuple[tuple[int, int, int], ...]
    symmetry_order: int

    def summary(self) -> dict:
        data = asdict(self)
        data.pop("contour", None)
        data.pop("edge_map", None)
        data.pop("mask", None)
        return data


def _largest_colourful_region(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray | None, float]:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    mask = ((sat >= 45) & (val >= 45)).astype(np.uint8) * 255
    k = max(3, int(round(min(frame.shape[:2]) / 90)) | 1)
    kernel = np.ones((k, k), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape
    candidates = [c for c in contours if 0.008 * w * h < cv2.contourArea(c) < 0.90 * w * h]
    if not candidates:
        return mask, None, 0.0
    contour = max(candidates, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    x, y, bw, bh = cv2.boundingRect(contour)
    fill = area / max(1.0, bw * bh)
    coverage = min(1.0, area / max(1.0, w * h * 0.30))
    perimeter = cv2.arcLength(contour, True)
    circularity = 0.0 if perimeter == 0 else min(1.0, 4 * np.pi * area / (perimeter * perimeter))
    confidence = float(np.clip(0.45 * fill + 0.35 * coverage + 0.20 * circularity, 0, 1))
    return mask, contour, confidence


def _dominant_colours(frame: np.ndarray, mask: np.ndarray, count: int = 6) -> tuple[tuple[int, int, int], ...]:
    pixels = frame[mask > 0]
    if len(pixels) < 50:
        return ()
    sample = pixels[::max(1, len(pixels) // 3000)].astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    k = min(count, max(1, len(sample)))
    _, _, centres = cv2.kmeans(sample, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    # Return RGB-like values for UI/effect metadata, while the source is BGR.
    return tuple(tuple(int(v) for v in c[::-1]) for c in centres)


def _symmetry_order(mask: np.ndarray, centre: tuple[float, float]) -> int:
    # Cheap radial symmetry estimate. Restrict to common Pookalam orders.
    h, w = mask.shape
    cx, cy = centre
    best_order, best_score = 1, -1.0
    base = mask.astype(np.float32) / 255.0
    for order in (4, 6, 8, 10, 12):
        score = 0.0
        for i in range(order):
            angle = 360.0 / order * i
            mat = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
            rotated = cv2.warpAffine(base, mat, (w, h), flags=cv2.INTER_NEAREST)
            score += float(np.mean(1.0 - np.abs(base - rotated)))
        score /= order
        if score > best_score:
            best_score, best_order = score, order
    return best_order


def analyze(frame: np.ndarray) -> PatternAnalysis:
    """Analyze a camera frame or uploaded Pookalam image."""
    if frame is None or frame.size == 0:
        raise ValueError("frame is empty")
    h, w = frame.shape[:2]
    mask, contour, confidence = _largest_colourful_region(frame)
    if contour is None:
        empty = np.zeros((h, w), np.uint8)
        return PatternAnalysis(w, h, 0.0, (w / 2, h / 2), 0.0, None, empty, mask, (), (), 1)

    moments = cv2.moments(contour)
    if moments["m00"]:
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
    else:
        x, y, bw, bh = cv2.boundingRect(contour)
        cx, cy = x + bw / 2, y + bh / 2
    (_, _), radius = cv2.minEnclosingCircle(contour)

    edge_map = cv2.Canny(mask, 60, 160)
    # A small contour approximation gives effects a stable path rather than thousands of noisy points.
    epsilon = max(1.0, 0.0025 * cv2.arcLength(contour, True))
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    rings = tuple(float(radius * f) for f in (0.22, 0.38, 0.54, 0.70, 0.86))
    colours = _dominant_colours(frame, mask)
    symmetry = _symmetry_order(mask, (cx, cy))
    return PatternAnalysis(w, h, confidence, (float(cx), float(cy)), float(radius), simplified, edge_map, mask, rings, colours, symmetry)

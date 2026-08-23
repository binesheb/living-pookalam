"""Webcam discovery and selection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CameraInfo:
    index: int
    width: int
    height: int

    def as_dict(self) -> dict[str, Any]:
        return {"index": self.index, "width": self.width, "height": self.height,
                "label": f"Camera {self.index} ({self.width}x{self.height})"}


def _cv2():
    import cv2
    return cv2


def discover_cameras(max_index: int = 10) -> list[dict[str, Any]]:
    """Probe available OpenCV camera indexes without keeping devices open."""
    cv2 = _cv2()
    cameras: list[dict[str, Any]] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                continue
            ok, _ = capture.read()
            if not ok:
                continue
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append(CameraInfo(index, width, height).as_dict())
        finally:
            capture.release()
    return cameras


def test_camera(index: int) -> dict[str, Any]:
    """Open a selected camera briefly and return its availability."""
    cv2 = _cv2()
    capture = cv2.VideoCapture(index)
    try:
        if not capture.isOpened():
            return {"ok": False, "index": index, "error": "Unable to open camera"}
        ok, frame = capture.read()
        if not ok or frame is None:
            return {"ok": False, "index": index, "error": "Unable to read frame"}
        height, width = frame.shape[:2]
        return {"ok": True, "index": index, "width": int(width), "height": int(height)}
    finally:
        capture.release()

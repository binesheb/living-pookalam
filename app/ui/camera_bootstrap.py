"""Non-blocking camera bootstrap for the Windows field UI.

OpenCV camera discovery can block for several seconds on some Windows/USB
configurations. The UI must never wait for hardware discovery before painting.
This module replaces cv2.VideoCapture with a small compatibility wrapper whose
real device is opened on a background thread.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import cv2

_RealVideoCapture = cv2.VideoCapture


class AsyncVideoCapture:
    def __init__(self, index: int = 0, api_preference: int = cv2.CAP_ANY, *args: Any, **kwargs: Any) -> None:
        self.index = index
        self.api_preference = api_preference
        self.args = args
        self.kwargs = kwargs
        self._cap = None
        self._lock = threading.Lock()
        self._opened = False
        self._opening = True
        self._closed = False
        self._properties: dict[int, float] = {}
        self._thread = threading.Thread(target=self._open, name="live-pookalam-camera", daemon=True)
        self._thread.start()

    def _open(self) -> None:
        try:
            cap = _RealVideoCapture(self.index, self.api_preference, *self.args, **self.kwargs)
            with self._lock:
                if self._closed:
                    cap.release()
                    return
                self._cap = cap
                self._opened = bool(cap.isOpened())
                for prop, value in self._properties.items():
                    try:
                        cap.set(prop, value)
                    except Exception:
                        pass
        except Exception:
            with self._lock:
                self._cap = None
                self._opened = False
        finally:
            self._opening = False

    def isOpened(self) -> bool:
        with self._lock:
            return self._opened and self._cap is not None and self._cap.isOpened()

    def read(self):
        with self._lock:
            cap = self._cap
        if cap is None:
            return False, None
        try:
            return cap.read()
        except Exception:
            return False, None

    def set(self, prop_id: int, value: float) -> bool:
        self._properties[prop_id] = value
        with self._lock:
            cap = self._cap
        if cap is None:
            return True
        try:
            return bool(cap.set(prop_id, value))
        except Exception:
            return False

    def get(self, prop_id: int) -> float:
        with self._lock:
            cap = self._cap
        if cap is None:
            return 0.0
        try:
            return float(cap.get(prop_id))
        except Exception:
            return 0.0

    def release(self) -> None:
        with self._lock:
            self._closed = True
            cap = self._cap
            self._cap = None
            self._opened = False
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    @property
    def opening(self) -> bool:
        return self._opening


def install_nonblocking_camera() -> None:
    """Install the wrapper before any field UI module constructs a camera."""
    if getattr(cv2, "_live_pookalam_async_camera", False):
        return
    cv2.VideoCapture = AsyncVideoCapture  # type: ignore[assignment]
    cv2._live_pookalam_async_camera = True

"""White-field + black-dot geometry calibration stage.

The projector first fills its complete field with white. Once the camera sees
that illuminated quadrilateral, four large black targets are placed inside the
white field. Black-on-white is deliberately used for geometry acquisition: it
does not depend on projector colour reproduction or camera colour balance.
Colour calibration can then run as a separate photometric stage.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from app.calibration.staged import _detect_projector_rectangle


MARGIN = 0.12
DOT_RADIUS_FRACTION = 0.065


def _white_field(self):
    self.clear()
    self.canvas.configure(bg="white")
    self.canvas.create_rectangle(0, 0, self.w, self.h, fill="white", outline="white")
    self.canvas.create_text(
        self.w / 2, self.h * 0.5,
        text="CALIBRATING PROJECTOR SPACE",
        fill="#111111", font=("Segoe UI", 26, "bold"),
    )
    self.canvas.create_text(
        self.w / 2, self.h * 0.55,
        text="FULL WHITE FIELD • CAMERA OBSERVATION",
        fill="#333333", font=("Segoe UI", 14, "bold"),
    )


def _black_dot(self, index):
    self.clear()
    self.canvas.configure(bg="white")
    self.canvas.create_rectangle(0, 0, self.w, self.h, fill="white", outline="white")

    points = [
        (self.w * MARGIN, self.h * MARGIN),
        (self.w * (1 - MARGIN), self.h * MARGIN),
        (self.w * (1 - MARGIN), self.h * (1 - MARGIN)),
        (self.w * MARGIN, self.h * (1 - MARGIN)),
    ]
    x, y = points[index]
    r = min(self.w, self.h) * DOT_RADIUS_FRACTION

    self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="black", outline="black")
    self.canvas.create_oval(x-r * 0.18, y-r * 0.18,
                            x+r * 0.18, y+r * 0.18,
                            fill="white", outline="white")
    arm = r * 1.45
    for a, b in [((x-arm, y), (x+r, y)), ((x-r, y), (x+arm, y)),
                 ((x, y-arm), (x, y+r)), ((x, y-r), (x, y+arm))]:
        self.canvas.create_line(*a, *b, fill="black", width=5)

    self.canvas.create_text(
        self.w / 2, self.h * 0.50,
        text=f"GEOMETRY • TARGET {index + 1}",
        fill="black", font=("Segoe UI", 26, "bold"),
    )
    self.canvas.create_text(
        self.w / 2, self.h * 0.55,
        text="BLACK ON WHITE • ACQUIRE → PINPOINT → LOCK",
        fill="#222222", font=("Segoe UI", 14, "bold"),
    )


def _detect_black_dot(frame: np.ndarray, expected_xy, radius: int):
    """Detect a large dark target inside a predicted camera-space ROI."""
    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    cx, cy = int(expected_xy[0]), int(expected_xy[1])
    r = max(30, int(radius))
    x0, x1 = max(0, cx-r), min(w, cx+r)
    y0, y1 = max(0, cy-r), min(h, cy+r)
    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    threshold = int(np.clip(np.percentile(gray, 12) + 12, 35, 120))
    mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)[1]
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    expected_area = np.pi * (r * 0.28) ** 2
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < max(40.0, expected_area * 0.15):
            continue
        m = cv2.moments(c)
        if not m["m00"]:
            continue
        px = x0 + m["m10"] / m["m00"]
        py = y0 + m["m01"] / m["m00"]
        distance = float(np.hypot(px - cx, py - cy))
        if distance <= r * 0.85:
            candidates.append((distance, area, (px, py)))

    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], -item[1]))[2]


def _projector_points(proj):
    return np.float32([
        (proj.w * MARGIN, proj.h * MARGIN),
        (proj.w * (1 - MARGIN), proj.h * MARGIN),
        (proj.w * (1 - MARGIN), proj.h * (1 - MARGIN)),
        (proj.w * MARGIN, proj.h * (1 - MARGIN)),
    ])


def _install():
    from app.ui.field_ui import FieldConsole, ProjectionWindow, save_state

    ProjectionWindow.white = _white_field
    ProjectionWindow.target = _black_dot

    def start_calibration(self):
        self.open_projector()
        self.stop_show()
        self.open_projector()
        self.calib_index = -2
        self.calib_history = []
        self.calib_points = []
        self.calib_started = time.perf_counter()
        self.calib_baseline = None if self.frame is None else self.frame.copy()
        self.calib_stage = "WHITE_FIELD"
        self.proj.white()
        self.calib_status.set("CALIBRATING • WHITE PROJECTOR FIELD")
        self.calib_detail.set("Projecting full white. Finding the complete illuminated projector space…")
        for i, (var, lab) in enumerate(self.calib_labels):
            var.set(f"{i + 1}   GEOMETRY DOT   WAITING")
            lab.configure(fg="#9c95aa")
        self.calib_progress.set("PROJECTOR SPACE")
        self.calib_error.set("Reprojection error: PENDING")
        self.projection_quad = None
        self.H = None

    def detect_target(self, frame, index):
        if getattr(self, "projection_quad", None) is None or self.H is None:
            return None
        p = _projector_points(self.proj)[index]
        try:
            inv_h = np.linalg.inv(self.H)
            expected = cv2.perspectiveTransform(p.reshape(1, 1, 2), inv_h).reshape(2)
        except np.linalg.LinAlgError:
            return None
        return _detect_black_dot(
            frame,
            expected,
            max(70, int(min(frame.shape[:2]) * 0.20)),
        )

    def calibration_tick(self):
        if self.calib_index == -1 or self.frame is None:
            return

        if self.calib_index == -2:
            if time.perf_counter() - self.calib_started < 1.2:
                self.calib_detail.set("WHITE FIELD • allowing camera/projector exposure to settle…")
                return
            quad = _detect_projector_rectangle(self.frame, self.calib_baseline)
            if quad is None:
                self.calib_detail.set("WHITE FIELD • searching for the illuminated projector rectangle…")
                return
            self.projection_quad = quad
            proj_pts = np.float32([(0, 0), (self.proj.w, 0),
                                   (self.proj.w, self.proj.h), (0, self.proj.h)])
            H, _ = cv2.findHomography(quad, proj_pts, 0)
            if H is None:
                self.calib_detail.set("WHITE FIELD • rectangle found, but initial geometry transform failed")
                return
            self.H = H.astype(np.float32)
            self.state["homography"] = self.H.tolist()
            self.state["projector_width"] = self.proj.w
            self.state["projector_height"] = self.proj.h
            self.state["surface_rectangle_camera"] = quad.tolist()
            self.state["geometry_from_white"] = True
            self.state["calibration_stage"] = "BLACK_DOTS"
            self.calib_index = 0
            self.calib_history = []
            self.proj.target(0)
            self.calib_labels[0][0].set("1   GEOMETRY DOT   ACTIVE")
            self.calib_labels[0][1].configure(fg="#8b35ff")
            self.calib_status.set("CALIBRATING • BLACK GEOMETRY TARGETS")
            self.calib_detail.set("White field locked. Acquiring black targets inside the projected rectangle…")
            self.calib_progress.set("BLACK DOT 1 / 4")
            return

        p = self.detect_target(self.frame, self.calib_index)
        if p is None:
            self.calib_history = []
            self.calib_detail.set(
                f"Geometry target {self.calib_index + 1}: acquiring black dot inside white field…"
            )
            return

        self.calib_history.append(p)
        if len(self.calib_history) > 8:
            self.calib_history.pop(0)
        if len(self.calib_history) < 8:
            self.calib_detail.set(
                f"Geometry target {self.calib_index + 1}: pinpointing centre {len(self.calib_history)}/8…"
            )
            return

        arr = np.asarray(self.calib_history, np.float32)
        mean = arr.mean(axis=0)
        jitter = float(np.max(np.linalg.norm(arr - mean, axis=1)))
        self.calib_detail.set(
            f"Geometry target {self.calib_index + 1}: centre locked • jitter {jitter:.1f}px"
        )
        if jitter > 12:
            return

        idx = self.calib_index
        self.calib_points.append(tuple(mean))
        self.calib_labels[idx][0].set(f"{idx + 1}   GEOMETRY DOT   LOCKED")
        self.calib_labels[idx][1].configure(fg="#32e875")
        self.calib_history = []

        if idx < 3:
            self.calib_index += 1
            self.proj.target(self.calib_index)
            self.calib_labels[self.calib_index][0].set(
                f"{self.calib_index + 1}   GEOMETRY DOT   ACTIVE"
            )
            self.calib_labels[self.calib_index][1].configure(fg="#8b35ff")
            self.calib_progress.set(f"BLACK DOT {self.calib_index + 1} / 4")
            return

        camera_pts = np.asarray(self.calib_points, np.float32)
        projector_pts = _projector_points(self.proj)
        refined, _ = cv2.findHomography(camera_pts, projector_pts, cv2.RANSAC, 4.0)
        if refined is not None:
            self.H = refined.astype(np.float32)
            self.state["homography"] = self.H.tolist()

        self.state["calibration_stage"] = "COLOUR_CALIBRATION_PENDING"
        self.state["geometry_calibration_valid"] = True
        self.state["surface_calibration_valid"] = True
        self.state["reprojection_error"] = None
        self.state["reprojection_status"] = "PENDING"
        save_state(self.state)

        self.calib_error.set("Reprojection error: PENDING")
        self.calib_progress.set("GEOMETRY LOCKED")
        self.calib_status.set("GEOMETRY CALIBRATION COMPLETE")
        self.calib_detail.set(
            "Black geometry targets locked. Colour calibration can now run independently without affecting geometry."
        )
        self.calib_index = -1
        self.proj.black()

    # Patch both the legacy base class and the actual production subclass.
    # ProductFieldConsole defines its own calibration state machine, so patching
    # only FieldConsole would leave the production GUI on the old colour workflow.
    FieldConsole.start_calibration = start_calibration
    FieldConsole.detect_target = detect_target
    FieldConsole.calibration_tick = calibration_tick

    try:
        from app.ui.field_product import ProductFieldConsole
        ProductFieldConsole.start_calibration = start_calibration
        ProductFieldConsole.detect_target = detect_target
        ProductFieldConsole.calibration_tick = calibration_tick
    except ImportError:
        # Safe for direct module imports before the production console is loaded.
        pass


_install()

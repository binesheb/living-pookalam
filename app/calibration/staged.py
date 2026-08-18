"""Staged field calibration for Live Pookalam.

Physical calibration is deliberately separated into reliable stages:
1. full-white projection -> camera/surface baseline + projector quadrilateral
2. large black dots on that white field -> geometry points
3. geometry/reprojection validation
4. colour calibration can run independently after geometry is locked

The first geometry stage intentionally does not depend on projector colour
reproduction. This is important for side-mounted cameras where cyan/yellow may
clip toward white in the camera image.
"""
from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np


def _projector_white(self):
    self.clear()
    self.canvas.configure(bg="white")
    self.canvas.create_rectangle(0, 0, self.w, self.h, fill="white", outline="white")


def _projector_black(self):
    self.clear()
    self.canvas.configure(bg="black")


def _target(self, index):
    """Project a large black acquisition dot on the white projector field."""
    self.clear()
    self.canvas.configure(bg="white")
    margin = 0.12
    pts = [(self.w * margin, self.h * margin),
           (self.w * (1 - margin), self.h * margin),
           (self.w * (1 - margin), self.h * (1 - margin)),
           (self.w * margin, self.h * (1 - margin))]
    x, y = pts[index]
    r = min(self.w, self.h) * 0.075
    inner = r * 0.34
    self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="black", outline="white", width=6)
    self.canvas.create_oval(x-inner, y-inner, x+inner, y+inner,
                            fill="white", outline="black", width=3)
    self.canvas.create_oval(x-inner*0.25, y-inner*0.25,
                            x+inner*0.25, y+inner*0.25,
                            fill="black", outline="black")
    arm = r * 1.25
    for a, b in [((x-arm, y), (x-r*1.02, y)),
                 ((x+r*1.02, y), (x+arm, y)),
                 ((x, y-arm), (x, y-r*1.02)),
                 ((x, y+r*1.02), (x, y+arm))]:
        self.canvas.create_line(*a, *b, fill="black", width=4)
    self.canvas.create_text(self.w/2, self.h*0.50,
                            text=f"GEOMETRY  •  TARGET {index+1}",
                            fill="#111111", font=("Segoe UI", 26, "bold"))
    self.canvas.create_text(self.w/2, self.h*0.55,
                            text="BLACK DOT • ACQUIRE → PINPOINT CENTRE",
                            fill="#333333", font=("Segoe UI", 14, "bold"))


def _detect_projector_rectangle(frame: np.ndarray, baseline: Optional[np.ndarray]):
    """Return a camera-space quadrilateral for the illuminated projector area."""
    if frame is None or frame.size == 0:
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if baseline is not None and baseline.shape == frame.shape:
        base = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)
        score = cv2.GaussianBlur(cv2.absdiff(gray, base), (0, 0), 5)
    else:
        score = cv2.GaussianBlur(gray, (0, 0), 5)

    score = np.asarray(score, dtype=np.uint8)
    peak = int(score.max())
    if peak <= 4:
        return None

    positive = score[score > 4]
    percentile_threshold = float(np.percentile(positive, 65)) if positive.size else float(peak)
    threshold = int(np.clip(min(percentile_threshold, peak * 0.65), 8, 245))
    mask = cv2.threshold(score, threshold, 255, cv2.THRESH_BINARY)[1]

    kernel = np.ones((15, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    h, w = gray.shape
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.12 * w * h:
            continue
        peri = cv2.arcLength(c, True)
        poly = cv2.approxPolyDP(c, 0.025 * peri, True)
        if len(poly) < 4:
            hull = cv2.convexHull(c)
            poly = cv2.approxPolyDP(hull, 0.04 * cv2.arcLength(hull, True), True)
        candidates.append((area, poly.reshape(-1, 2).astype(np.float32)))

    if not candidates:
        return None

    _, pts = max(candidates, key=lambda item: item[0])
    if len(pts) < 4:
        return None
    rect = cv2.minAreaRect(pts.reshape(-1, 1, 2))
    return _order_quad(cv2.boxPoints(rect).astype(np.float32))


def _order_quad(pts):
    s = pts.sum(axis=1)
    d = pts[:, 0] - pts[:, 1]
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)],
                       pts[np.argmax(s)], pts[np.argmax(d)]])


def _white_model(frame, quad):
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
    mask = cv2.erode(mask, np.ones((31, 31), np.uint8))
    pixels = frame[mask > 0].astype(np.float32)
    if len(pixels) < 500:
        return None
    observed_bgr = np.median(pixels, axis=0)
    target = float(np.mean(observed_bgr))
    gains = np.clip(target / np.maximum(observed_bgr, 1.0), 0.35, 3.0)
    return {
        "observed_white_bgr": observed_bgr.tolist(),
        "white_balance_gains_bgr": gains.tolist(),
        "brightness": float(np.mean(observed_bgr)),
        "uniformity": float(np.clip(1.0 - np.std(pixels.mean(axis=1)) / max(1.0, target), 0.0, 1.0)),
    }


def _detect_black_dot(frame: np.ndarray, expected_xy, radius: int):
    """Detect the dark circular geometry target inside a known white field."""
    if frame is None or frame.size == 0:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    cx, cy = int(expected_xy[0]), int(expected_xy[1])
    r = max(24, int(radius))
    x0, x1 = max(0, cx-r), min(w, cx+r)
    y0, y1 = max(0, cy-r), min(h, cy+r)
    roi = gray[y0:y1, x0:x1]
    if roi.size == 0:
        return None

    # Dark-on-white is intentionally simple and robust against colour clipping.
    local_white = float(np.percentile(roi, 75))
    threshold = int(np.clip(local_white * 0.45, 25, 120))
    mask = cv2.threshold(roi, threshold, 255, cv2.THRESH_BINARY_INV)[1]
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    best = None
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.001 * roi.shape[0] * roi.shape[1]:
            continue
        peri = cv2.arcLength(c, True)
        circularity = 4.0 * np.pi * area / max(peri * peri, 1.0)
        if circularity < 0.35:
            continue
        m = cv2.moments(c)
        if not m["m00"]:
            continue
        px = x0 + m["m10"] / m["m00"]
        py = y0 + m["m01"] / m["m00"]
        distance = float(np.hypot(px-cx, py-cy))
        score = area * max(0.05, circularity) / (1.0 + distance)
        if best is None or score > best[0]:
            best = (score, px, py)
    return None if best is None else (float(best[1]), float(best[2]))


def _draw_crosshair(frame, point, colour, label, radius=24):
    """Draw a highly visible calibration marker in camera coordinates."""
    x, y = int(round(point[0])), int(round(point[1]))
    cv2.circle(frame, (x, y), radius, colour, 3, cv2.LINE_AA)
    cv2.line(frame, (x-radius-12, y), (x+radius+12, y), colour, 2, cv2.LINE_AA)
    cv2.line(frame, (x, y-radius-12), (x, y+radius+12), colour, 2, cv2.LINE_AA)
    cv2.circle(frame, (x, y), 5, colour, -1, cv2.LINE_AA)
    cv2.putText(frame, label, (x+radius+10, y-8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour, 2, cv2.LINE_AA)


def _camera_calibration_overlay(self, frame):
    """Overlay expected, detected and locked calibration points on camera feed."""
    if frame is None:
        return frame

    out = frame.copy()
    quad = getattr(self, "projection_quad", None)
    if quad is not None:
        q = np.int32(np.round(quad))
        cv2.polylines(out, [q], True, (0, 255, 255), 3, cv2.LINE_AA)
        for i, p in enumerate(q):
            cv2.circle(out, tuple(p), 7, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.putText(out, f"SURFACE {i+1}", (int(p[0])+10, int(p[1])-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)

    # The yellow cross is where the current homography predicts the projector
    # target should appear in the camera. Green is where the detector actually
    # found the black target. The difference is immediately visible.
    if self.H is not None and self.proj is not None:
        margin = 0.12
        projector_points = np.float32([
            [self.proj.w*margin, self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*(1-margin)],
            [self.proj.w*margin, self.proj.h*(1-margin)],
        ])
        try:
            expected_camera = cv2.perspectiveTransform(
                projector_points.reshape(-1, 1, 2), np.linalg.inv(self.H)
            ).reshape(-1, 2)
        except np.linalg.LinAlgError:
            expected_camera = None

        if expected_camera is not None:
            for i, p in enumerate(expected_camera):
                _draw_crosshair(out, p, (0, 215, 255), f"P{i+1} EXPECTED", radius=18)

    locked = list(getattr(self, "calib_points", []) or [])
    for i, p in enumerate(locked):
        _draw_crosshair(out, p, (0, 255, 0), f"P{i+1} LOCKED  {p[0]:.0f},{p[1]:.0f}", radius=28)

    # While a target is active, show the live detector result even before the
    # eight-frame lock completes. This makes it obvious what the algorithm sees.
    idx = getattr(self, "calib_index", -1)
    if idx >= 0 and idx < 4:
        detected = self.detect_target(frame, idx)
        if detected is not None:
            _draw_crosshair(out, detected, (255, 80, 255),
                            f"P{idx+1} DETECTED  {detected[0]:.0f},{detected[1]:.0f}", radius=34)
            if self.H is not None and expected_camera is not None:
                error = float(np.linalg.norm(np.asarray(detected) - expected_camera[idx]))
                cv2.putText(out, f"TARGET ERROR: {error:.1f}px",
                            (30, out.shape[0]-28), cv2.FONT_HERSHEY_SIMPLEX,
                            0.75, (255, 80, 255), 2, cv2.LINE_AA)

    status = "GEOMETRY OVERLAY"
    if len(locked) == 4 and idx == -1:
        status = "GEOMETRY LOCKED • 4/4 POINTS"
    elif idx >= 0:
        status = f"LIVE DETECTION • TARGET {idx+1}/4"
    elif getattr(self, "calib_index", -1) == -2:
        status = "WHITE FIELD • PROJECTOR SPACE"

    cv2.rectangle(out, (18, 14), (430, 55), (0, 0, 0), -1)
    cv2.putText(out, status, (30, 43), cv2.FONT_HERSHEY_SIMPLEX,
                0.72, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def _install():
    from app.ui.field_ui import FieldConsole, ProjectionWindow

    ProjectionWindow.white = _projector_white
    ProjectionWindow.black = _projector_black
    ProjectionWindow.target = _target

    def start_calibration(self):
        self.open_projector()
        self.stop_show()
        self.open_projector()
        self.calib_index = -2
        self.calib_history = []
        self.calib_points = []
        self.calib_color_samples = []
        self.calib_started = time.perf_counter()
        self.calib_baseline = None if self.frame is None else self.frame.copy()
        self.calib_stage = "WHITE"
        self.proj.white()
        self.calib_status.set("CALIBRATING • WHITE FIELD")
        self.calib_detail.set("Projecting full white. Finding the complete projector area and measuring camera response…")
        for i, (var, lab) in enumerate(self.calib_labels):
            var.set(f"{i+1}   GEOMETRY DOT   WAITING")
            lab.configure(fg="#9c95aa")
        self.calib_progress.set("WHITE FIELD")
        self.calib_error.set("Reprojection error: PENDING")

    def detect_target(self, frame, index):
        if getattr(self, "projection_quad", None) is None or self.H is None:
            return None
        margin = 0.12
        projector_points = np.float32([
            [self.proj.w*margin, self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*(1-margin)],
            [self.proj.w*margin, self.proj.h*(1-margin)],
        ])
        camera_points = cv2.perspectiveTransform(
            projector_points.reshape(-1, 1, 2), np.linalg.inv(self.H)
        ).reshape(-1, 2)
        expected = camera_points[index]
        return _detect_black_dot(frame, expected, max(50, int(min(frame.shape[:2]) * 0.16)))

    def calibration_tick(self):
        if self.calib_index == -1 or self.frame is None:
            return

        if self.calib_index == -2:
            if time.perf_counter() - self.calib_started < 1.2:
                self.calib_detail.set("WHITE • allowing projector/camera exposure to settle…")
                return
            quad = _detect_projector_rectangle(self.frame, self.calib_baseline)
            if quad is None:
                self.calib_detail.set("WHITE • searching for the complete bright projector rectangle…")
                return
            self.projection_quad = quad
            model = _white_model(self.frame, quad)
            if model is None:
                self.calib_detail.set("WHITE • rectangle found; measuring surface response…")
                return
            self.state["colour_profile"] = model
            proj_pts = np.float32([(0,0),(self.proj.w,0),(self.proj.w,self.proj.h),(0,self.proj.h)])
            H, _ = cv2.findHomography(quad, proj_pts, 0)
            if H is None:
                self.calib_detail.set("WHITE • rectangle found but geometry transform failed")
                return
            self.H = H.astype(np.float32)
            self.state["homography"] = self.H.tolist()
            self.state["projector_width"] = self.proj.w
            self.state["projector_height"] = self.proj.h
            self.state["surface_rectangle_camera"] = quad.tolist()
            self.state["calibration_stage"] = "BLACK_GEOMETRY"
            self.proj.target(0)
            self.calib_index = 0
            self.calib_history = []
            self.calib_labels[0][0].set("1   BLACK DOT   ACTIVE")
            self.calib_labels[0][1].configure(fg="#32e875")
            self.calib_status.set("CALIBRATING • BLACK GEOMETRY")
            self.calib_detail.set("White field locked. Acquiring black geometry dot 1…")
            self.calib_progress.set("GEOMETRY 0 / 4")
            return

        p = self.detect_target(self.frame, self.calib_index)
        if p is None:
            self.calib_history = []
            self.calib_detail.set(f"Geometry dot {self.calib_index+1}: acquiring dark circle in predicted region…")
            return
        self.calib_history.append(p)
        if len(self.calib_history) > 8:
            self.calib_history.pop(0)
        if len(self.calib_history) < 8:
            self.calib_detail.set(f"Geometry dot {self.calib_index+1}: acquired • pinpointing centre {len(self.calib_history)}/8")
            return
        arr = np.array(self.calib_history, np.float32)
        mean = arr.mean(0)
        spread = float(np.max(np.linalg.norm(arr-mean, axis=1)))
        self.calib_detail.set(f"Geometry dot {self.calib_index+1}: centre locked • jitter {spread:.1f}px")
        if spread > 12:
            return

        idx = self.calib_index
        self.calib_points.append(tuple(mean))
        self.calib_labels[idx][0].set(f"{idx+1}   BLACK DOT   LOCKED")
        self.calib_labels[idx][1].configure(fg="#32e875")
        self.calib_progress.set(f"GEOMETRY {idx+1} / 4")
        self.calib_history = []
        if idx < 3:
            self.calib_index += 1
            self.proj.target(self.calib_index)
            self.calib_labels[self.calib_index][0].set(f"{self.calib_index+1}   BLACK DOT   ACTIVE")
            self.calib_labels[self.calib_index][1].configure(fg="#32e875")
            return

        # The four black dots are observed in camera space. Their known projector
        # coordinates refine the initial white-field homography.
        observed = np.float32(self.calib_points)
        margin = 0.12
        expected = np.float32([
            [self.proj.w*margin, self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*margin],
            [self.proj.w*(1-margin), self.proj.h*(1-margin)],
            [self.proj.w*margin, self.proj.h*(1-margin)],
        ])
        H, _ = cv2.findHomography(observed, expected, 0)
        if H is None:
            self.calib_detail.set("BLACK GEOMETRY • refinement failed; retrying calibration…")
            self.calib_index = 0
            self.calib_points = []
            self.proj.target(0)
            return
        self.H = H.astype(np.float32)
        self.state["homography"] = self.H.tolist()
        self.state["geometry_points_camera"] = observed.tolist()
        self.state["geometry_points_projector"] = expected.tolist()
        self.state["calibration_stage"] = "REPROJECTION"
        self.state["geometry_from_white"] = True
        self.state["surface_calibration_valid"] = True
        self.state["reprojection_error"] = None
        self.state["reprojection_status"] = "PENDING"
        self.state["colour_calibration_pending"] = True
        from app.ui.field_ui import save_state
        save_state(self.state)
        self.calib_error.set("Reprojection error: PENDING")
        self.calib_status.set("GEOMETRY CALIBRATION COMPLETE")
        self.calib_detail.set("White field + black geometry locked. Ready for independent reprojection and colour calibration.")
        self.calib_progress.set("GEOMETRY COMPLETE")
        self.calib_index = -1
        self.proj.black()

    # Keep the existing production camera loop intact, then add a visualization
    # pass. This is deliberately wrapped here so ProductFieldConsole and other
    # subclasses inherit the overlay without replacing their own tick methods.
    original_tick = FieldConsole.tick

    def tick_with_calibration_overlay(self):
        original_tick(self)
        if self.frame is None or not hasattr(self, "calib_preview"):
            return
        try:
            overlay = _camera_calibration_overlay(self, self.frame)
            image = cv2.resize(overlay, (900, 506), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            from PIL import Image, ImageTk
            self.calib_overlay_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.calib_preview.configure(image=self.calib_overlay_photo)
        except Exception:
            # Visualization must never break the calibration loop.
            pass

    FieldConsole.start_calibration = start_calibration
    FieldConsole.detect_target = detect_target
    FieldConsole.calibration_tick = calibration_tick
    FieldConsole.tick = tick_with_calibration_overlay


_install()

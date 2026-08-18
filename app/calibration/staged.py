"""Staged field calibration for Live Pookalam.

The physical sequence is deliberately:
1. white projection -> camera/surface baseline + projected rectangle
2. four large colour targets -> learn observed camera colours and refine centres
3. geometry/reprojection -> only after the colour model is known

This module patches the existing Tk field console at startup so the operator gets
one automated workflow without replacing the established renderer.
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
    self.clear()
    self.canvas.configure(bg="black")
    margin = 0.12
    pts = [(self.w * margin, self.h * margin),
           (self.w * (1 - margin), self.h * margin),
           (self.w * (1 - margin), self.h * (1 - margin)),
           (self.w * margin, self.h * (1 - margin))]
    x, y = pts[index]
    name, color = self.TARGETS[index]
    r = min(self.w, self.h) * 0.105
    inner = r * 0.30
    self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="white", width=8)
    self.canvas.create_oval(x-inner, y-inner, x+inner, y+inner,
                            fill="black", outline="white", width=5)
    self.canvas.create_oval(x-inner*0.22, y-inner*0.22,
                            x+inner*0.22, y+inner*0.22,
                            fill="white", outline="white")
    arm = r * 1.12
    for a, b in [((x-arm, y), (x-r*0.50, y)),
                 ((x+r*0.50, y), (x+arm, y)),
                 ((x, y-arm), (x, y-r*0.50)),
                 ((x, y+r*0.50), (x, y+arm))]:
        self.canvas.create_line(*a, *b, fill="white", width=4)
    self.canvas.create_text(self.w/2, self.h*0.50,
                            text=f"CALIBRATING  •  TARGET {index+1}  {name}",
                            fill=color, font=("Segoe UI", 26, "bold"))
    self.canvas.create_text(self.w/2, self.h*0.55,
                            text="ACQUIRE LARGE COLOUR  →  PINPOINT CENTRE",
                            fill="white", font=("Segoe UI", 14, "bold"))


def _detect_projector_rectangle(frame: np.ndarray, baseline: Optional[np.ndarray]):
    """Return a camera-space quadrilateral for the illuminated projector area."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if baseline is not None and baseline.shape == frame.shape:
        base = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)
        score = cv2.GaussianBlur(cv2.absdiff(gray, base), (0, 0), 5)
    else:
        score = cv2.GaussianBlur(gray, (0, 0), 5)
    # Keep the bright/changed projection area, not isolated floor highlights.
    threshold = max(22, int(np.percentile(score, 88)))
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
        candidates.append((area, poly.reshape(-1, 2).astype(np.float32)))
    if not candidates:
        return None
    _, pts = max(candidates, key=lambda item: item[0])
    if len(pts) < 4:
        return None
    rect = cv2.minAreaRect(pts.reshape(-1, 1, 2))
    box = cv2.boxPoints(rect).astype(np.float32)
    return _order_quad(box)


def _order_quad(pts):
    s = pts.sum(axis=1)
    d = pts[:, 0] - pts[:, 1]
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)],
                       pts[np.argmax(s)], pts[np.argmax(d)]])


def _white_model(frame, quad):
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
    # Avoid edges where the projector rectangle and floor mix.
    kernel = np.ones((31, 31), np.uint8)
    mask = cv2.erode(mask, kernel)
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


def _apply_white_balance(frame, gains):
    g = np.asarray(gains, dtype=np.float32).reshape(1, 1, 3)
    return np.clip(frame.astype(np.float32) * g, 0, 255).astype(np.uint8)


def _colour_sample(frame, expected_bgr, expected_xy, radius):
    """Find the most target-like pixels near the predicted corner."""
    h, w = frame.shape[:2]
    cx, cy = int(expected_xy[0]), int(expected_xy[1])
    r = int(radius)
    x0, x1 = max(0, cx-r), min(w, cx+r)
    y0, y1 = max(0, cy-r), min(h, cy+r)
    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return None
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    target = cv2.cvtColor(np.uint8([[expected_bgr]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)
    dist = np.linalg.norm(lab - target, axis=2)
    sat = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32)
    score = dist - 0.18 * sat
    # Use the best 5% of pixels, then return a robust median colour.
    limit = np.percentile(score, 5)
    pixels = roi[score <= limit]
    if len(pixels) < 20:
        return None
    observed = np.median(pixels, axis=0).astype(np.float32)
    ys, xs = np.where(score <= limit)
    return (float(x0 + np.median(xs)), float(y0 + np.median(ys))), observed


def _install():
    from app.ui.field_ui import FieldConsole, ProjectionWindow

    ProjectionWindow.white = _projector_white
    ProjectionWindow.black = _projector_black
    ProjectionWindow.target = _target

    def start_calibration(self):
        self.open_projector()
        self.stop_show()
        self.open_projector()
        self.calib_index = -2  # -2=white/surface stage, -1=finished
        self.calib_history = []
        self.calib_points = []
        self.calib_color_samples = []
        self.calib_started = time.perf_counter()
        self.calib_baseline = None if self.frame is None else self.frame.copy()
        self.calib_stage = "WHITE"
        self.proj.white()
        self.calib_status.set("CALIBRATING • WHITE SURFACE")
        self.calib_detail.set("Projecting full white. Measuring camera response and projector rectangle…")
        for i, (var, lab) in enumerate(self.calib_labels):
            var.set(f"{i+1}   {ProjectionWindow.TARGETS[i][0]}   WAITING")
            lab.configure(fg="#9c95aa")
        self.calib_progress.set("SURFACE")
        self.calib_error.set("Reprojection error: PENDING")

    def detect_target(self, frame, index):
        if not getattr(self, "projection_quad", None) is None and self.H is not None:
            # Predict the projector corner in camera space using the inverse map.
            proj_margin = 0.12
            p = np.float32([[self.proj.w*proj_margin, self.proj.h*proj_margin],
                            [self.proj.w*(1-proj_margin), self.proj.h*proj_margin],
                            [self.proj.w*(1-proj_margin), self.proj.h*(1-proj_margin)],
                            [self.proj.w*proj_margin, self.proj.h*(1-proj_margin)]])[index]
            inv = np.linalg.inv(self.H)
            cp = cv2.perspectiveTransform(p.reshape(1,1,2), inv).reshape(2)
            expected = self.proj.TARGETS[index][1]
            # Broad local colour search; white-balance first if available.
            sample_frame = frame
            wb = self.state.get("colour_profile", {}).get("white_balance_gains_bgr")
            if wb:
                sample_frame = _apply_white_balance(frame, wb)
            rgb = tuple(int(expected.lstrip("#")[i:i+2], 16) for i in (0,2,4))
            expected_bgr = np.array(rgb[::-1], np.uint8)
            result = _colour_sample(sample_frame, expected_bgr, cp, max(80, int(min(frame.shape[:2])*0.18)))
            if result:
                xy, observed = result
                return xy
        # Fallback to the existing HSV detector for profiles without a rectangle yet.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ranges = [(130,179), (70,120), (15,45), (35,95)]
        lo, hi = ranges[index]
        mask = cv2.inRange(hsv, (lo,70,45), (hi,255,255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [c for c in contours if 0.00003*frame.shape[0]*frame.shape[1] < cv2.contourArea(c) < 0.10*frame.shape[0]*frame.shape[1]]
        if not candidates:
            return None
        c = max(candidates, key=cv2.contourArea)
        m = cv2.moments(c)
        return None if not m["m00"] else (m["m10"]/m["m00"], m["m01"]/m["m00"])

    def calibration_tick(self):
        if self.calib_index == -1 or self.frame is None:
            return
        if self.calib_index == -2:
            if time.perf_counter() - self.calib_started < 1.2:
                self.calib_detail.set("WHITE • allowing projector/camera exposure to settle…")
                return
            quad = _detect_projector_rectangle(self.frame, self.calib_baseline)
            if quad is None:
                self.calib_detail.set("WHITE • projector rectangle not locked yet. Increase contrast or wait…")
                return
            self.projection_quad = quad
            model = _white_model(self.frame, quad)
            if model is None:
                self.calib_detail.set("WHITE • rectangle found; measuring surface response…")
                return
            self.state["colour_profile"] = model
            # White rectangle establishes the initial camera→projector plane.
            cam = quad
            proj_pts = np.float32([(0,0),(self.proj.w,0),(self.proj.w,self.proj.h),(0,self.proj.h)])
            H, _ = cv2.findHomography(cam, proj_pts, 0)
            if H is None:
                self.calib_detail.set("WHITE • rectangle found but geometry transform failed")
                return
            self.H = H.astype(np.float32)
            self.state["homography"] = self.H.tolist()
            self.state["projector_width"] = self.proj.w
            self.state["projector_height"] = self.proj.h
            self.state["surface_rectangle_camera"] = quad.tolist()
            self.state["calibration_stage"] = "COLOUR_TARGETS"
            self.proj.target(0)
            self.calib_index = 0
            self.calib_history = []
            self.calib_labels[0][0].set("1   MAGENTA   ACTIVE")
            self.calib_labels[0][1].configure(fg="#8b35ff")
            self.calib_status.set("CALIBRATING • COLOUR TARGETS")
            self.calib_detail.set("White baseline locked. Learning the camera-observed colour of each projected target…")
            self.calib_progress.set("COLOUR 0 / 4")
            return

        p = self.detect_target(self.frame, self.calib_index)
        if p is None:
            self.calib_history = []
            self.calib_detail.set(f"Target {self.calib_index+1}: acquiring large {self.proj.TARGETS[self.calib_index][0]} target…")
            return
        self.calib_history.append(p)
        if len(self.calib_history) > 8:
            self.calib_history.pop(0)
        if len(self.calib_history) < 8:
            self.calib_detail.set(f"Target {self.calib_index+1}: acquired • pinpointing centre {len(self.calib_history)}/8")
            return
        arr = np.array(self.calib_history, np.float32)
        mean = arr.mean(0)
        spread = float(np.max(np.linalg.norm(arr-mean, axis=1)))
        self.calib_detail.set(f"Target {self.calib_index+1}: centre locked • jitter {spread:.1f}px")
        if spread > 12:
            return
        idx = self.calib_index
        # Measure the colour after the centre is stable.
        expected = self.proj.TARGETS[idx][1]
        rgb = tuple(int(expected.lstrip("#")[i:i+2], 16) for i in (0,2,4))
        frame = self.frame
        wb = self.state.get("colour_profile", {}).get("white_balance_gains_bgr")
        if wb:
            frame = _apply_white_balance(frame, wb)
        x, y = int(mean[0]), int(mean[1])
        rr = max(10, int(min(frame.shape[:2]) * 0.025))
        patch = frame[max(0,y-rr):min(frame.shape[0],y+rr), max(0,x-rr):min(frame.shape[1],x+rr)]
        observed = np.median(patch.reshape(-1,3), axis=0) if patch.size else np.array([0,0,0])
        self.calib_color_samples.append({"target": self.proj.TARGETS[idx][0], "desired_bgr": list(rgb[::-1]), "observed_bgr": observed.astype(float).tolist()})
        self.calib_points.append(tuple(mean))
        self.calib_labels[idx][0].set(f"{idx+1}   {self.proj.TARGETS[idx][0]}   COLOUR LOCKED")
        self.calib_labels[idx][1].configure(fg="#32e875")
        self.calib_progress.set(f"COLOUR {idx+1} / 4")
        self.calib_history = []
        if idx < 3:
            self.calib_index += 1
            self.proj.target(self.calib_index)
            self.calib_labels[self.calib_index][0].set(f"{self.calib_index+1}   {self.proj.TARGETS[self.calib_index][0]}   ACTIVE")
            self.calib_labels[self.calib_index][1].configure(fg="#8b35ff")
            return
        # Four colour observations now define the actual camera colour response.
        self.state["colour_profile"]["targets"] = self.calib_color_samples
        self.state["calibration_stage"] = "REPROJECTION"
        self.state["homography"] = self.H.tolist()
        self.state["projector_width"] = self.proj.w
        self.state["projector_height"] = self.proj.h
        self.state["colour_profile"]["valid"] = True
        self.state["surface_calibration_valid"] = True
        self.state["geometry_from_white"] = True
        self.state["reprojection_error"] = None
        self.state["reprojection_status"] = "PENDING"
        from app.ui.field_ui import save_state
        save_state(self.state)
        self.calib_error.set("Reprojection error: PENDING")
        self.calib_status.set("COLOUR CALIBRATION COMPLETE")
        self.calib_detail.set("Camera/projector colour response learned. Next step is independent reprojection validation.")
        self.calib_index = -1
        self.proj.black()

    FieldConsole.start_calibration = start_calibration
    FieldConsole.detect_target = detect_target
    FieldConsole.calibration_tick = calibration_tick


_install()

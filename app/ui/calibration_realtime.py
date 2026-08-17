"""Realtime calibration UX for Live Pookalam.

This module intentionally patches the shared Windows operator application instead
of duplicating it. Calibration stays a live workflow: the webcam feed remains
visible, detected targets are drawn over it, and the operator can recalibrate
any time the projector/webcam position changes.
"""
from __future__ import annotations

import cv2
from PIL import Image, ImageTk
import tkinter as tk

from app.ui.live_pookalam_app import LivePookalamApp, launch as _base_launch

BG = "#06070a"
PANEL = "#11141a"
PANEL2 = "#171c23"
BORDER = "#2a313b"
TEXT = "#f2f4f7"
MUTED = "#98a2ae"
GOLD = "#ffd45a"
GREEN = "#72f59a"
RED = "#ff7474"


def _page_calibrate(self: LivePookalamApp) -> None:
    self.title(
        "Calibrate the installation.",
        "The webcam feed stays live while the projector shows the four targets. "
        "Recalibrate whenever either device moves.",
    )

    status = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
    status.pack(fill="x", pady=(0, 10))

    self.calib_status = tk.StringVar(value="READY TO CALIBRATE")
    tk.Label(
        status, textvariable=self.calib_status, bg=PANEL, fg=GOLD,
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w", padx=16, pady=(12, 2))
    self.calib_info = tk.StringVar(value="Live webcam feed: waiting")
    tk.Label(
        status, textvariable=self.calib_info, bg=PANEL, fg=MUTED,
        font=("Consolas", 10),
    ).pack(anchor="w", padx=16, pady=(0, 12))

    actions = tk.Frame(self.main, bg=BG)
    actions.pack(fill="x", pady=(0, 10))
    self.action(actions, "CALIBRATE / RECALIBRATE", self.calibrate, True)
    self.action(actions, "PROJECTOR GRID", self.projector_test)
    self.action(actions, "ABORT", self.stop_show)
    self.action(actions, "CLEAR SAVED MAP", self.clear_calibration)

    work = tk.Frame(self.main, bg=BG)
    work.pack(fill="both", expand=True)

    left = tk.Frame(work, bg="#030407", highlightthickness=1, highlightbackground=BORDER)
    left.pack(side="left", fill="both", expand=True, padx=(0, 6))
    tk.Label(left, text="LIVE WEBCAM FEED", bg="#030407", fg=MUTED,
             font=("Segoe UI", 9, "bold")).pack(anchor="nw", padx=10, pady=8)
    self.calib_preview = tk.Label(left, bg="#030407")
    self.calib_preview.pack(expand=True, fill="both", padx=8, pady=(0, 8))

    right = tk.Frame(work, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER, width=290)
    right.pack(side="right", fill="y", padx=(6, 0))
    right.pack_propagate(False)
    tk.Label(right, text="CALIBRATION STATUS", bg=PANEL2, fg=GOLD,
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 8))

    self.calib_target_labels = []
    for i in range(4):
        var = tk.StringVar(value=f"TARGET {i+1}   NOT FOUND")
        lbl = tk.Label(right, textvariable=var, bg=PANEL2, fg=RED,
                       font=("Consolas", 10, "bold"))
        lbl.pack(anchor="w", padx=16, pady=5)
        self.calib_target_labels.append((var, lbl))

    tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=16, pady=14)
    self.calib_map_var = tk.StringVar(
        value="MAP\n" + ("CALIBRATED" if self.H is not None else "NOT CALIBRATED")
    )
    tk.Label(right, textvariable=self.calib_map_var, bg=PANEL2,
             fg=GREEN if self.H is not None else GOLD,
             font=("Consolas", 12, "bold"), justify="left").pack(anchor="w", padx=16)

    tk.Label(
        right,
        text="Move the projector or webcam, then press\nCALIBRATE / RECALIBRATE.\n\nThe previous saved map is kept until\na new valid 4-point map is captured.",
        bg=PANEL2, fg=MUTED, font=("Segoe UI", 9), justify="left",
    ).pack(anchor="w", padx=16, pady=20)

    self._update_calibration_preview()


def _update_calibration_preview(self: LivePookalamApp) -> None:
    if not hasattr(self, "calib_preview") or self.frame is None:
        return

    frame = self.frame.copy()
    try:
        circles = self.__class__.calibration_circles(frame)
    except AttributeError:
        # Keep compatibility with the existing module-level detector.
        from app.ui.live_pookalam_app import detect_calibration_circles
        circles = detect_calibration_circles(frame)

    # Order by the same geometric ordering used by calibration.
    if len(circles) == 4:
        try:
            from app.ui.live_pookalam_app import order4
            ordered = order4([(x, y) for x, y, _ in circles])
            points = [(int(x), int(y)) for x, y in ordered]
        except Exception:
            points = [(int(x), int(y)) for x, y, _ in circles]
    else:
        points = [(int(x), int(y)) for x, y, _ in circles]

    for idx, (x, y) in enumerate(points[:4], 1):
        cv2.circle(frame, (x, y), 28, (0, 255, 0), 3)
        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
        cv2.putText(frame, str(idx), (x + 35, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

    total = len(points)
    if hasattr(self, "calib_info"):
        phase = "CAPTURE IN PROGRESS" if self.mode == "calibrate" else "LIVE MONITOR"
        self.calib_info.set(f"{phase}   •   PROJECTED TARGETS DETECTED: {total}/4")

    for i, (var, lbl) in enumerate(getattr(self, "calib_target_labels", [])):
        if i < len(points):
            x, y = points[i]
            var.set(f"TARGET {i+1}   DETECTED  ({x}, {y})")
            lbl.configure(fg=GREEN)
        else:
            var.set(f"TARGET {i+1}   NOT FOUND")
            lbl.configure(fg=RED)

    if hasattr(self, "calib_map_var"):
        self.calib_map_var.set(
            "MAP\n" + ("CALIBRATED" if self.H is not None else "NOT CALIBRATED")
        )

    rgb = cv2.cvtColor(cv2.resize(frame, (900, 506)), cv2.COLOR_BGR2RGB)
    self.calib_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
    self.calib_preview.configure(image=self.calib_photo)


def _calibrate(self: LivePookalamApp) -> None:
    # Reuse the actual calibration algorithm already in the application.
    self.open_projector()
    self.proj.targets()
    self.mode = "calibrate"
    self.calibration_started = __import__("time").time()
    if hasattr(self, "calib_status"):
        self.calib_status.set("CALIBRATING — REAL-TIME TARGET ACQUISITION")


def _tick(self: LivePookalamApp) -> None:
    # Run the original application loop, then refresh the calibration workspace
    # using the newest webcam frame. The original tick owns scheduling.
    original_tick = getattr(self, "_original_tick")
    original_tick()
    if self.mode == "calibrate":
        self._update_calibration_preview()


def install() -> None:
    if getattr(LivePookalamApp, "_realtime_calibration_installed", False):
        return

    LivePookalamApp.page_calibrate = _page_calibrate
    LivePookalamApp.calibrate = _calibrate
    LivePookalamApp._update_calibration_preview = _update_calibration_preview

    # Preserve the shared runtime loop and wrap it once.
    LivePookalamApp._original_tick = LivePookalamApp.tick
    LivePookalamApp.tick = _tick
    LivePookalamApp._realtime_calibration_installed = True


def launch() -> None:
    install()
    _base_launch()


__all__ = ["install", "launch"]

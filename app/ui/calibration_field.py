"""Field-safe calibration workflow for Live Pookalam."""
from __future__ import annotations

import time
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from app.ui.live_pookalam_app import LivePookalamApp, launch as _base_launch
from app.calibration.engine import LiveCalibrator

BG = "#06070a"
PANEL = "#11141a"
PANEL2 = "#171c23"
BORDER = "#2a313b"
TEXT = "#f2f4f7"
MUTED = "#98a2ae"
GOLD = "#ffd45a"
GREEN = "#72f59a"
RED = "#ff7474"
BLUE = "#75b8ff"
PURPLE = "#bd86ff"


def _draw_target(app: LivePookalamApp) -> None:
    if not app.proj or not hasattr(app, "calibrator"):
        return
    canvas = app.proj.canvas
    canvas.delete("all")
    w, h = app.proj.w, app.proj.h
    canvas.configure(bg="black")
    target = app.calibrator.active_target()
    if target is None:
        canvas.create_text(w / 2, h / 2 - 32, text="CALIBRATION COMPLETE", fill=GREEN,
                           font=("Segoe UI", 30, "bold"))
        canvas.create_text(w / 2, h / 2 + 18, text="Verifying camera ↔ projector mapping…", fill=TEXT,
                           font=("Segoe UI", 16))
        return
    x, y = target.projector_xy
    radius = min(w, h) * 0.032
    color = "#ff00ff" if target.index == 0 else "#00ffff" if target.index == 1 else "#ffff00" if target.index == 2 else "#00ff00"
    canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill=color, outline="white", width=5)
    canvas.create_text(x, y, text=str(target.index + 1), fill="black", font=("Segoe UI", 24, "bold"))
    canvas.create_text(w / 2, h - 70, text=f"TARGET {target.index + 1} / 4  •  {target.name}",
                       fill=TEXT, font=("Segoe UI", 17, "bold"))
    canvas.create_text(w / 2, 55, text="LIVE POOKALAM • CALIBRATION", fill=GOLD,
                       font=("Segoe UI", 20, "bold"))


def _page_calibrate(self: LivePookalamApp) -> None:
    self.title(
        "Calibrate",
        "Live camera calibration. Only the active colored target is valid; the wallpaper and background are ignored.",
    )
    status = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
    status.pack(fill="x", pady=(0, 10))
    self.calib_status = tk.StringVar(value="READY")
    tk.Label(status, textvariable=self.calib_status, bg=PANEL, fg=GOLD,
             font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
    self.calib_info = tk.StringVar(value="Press CALIBRATE to begin.")
    tk.Label(status, textvariable=self.calib_info, bg=PANEL, fg=MUTED,
             font=("Consolas", 10)).pack(anchor="w", padx=16, pady=(0, 12))

    actions = tk.Frame(self.main, bg=BG)
    actions.pack(fill="x", pady=(0, 10))
    self.action(actions, "CALIBRATE", self.calibrate, True)
    self.action(actions, "RECALIBRATE", self.calibrate)
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

    right = tk.Frame(work, bg=PANEL2, width=330, highlightthickness=1, highlightbackground=BORDER)
    right.pack(side="right", fill="y", padx=(6, 0))
    right.pack_propagate(False)
    tk.Label(right, text="FIELD CALIBRATION", bg=PANEL2, fg=GOLD,
             font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
    self.calib_target_labels = []
    for i, name in enumerate(("TOP LEFT", "TOP RIGHT", "BOTTOM RIGHT", "BOTTOM LEFT")):
        var = tk.StringVar(value=f"{i+1}  {name}  WAITING")
        lbl = tk.Label(right, textvariable=var, bg=PANEL2, fg=MUTED,
                       font=("Consolas", 10, "bold"))
        lbl.pack(anchor="w", padx=16, pady=5)
        self.calib_target_labels.append((var, lbl))
    tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=16, pady=14)
    self.calib_map_var = tk.StringVar(value="MAP: " + ("CALIBRATED" if self.H is not None else "NOT CALIBRATED"))
    tk.Label(right, textvariable=self.calib_map_var, bg=PANEL2,
             fg=GREEN if self.H is not None else GOLD,
             font=("Consolas", 12, "bold")).pack(anchor="w", padx=16)
    self.calib_error_var = tk.StringVar(value="Reprojection error: —")
    tk.Label(right, textvariable=self.calib_error_var, bg=PANEL2, fg=BLUE,
             font=("Consolas", 10, "bold")).pack(anchor="w", padx=16, pady=10)
    tk.Label(right,
             text="The projector must show a BLACK calibration surface with one active marker.\n\nIf you can see your Windows wallpaper during calibration, stop and check the projector display selection.",
             bg=PANEL2, fg=MUTED, font=("Segoe UI", 9), justify="left", wraplength=280).pack(anchor="w", padx=16, pady=18)
    self._refresh_calibration_preview()


def _refresh_calibration_preview(self: LivePookalamApp) -> None:
    if not hasattr(self, "calib_preview") or self.frame is None:
        return
    frame = self.frame.copy()
    obs = self.calibrator.detect_active(frame) if hasattr(self, "calibrator") else None
    target = self.calibrator.active_target() if hasattr(self, "calibrator") else None
    if obs is not None:
        x, y = map(int, obs.camera_xy)
        cv2.circle(frame, (x, y), 32, (0, 255, 0), 3)
        cv2.circle(frame, (x, y), 6, (0, 255, 0), -1)
        cv2.putText(frame, f"TARGET {obs.index + 1}  LOCK CANDIDATE", (x + 20, max(30, y - 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    if target is not None:
        self.calib_info.set(f"TARGET {target.index + 1}/4  •  STABILITY {len(self.calibrator.candidate_history)}/8")
    for i, (var, lbl) in enumerate(getattr(self, "calib_target_labels", [])):
        if i in self.calibrator.observations:
            var.set(f"{i+1}  {self.calibrator.targets[i].name}  LOCKED")
            lbl.configure(fg=GREEN)
        elif target is not None and target.index == i:
            var.set(f"{i+1}  {self.calibrator.targets[i].name}  ACQUIRING")
            lbl.configure(fg=GOLD)
        else:
            var.set(f"{i+1}  {self.calibrator.targets[i].name}  WAITING")
            lbl.configure(fg=MUTED)
    rgb = cv2.cvtColor(cv2.resize(frame, (900, 506)), cv2.COLOR_BGR2RGB)
    self.calib_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
    self.calib_preview.configure(image=self.calib_photo)


def _calibrate(self: LivePookalamApp) -> None:
    self.open_projector()
    pw, ph = self.proj.w, self.proj.h
    self.calibrator = LiveCalibrator(pw, ph)
    self.calibrator.begin()
    self.mode = "calibration"
    self.calibration_started = time.monotonic()
    _draw_target(self)
    self.calib_status.set("CALIBRATING") if hasattr(self, "calib_status") else None


def _process_calibration(self: LivePookalamApp) -> None:
    if self.mode != "calibration" or not hasattr(self, "calibrator") or self.frame is None:
        return
    obs = self.calibrator.detect_active(self.frame)
    if obs is not None and self.calibrator.accept_observation(obs):
        _draw_target(self)
    if self.calibrator.finished():
        result = self.calibrator.build_result()
        if result is None or result.reprojection_error > 12.0:
            if hasattr(self, "calib_status"):
                self.calib_status.set("CALIBRATION REJECTED")
                self.calib_info.set("Mapping error is too high. Reposition hardware and recalibrate.")
            self.calibrator.reset()
            _draw_target(self)
            return
        self.H = result.homography
        self.state.update({"homography": self.H.tolist(), "projector_width": self.proj.w, "projector_height": self.proj.h})
        self.state["calibration_error_px"] = result.reprojection_error
        save_state(self.state)
        self.calib_status.set("CALIBRATION ACCEPTED")
        self.calib_info.set(f"Stable 4-point map saved • error {result.reprojection_error:.1f}px")
        self.calib_error_var.set(f"Reprojection error: {result.reprojection_error:.1f}px")
        self.calib_map_var.set("MAP: CALIBRATED")
        canvas = self.proj.canvas
        canvas.delete("all")
        canvas.create_text(self.proj.w / 2, self.proj.h / 2 - 25, text="CALIBRATION ACCEPTED", fill=GREEN, font=("Segoe UI", 30, "bold"))
        canvas.create_text(self.proj.w / 2, self.proj.h / 2 + 25, text=f"Error {result.reprojection_error:.1f}px", fill=TEXT, font=("Segoe UI", 18))
        self.mode = "calibrate"


def _tick(self: LivePookalamApp) -> None:
    # Execute the original camera/render loop, then run the calibration state machine.
    original = getattr(LivePookalamApp, "_field_original_tick", LivePookalamApp.tick)
    original(self)
    if getattr(self, "mode", "") == "calibration":
        _process_calibration(self)
        _refresh_calibration_preview(self)


def install() -> None:
    if getattr(LivePookalamApp, "_field_calibration_installed", False):
        return
    LivePookalamApp.page_calibrate = _page_calibrate
    LivePookalamApp.calibrate = _calibrate
    LivePookalamApp._refresh_calibration_preview = _refresh_calibration_preview
    LivePookalamApp._field_original_tick = LivePookalamApp.tick
    LivePookalamApp.tick = _tick
    LivePookalamApp._field_calibration_installed = True


def launch() -> None:
    install()
    _base_launch()


__all__ = ["install", "launch"]

"""Windows launcher wiring shared runtime behavior into the Live Pookalam UI."""
from __future__ import annotations

import cv2
import numpy as np
from tkinter import messagebox

from app.ui.live_pookalam_app import LivePookalamApp, order4, detect_calibration_circles, save_state


def calibration_step(self: LivePookalamApp) -> None:
    if self.frame is None or not self.proj:
        return
    circles = detect_calibration_circles(self.frame)
    self.status_message(f"CALIBRATION TARGETS {len(circles)}/4")
    if len(circles) != 4:
        return
    camera_points = order4([(x, y) for x, y, _ in circles])
    margin = 0.12
    pw, ph = self.proj.w, self.proj.h
    projector_points = np.float32([
        [pw * margin, ph * margin],
        [pw * (1 - margin), ph * margin],
        [pw * (1 - margin), ph * (1 - margin)],
        [pw * margin, ph * (1 - margin)],
    ])
    homography, _ = cv2.findHomography(camera_points, projector_points, 0)
    if homography is None:
        return
    self.H = homography.astype(np.float32)
    self.state.update({
        "homography": self.H.tolist(),
        "projector_width": int(pw),
        "projector_height": int(ph),
    })
    save_state(self.state)
    self.mode = "calibrate"
    self.proj.clear()
    self.status_message("CALIBRATION SAVED")
    messagebox.showinfo("Calibration Complete", "Camera → projector mapping has been saved to the installation profile.")


def _tick_with_calibration(original_tick):
    def wrapped(self: LivePookalamApp):
        original_tick(self)
        if self.mode == "calibrate" and self.frame is not None and self.proj is not None:
            try:
                calibration_step(self)
            except Exception as exc:
                self.status_message(f"CALIBRATION ERROR: {exc}")
    return wrapped


LivePookalamApp.calibration_step = calibration_step
LivePookalamApp.tick = _tick_with_calibration(LivePookalamApp.tick)


def launch() -> None:
    import tkinter as tk
    root = tk.Tk()
    LivePookalamApp(root)
    root.mainloop()

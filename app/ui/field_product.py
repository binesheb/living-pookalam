"""Production launcher for the Live Pookalam field console."""
from __future__ import annotations

import time
import tkinter as tk

from app.calibration.engine import LiveCalibrator
from app.ui.field_experience_console import FieldExperienceConsole
from app.ui.field_ui import ProjectionWindow, save_state
from app.ui.masked_projection import MaskedProjectionWindow


class ProductFieldConsole(FieldExperienceConsole):
    """Approved production calibration and projection paths."""

    def __init__(self, root):
        self.calibrator = None
        super().__init__(root)

    def open_projector(self):
        if self.proj is None or not self.proj.win.winfo_exists():
            self.proj = MaskedProjectionWindow(self)
        self.proj.place()

    def start_calibration(self):
        """Start a fully automated four-target calibration state machine."""
        self.open_projector()
        self.stop_show()
        self.open_projector()
        self.calibrator = LiveCalibrator(self.proj.w, self.proj.h)
        self.calibrator.begin()
        self.calib_index = 0
        self.calib_history = []
        self.calib_started = time.monotonic()
        self.proj.target(0)
        self.calib_status.set("CALIBRATING • TARGET 1 / 4")
        self.calib_detail.set("Acquiring the active coloured marker automatically. Do not click the target.")
        for i, (var, lab) in enumerate(self.calib_labels):
            var.set(f"{i+1}   {ProjectionWindow.TARGETS[i][0]}   {'ACTIVE' if i == 0 else 'WAITING'}")
            lab.configure(fg="#8b35ff" if i == 0 else "#9c95aa")
        self.calib_progress.set("0 / 4")
        self.calib_error.set("Reprojection error: pending")

    def stop_calibration(self):
        self.calib_index = -1
        if self.calibrator is not None:
            self.calibrator.active_index = None
            self.calibrator.candidate_history.clear()
        if self.proj:
            self.proj.black()
        if hasattr(self, "calib_status"):
            self.calib_status.set("CALIBRATION STOPPED")

    def calibration_tick(self):
        if self.calib_index < 0 or self.frame is None or self.calibrator is None:
            return

        observation = self.calibrator.detect_active(self.frame)
        if observation is None:
            self.calib_detail.set(f"Target {self.calib_index + 1}: searching for active projected marker…")
            self.calib_history = self.calibrator.candidate_history
            return

        self.calibrator.accept_observation(observation)
        self.calib_history = self.calibrator.candidate_history
        target = self.calibrator.active_target()
        locked = len(self.calibrator.observations)
        self.calib_progress.set(f"{locked} / 4")
        self.calib_detail.set(
            f"Target {observation.index + 1}: stability {len(self.calibrator.candidate_history)}/8 • "
            f"score {observation.score:.2f}"
        )

        for i, (var, lab) in enumerate(self.calib_labels):
            if i in self.calibrator.observations:
                var.set(f"{i+1}   {ProjectionWindow.TARGETS[i][0]}   LOCKED")
                lab.configure(fg="#32e875")
            elif target is not None and i == target.index:
                var.set(f"{i+1}   {ProjectionWindow.TARGETS[i][0]}   ACTIVE")
                lab.configure(fg="#8b35ff")

        if not self.calibrator.finished():
            if target is not None:
                self.calib_index = target.index
                self.proj.target(target.index)
                self.calib_status.set(f"CALIBRATING • TARGET {target.index + 1} / 4")
            return

        result = self.calibrator.build_result()
        if result is None or result.reprojection_error > 12.0:
            self.calib_index = -1
            self.calib_status.set("CALIBRATION REJECTED")
            error = "unavailable" if result is None else f"{result.reprojection_error:.1f}px"
            self.calib_detail.set(f"New mapping rejected • reprojection error {error}. Reposition and press CALIBRATE again.")
            self.calib_error.set(f"Reprojection error: {error} • OLD MAP RETAINED")
            if self.proj:
                self.proj.black()
            return

        self.H = result.homography
        self.state["homography"] = self.H.tolist()
        self.state["projector_width"] = self.proj.w
        self.state["projector_height"] = self.proj.h
        self.state["calibration_error_px"] = result.reprojection_error
        save_state(self.state)

        self.calib_index = -1
        self.calib_status.set("CALIBRATION ACCEPTED")
        self.calib_detail.set(f"New camera ↔ projector map saved • {result.reprojection_error:.1f}px mean error")
        self.calib_error.set(f"Reprojection error: {result.reprojection_error:.1f}px • MAP SAVED")
        self.calib_progress.set("4 / 4")
        if self.proj:
            self.proj.canvas.delete("all")
            self.proj.canvas.create_text(self.proj.w / 2, self.proj.h / 2 - 25,
                                         text="CALIBRATION ACCEPTED", fill="#32e875",
                                         font=("Segoe UI", 30, "bold"))
            self.proj.canvas.create_text(self.proj.w / 2, self.proj.h / 2 + 25,
                                         text=f"Mean error {result.reprojection_error:.1f}px",
                                         fill="#f4f1fa", font=("Segoe UI", 18))


def launch():
    root = tk.Tk()
    # Import late to avoid a circular dependency during module discovery.
    from app.ui.premium_shell import PremiumProductFieldConsole
    PremiumProductFieldConsole(root)
    root.mainloop()

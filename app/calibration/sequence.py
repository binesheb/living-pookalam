"""Automated calibration sequence state model.

The UI/runner can use this model to make calibration observable and resumable.
Colour/surface baseline intentionally precedes perception and geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CalibrationStage(str, Enum):
    HARDWARE = "hardware"
    BLACK = "black"
    WHITE = "white"
    COLOUR = "colour"
    SURFACE = "surface"
    PERCEPTION = "perception"
    GEOMETRY = "geometry"
    REPROJECTION = "reprojection"
    SAVE = "save"
    COMPLETE = "complete"
    FAILED = "failed"


STAGES = (
    CalibrationStage.HARDWARE,
    CalibrationStage.BLACK,
    CalibrationStage.WHITE,
    CalibrationStage.COLOUR,
    CalibrationStage.SURFACE,
    CalibrationStage.PERCEPTION,
    CalibrationStage.GEOMETRY,
    CalibrationStage.REPROJECTION,
    CalibrationStage.SAVE,
)


@dataclass
class CalibrationProgress:
    stage: CalibrationStage = CalibrationStage.HARDWARE
    completed: tuple[str, ...] = ()
    message: str = "Waiting to start"
    progress: float = 0.0
    reprojection_error: float | None = None

    def start(self, stage: CalibrationStage, message: str) -> "CalibrationProgress":
        completed = list(self.completed)
        if self.stage.value not in completed and self.stage in STAGES:
            completed.append(self.stage.value)
        return CalibrationProgress(stage, tuple(completed), message, self.progress, self.reprojection_error)

    def set_progress(self, value: float, message: str | None = None) -> "CalibrationProgress":
        return CalibrationProgress(self.stage, self.completed, message or self.message, max(0.0, min(1.0, value)), self.reprojection_error)

    def set_reprojection_error(self, pixels: float) -> "CalibrationProgress":
        return CalibrationProgress(self.stage, self.completed, self.message, self.progress, float(pixels))

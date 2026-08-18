"""Surface-aware camera/projector colour calibration primitives."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


REFERENCE_PATCHES = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "gray": (128, 128, 128),
}


@dataclass
class SurfaceResponse:
    """Measured response of the projection surface under black/white frames."""
    black_rgb: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    white_rgb: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32) * 255.0)
    ambient_rgb: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    brightness_headroom: float = 1.0
    uniformity: float = 1.0

    @property
    def white_minus_black(self) -> np.ndarray:
        return np.maximum(self.white_rgb - self.black_rgb, 1.0)

    def normalize_observed(self, rgb: np.ndarray) -> np.ndarray:
        x = np.asarray(rgb, dtype=np.float32)
        return np.clip((x - self.black_rgb) / self.white_minus_black, 0.0, 1.0)


def measure_surface_response(black_rgb: np.ndarray, white_rgb: np.ndarray) -> SurfaceResponse:
    """Build a surface profile from representative camera RGB samples."""
    black = np.asarray(black_rgb, dtype=np.float32).reshape(-1, 3)
    white = np.asarray(white_rgb, dtype=np.float32).reshape(-1, 3)
    if black.size == 0 or white.size == 0 or black.shape[1] != 3 or white.shape[1] != 3:
        raise ValueError("black_rgb and white_rgb must contain RGB samples")
    black_mean = np.mean(black, axis=0)
    white_mean = np.mean(white, axis=0)
    span = np.maximum(white - black_mean, 1.0)
    luma = np.mean(span, axis=1)
    uniformity = float(np.clip(np.min(luma) / max(float(np.max(luma)), 1.0), 0.0, 1.0))
    headroom = float(np.clip(np.mean(np.maximum(white_mean - black_mean, 0.0)) / 255.0, 0.0, 1.0))
    return SurfaceResponse(
        black_rgb=black_mean.astype(np.float32),
        white_rgb=white_mean.astype(np.float32),
        ambient_rgb=black_mean.astype(np.float32),
        brightness_headroom=headroom,
        uniformity=uniformity,
    )


@dataclass
class ColorProfile:
    """Installation-specific linear RGB correction profile."""
    matrix: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float32))
    gain: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32))
    gamma: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32))
    confidence: float = 0.0
    surface: SurfaceResponse = field(default_factory=SurfaceResponse)

    def correct(self, rgb: np.ndarray) -> np.ndarray:
        x = np.asarray(rgb, dtype=np.float32) / 255.0
        x = np.clip(x, 0.0, 1.0)
        x = np.power(x, np.maximum(self.gamma, 1e-3)) * self.gain
        x = x @ self.matrix.T
        return np.clip(x * 255.0, 0.0, 255.0).astype(np.uint8)

    def compensate_surface(self, desired_rgb: np.ndarray) -> np.ndarray:
        """Conservatively compensate a desired colour for measured surface response."""
        desired = np.asarray(desired_rgb, dtype=np.float32)
        desired_norm = np.clip(desired / 255.0, 0.0, 1.0)
        surface_norm = np.clip(self.surface.white_minus_black / 255.0, 0.02, 1.0)
        command = desired_norm / surface_norm
        return np.clip(command * 255.0, 0.0, 255.0).astype(np.uint8)


def estimate_profile(reference_rgb: np.ndarray, observed_rgb: np.ndarray, surface: SurfaceResponse | None = None) -> ColorProfile:
    """Estimate a deterministic RGB transform from matching reference/observed patches."""
    ref = np.asarray(reference_rgb, dtype=np.float32) / 255.0
    obs = np.asarray(observed_rgb, dtype=np.float32) / 255.0
    if ref.shape != obs.shape or ref.ndim != 2 or ref.shape[1] != 3 or len(ref) < 3:
        raise ValueError("reference_rgb and observed_rgb must be matching N×3 arrays")
    m, *_ = np.linalg.lstsq(obs, ref, rcond=None)
    predicted = obs @ m
    error = float(np.mean(np.abs(predicted - ref)))
    confidence = float(np.clip(1.0 - error, 0.0, 1.0))
    return ColorProfile(matrix=m.T.astype(np.float32), confidence=confidence, surface=surface or SurfaceResponse())

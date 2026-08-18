"""Automatic camera/projector colour-calibration primitives."""
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
class ColorProfile:
    """Installation-specific linear RGB correction profile."""

    matrix: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float32))
    gain: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32))
    gamma: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32))
    confidence: float = 0.0

    def correct(self, rgb: np.ndarray) -> np.ndarray:
        x = np.asarray(rgb, dtype=np.float32) / 255.0
        x = np.clip(x, 0.0, 1.0)
        x = np.power(x, np.maximum(self.gamma, 1e-3)) * self.gain
        x = x @ self.matrix.T
        return np.clip(x * 255.0, 0.0, 255.0).astype(np.uint8)


def estimate_profile(reference_rgb: np.ndarray, observed_rgb: np.ndarray) -> ColorProfile:
    """Estimate a robust RGB transform from matching reference/observed patches.

    Arrays are N×3 in RGB order. The solve is deliberately small and deterministic
    so it can run during installation calibration without an ML dependency.
    """
    ref = np.asarray(reference_rgb, dtype=np.float32) / 255.0
    obs = np.asarray(observed_rgb, dtype=np.float32) / 255.0
    if ref.shape != obs.shape or ref.ndim != 2 or ref.shape[1] != 3 or len(ref) < 3:
        raise ValueError("reference_rgb and observed_rgb must be matching N×3 arrays")
    # Least-squares colour matrix: observed @ M ≈ reference.
    m, *_ = np.linalg.lstsq(obs, ref, rcond=None)
    predicted = obs @ m
    error = float(np.mean(np.abs(predicted - ref)))
    confidence = float(np.clip(1.0 - error, 0.0, 1.0))
    return ColorProfile(matrix=m.T.astype(np.float32), confidence=confidence)

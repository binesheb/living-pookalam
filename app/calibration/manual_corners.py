"""Manual four-corner calibration helpers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
from .floor_space import _homography, _invert, transform
CORNER_ORDER=("top_left","top_right","bottom_right","bottom_left")
def validate_corners(points: Iterable[Iterable[float]]) -> np.ndarray:
    pts=np.asarray(list(points),dtype=np.float32)
    if pts.shape!=(4,2): raise ValueError("select exactly four corners")
    if not np.isfinite(pts).all(): raise ValueError("corner coordinates must be finite")
    c=np.vstack([pts,pts[0]]); area=.5*abs(float(np.sum(c[:-1,0]*c[1:,1]-c[1:,0]*c[:-1,1])))
    if area<1.0: raise ValueError("selected corners do not form a usable quadrilateral")
    return pts
@dataclass(frozen=True)
class ManualCornerCalibration:
    camera_points: np.ndarray; floor_to_camera: np.ndarray; camera_to_floor: np.ndarray; physical_width_mm: float; physical_height_mm: float
    def as_dict(self)->dict:
        return {"corner_order":list(CORNER_ORDER),"camera_points":self.camera_points.tolist(),"floor_to_camera":self.floor_to_camera.tolist(),"camera_to_floor":self.camera_to_floor.tolist(),"physical_width_mm":self.physical_width_mm,"physical_height_mm":self.physical_height_mm}
def calibrate_manual_corners(points,width_mm,height_mm)->ManualCornerCalibration:
    corners=validate_corners(points); width,height=float(width_mm),float(height_mm)
    if width<=0 or height<=0: raise ValueError("physical floor dimensions must be positive")
    floor=np.float32([[0,0],[width,0],[width,height],[0,height]])
    camera_to_floor=_homography(corners,floor)
    return ManualCornerCalibration(corners,_invert(camera_to_floor),camera_to_floor,width,height)
def map_floor_points(points,calibration): return transform(points,calibration.floor_to_camera)

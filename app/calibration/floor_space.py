"""Floor calibration and projector pre-warp geometry.

The user-selected camera quadrilateral is the authoritative usable floor area.
Projector reference points observed by the camera calibrate how projector pixels
land on that same plane. Content is generated in ideal floor coordinates and
pre-warped only for the projector.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import cv2
import numpy as np

@dataclass(frozen=True)
class FloorCalibrationResult:
    camera_to_floor: np.ndarray
    floor_to_camera: np.ndarray
    projector_to_floor: np.ndarray
    floor_to_projector: np.ndarray
    camera_to_projector: np.ndarray
    projector_to_camera: np.ndarray
    camera_error_mm: float
    projector_error_mm: float
    physical_width_mm: float
    physical_height_mm: float
    @property
    def max_error_mm(self): return max(self.camera_error_mm,self.projector_error_mm)
    @property
    def valid(self): return bool(np.isfinite(self.max_error_mm))

def _points(points):
    pts=np.asarray(list(points),dtype=np.float32)
    if pts.shape!=(4,2): raise ValueError("exactly four 2-D points are required")
    return pts

def _homography(src,dst):
    h,_=cv2.findHomography(src,dst,method=0)
    if h is None: raise ValueError("unable to compute homography from four points")
    return h.astype(np.float32)
def _invert(h):
    inv=np.linalg.inv(np.asarray(h,dtype=np.float64)); inv/=inv[2,2]; return inv.astype(np.float32)
def transform(points,homography):
    pts=np.asarray(list(points),dtype=np.float32).reshape(-1,1,2)
    return cv2.perspectiveTransform(pts,np.asarray(homography,dtype=np.float32)).reshape(-1,2)
def reprojection_error_mm(observed,expected,homography):
    expected_pts=_points(expected); mapped=transform(observed,homography)
    return float(np.mean(np.linalg.norm(mapped-expected_pts,axis=1)))

def build_floor_calibration(camera_points,projector_points,physical_width_mm,physical_height_mm):
    width,height=float(physical_width_mm),float(physical_height_mm)
    if width<=0 or height<=0: raise ValueError("physical floor dimensions must be positive")
    camera=_points(camera_points); projector=_points(projector_points)
    floor=np.float32([[0,0],[width,0],[width,height],[0,height]])
    camera_to_floor=_homography(camera,floor); floor_to_camera=_invert(camera_to_floor)
    projector_to_floor=_homography(projector,floor); floor_to_projector=_invert(projector_to_floor)
    camera_to_projector=_homography(camera,projector); projector_to_camera=_invert(camera_to_projector)
    return FloorCalibrationResult(camera_to_floor,floor_to_camera,projector_to_floor,floor_to_projector,camera_to_projector,projector_to_camera,reprojection_error_mm(camera,floor,camera_to_floor),reprojection_error_mm(projector,floor,projector_to_floor),width,height)

def projector_warp_for_camera_floor(camera_floor_points, projector_reference_camera_points):
    """Return projector->floor homography using the manually selected floor and
    four camera-observed projected reference points in matching corner order."""
    camera_floor=_points(camera_floor_points); projected=_points(projector_reference_camera_points)
    return _homography(projected,camera_floor)

def prewarp_floor_image(floor_image, floor_to_projector, projector_size):
    """Warp ideal floor-space artwork into the projector framebuffer."""
    width,height=map(int,projector_size)
    return cv2.warpPerspective(floor_image,np.asarray(floor_to_projector,dtype=np.float32),(width,height),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
def normalized_floor_corners(): return np.float32([[0,0],[1,0],[1,1],[0,1]])

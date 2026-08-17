"""Camera-image Pookalam analysis primitives.

The analyzer deliberately separates detection from rendering. It returns a
mask and normalized feature map so effects can later be constrained to the
actual physical design, even when the camera is mounted at an angle.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import cv2
import numpy as np

@dataclass
class PookalamAnalysis:
    found: bool
    confidence: float
    center: tuple[float,float] = (0.5,0.5)
    radius: float = 0.0
    bbox: tuple[int,int,int,int] = (0,0,0,0)
    contour: list[tuple[int,int]] | None = None
    ring_centers: list[tuple[float,float,float]] | None = None

    def to_dict(self): return asdict(self)

class PookalamAnalyzer:
    def analyze(self, frame: np.ndarray) -> PookalamAnalysis:
        if frame is None or frame.size == 0:return PookalamAnalysis(False,0.0)
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        sat=hsv[:,:,1]; val=hsv[:,:,2]
        mask=((sat>45)&(val>40)).astype(np.uint8)*255
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8))
        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        h,w=mask.shape; min_area=.01*w*h; max_area=.92*w*h
        candidates=[c for c in contours if min_area<cv2.contourArea(c)<max_area]
        if not candidates:return PookalamAnalysis(False,0.0)
        c=max(candidates,key=cv2.contourArea); area=cv2.contourArea(c); x,y,bw,bh=cv2.boundingRect(c)
        m=cv2.moments(c)
        if not m['m00']:return PookalamAnalysis(False,0.0)
        cx=m['m10']/m['m00']/w; cy=m['m01']/m['m00']/h
        (_, _),r=cv2.minEnclosingCircle(c); rn=r/min(w,h)
        fill=min(1.0,area/(np.pi*r*r+1e-6))
        size=min(1.0,area/(.35*w*h))
        confidence=float(.55*fill+.45*size)
        rings=[]
        for q in (.25,.45,.65,.85): rings.append((cx,cy,rn*q))
        contour=[(int(px),int(py)) for [[px,py]] in c[::max(1,len(c)//300)]]
        return PookalamAnalysis(True,confidence,(cx,cy),rn,(x,y,bw,bh),contour,rings)

    def make_mask(self, analysis:PookalamAnalysis, shape:tuple[int,int]):
        h,w=shape[:2]; mask=np.zeros((h,w),np.uint8)
        if not analysis.found or not analysis.contour:return mask
        pts=np.array(analysis.contour,np.int32).reshape(-1,1,2)
        cv2.fillPoly(mask,[pts],255)
        return mask

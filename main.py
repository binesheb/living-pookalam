import json, os, sys, subprocess
from pathlib import Path
import cv2
import numpy as np
import requests

VERSION='1.0.0'
ROOT=Path(__file__).resolve().parent
CONFIG=ROOT/'calibration.json'
VERSION_URL='https://raw.githubusercontent.com/binesheb/living-pookalam/main/version.txt'

def mandatory_update_check():
    try:
        remote=requests.get(VERSION_URL,timeout=5).text.strip()
        if remote and remote!=VERSION:
            subprocess.run(['git','pull','--ff-only'],cwd=ROOT,check=True)
            os.execv(sys.executable,[sys.executable,*sys.argv])
    except Exception as exc: print('Update check unavailable:',exc)

def cameras(limit=10):
    found=[]
    for i in range(limit):
        cap=cv2.VideoCapture(i)
        if cap.isOpened() and cap.read()[0]: found.append(i)
        cap.release()
    return found

def choose_camera():
    found=cameras()
    if not found: raise RuntimeError('No webcam found')
    print('Detected webcams:',found)
    while True:
        v=input('Camera index: ').strip()
        if v.isdigit() and int(v) in found: return int(v)

def projector_geometry():
    try:
        import ctypes
        user32=ctypes.windll.user32
        primary_w=user32.GetSystemMetrics(0)
        primary_h=user32.GetSystemMetrics(1)
        virtual_w=user32.GetSystemMetrics(78)
        virtual_h=user32.GetSystemMetrics(79)
        if virtual_w<=primary_w: raise RuntimeError('No extended display detected. Connect projector in Extend mode.')
        return primary_w,0,virtual_w-primary_w,virtual_h
    except AttributeError: raise RuntimeError('Windows extended display is required')

def show_white_projector():
    x,y,w,h=projector_geometry(); name='Living Pookalam - Projector'
    cv2.namedWindow(name,cv2.WINDOW_NORMAL)
    cv2.resizeWindow(name,w,h)
    cv2.moveWindow(name,x,y)
    cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
    cv2.imshow(name,np.full((h,w,3),255,np.uint8)); cv2.waitKey(200)
    return name

def validate(points,label):
    if len(points)!=4: raise ValueError(f'{label}: exactly four points required')
    pts=np.asarray(points,np.float32)
    if abs(cv2.contourArea(pts.reshape(-1,1,2)))<100: raise ValueError(f'{label}: area too small')
    return pts.tolist()

def inside(point,quad): return cv2.pointPolygonTest(np.asarray(quad,np.float32),tuple(point),False)>=0

def calibrate(camera_index):
    projector_window=show_white_projector()
    cap=cv2.VideoCapture(camera_index)
    if not cap.isOpened(): raise RuntimeError('Cannot open selected webcam')
    stage=0; points=[[],[]]; drag=[None]
    labels=[['TOP-LEFT','TOP-RIGHT','BOTTOM-RIGHT','BOTTOM-LEFT']]*2
    window='Living Pookalam - Calibration'; cv2.namedWindow(window,cv2.WINDOW_NORMAL)
    def mouse(event,x,y,flags,param):
        active=points[stage]
        if event==cv2.EVENT_LBUTTONDOWN:
            if len(active)<4: active.append([x,y])
            else:
                d=np.linalg.norm(np.asarray(active)-[x,y],axis=1)
                if d.min()<30: drag[0]=int(np.argmin(d))
        elif event==cv2.EVENT_MOUSEMOVE and drag[0] is not None and flags&cv2.EVENT_FLAG_LBUTTON: active[drag[0]]=[x,y]
        elif event==cv2.EVENT_LBUTTONUP: drag[0]=None
    cv2.setMouseCallback(window,mouse)
    while True:
        ok,frame=cap.read()
        if not ok: continue
        for s,pts in enumerate(points):
            color=(0,255,255) if s==0 else (0,255,0); prefix='P' if s==0 else 'F'
            for i,p in enumerate(pts):
                cv2.circle(frame,tuple(map(int,p)),8,color,-1); cv2.putText(frame,f'{prefix}{i+1}',tuple(map(int,np.asarray(p)+[10,-10])),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
            if len(pts)>1: cv2.polylines(frame,[np.asarray(pts,np.int32)],len(pts)==4,color,2)
        if len(points[stage])<4: hint=('PROJECTOR FIELD' if stage==0 else 'FLOOR BOUNDARY')+': click '+labels[stage][len(points[stage])]
        elif stage==0: hint='PROJECTOR FIELD READY - S=NEXT STAGE'
        else: hint='FLOOR READY - S=SAVE, U=UNDO, R=RESET, ESC=CANCEL'
        cv2.putText(frame,hint,(20,35),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2)
        cv2.imshow(window,frame); key=cv2.waitKey(1)&0xFF
        if key==27: break
        if key in (ord('r'),ord('R')): points[stage].clear()
        if key in (ord('u'),ord('U')) and points[stage]: points[stage].pop()
        if key in (ord('s'),ord('S')):
            try:
                if stage==0: validate(points[0],'Projector field'); stage=1
                else:
                    projector=validate(points[0],'Projector field'); floor=validate(points[1],'Floor boundary')
                    if not all(inside(p,projector) for p in floor): raise ValueError('Floor boundary must be inside projector field')
                    CONFIG.write_text(json.dumps({'version':VERSION,'camera_index':camera_index,'projector_field_camera':projector,'floor_boundary_camera':floor},indent=2)); print('Saved:',CONFIG); break
            except ValueError as e: print(e)
    cap.release(); cv2.destroyAllWindows()

def main(): mandatory_update_check(); calibrate(choose_camera())
if __name__=='__main__': main()

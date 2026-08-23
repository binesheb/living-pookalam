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
            print(f'Update required: {VERSION} -> {remote}')
            subprocess.run(['git','pull','--ff-only'],cwd=ROOT,check=True)
            os.execv(sys.executable,[sys.executable,*sys.argv])
    except Exception as exc: print(f'Update check unavailable: {exc}')

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

def choose_projector():
    try:
        import ctypes
        count=max(1,ctypes.windll.user32.GetSystemMetrics(80))
    except Exception: count=1
    print('Detected displays:',list(range(count)))
    while True:
        v=input('Projector display index: ').strip()
        if v.isdigit() and 0<=int(v)<count: return int(v)

def show_white_projector(index):
    name='Living Pookalam - Projector White Field'
    cv2.namedWindow(name,cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
    try:
        import ctypes
        width=ctypes.windll.user32.GetSystemMetrics(0)
        cv2.moveWindow(name,width*index,0)
    except Exception: pass
    cv2.imshow(name,np.full((1080,1920,3),255,np.uint8)); cv2.waitKey(100)
    return name

def validate(points,label):
    if len(points)!=4: raise ValueError(f'{label}: exactly four points required')
    pts=np.asarray(points,np.float32)
    if abs(cv2.contourArea(pts.reshape(-1,1,2)))<100: raise ValueError(f'{label}: area too small')
    return pts.tolist()

def point_inside_quad(point,quad):
    return cv2.pointPolygonTest(np.asarray(quad,np.float32),tuple(point),False)>=0

def calibrate(camera_index,projector_index):
    projector_window=show_white_projector(projector_index)
    cap=cv2.VideoCapture(camera_index)
    if not cap.isOpened(): raise RuntimeError('Cannot open selected webcam')
    stages=[('PROJECTOR FIELD',['TOP-LEFT','TOP-RIGHT','BOTTOM-RIGHT','BOTTOM-LEFT']),('FLOOR BOUNDARY',['TOP-LEFT','TOP-RIGHT','BOTTOM-RIGHT','BOTTOM-LEFT'])]
    stage=0; points=[[],[]]; drag=[None]
    window='Living Pookalam - Two Stage Calibration'; cv2.namedWindow(window,cv2.WINDOW_NORMAL)
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
        colors=[(0,255,255),(0,255,0)]
        for s,pts in enumerate(points):
            for i,p in enumerate(pts):
                cv2.circle(frame,tuple(map(int,p)),8,colors[s],-1)
                cv2.putText(frame,f'{"P" if s==0 else "F"}{i+1}',tuple(map(int,np.asarray(p)+[10,-10])),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
            if len(pts)>1: cv2.polylines(frame,[np.asarray(pts,np.int32)],len(pts)==4,colors[s],2)
        title,names=stages[stage]
        if len(points[stage])<4: hint=f'{title}: click {names[len(points[stage])]}'
        elif stage==0: hint='PROJECTOR FIELD READY - press S for FLOOR BOUNDARY'
        else: hint='FLOOR READY - drag pins, S=SAVE, U=UNDO, R=RESET, Esc=CANCEL'
        cv2.putText(frame,hint,(20,35),cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),2)
        cv2.putText(frame,'Yellow=P projector field | Green=F actual floor | White projector remains ON',(20,65),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
        cv2.imshow(window,frame); key=cv2.waitKey(1)&0xFF
        if key==27: break
        if key in (ord('r'),ord('R')): points[stage].clear()
        if key in (ord('u'),ord('U')) and points[stage]: points[stage].pop()
        if key in (ord('s'),ord('S')):
            try:
                if stage==0:
                    validate(points[0],'Projector field'); stage=1
                else:
                    projector_field=validate(points[0],'Projector field'); floor=validate(points[1],'Floor boundary')
                    if not all(point_inside_quad(p,projector_field) for p in floor): raise ValueError('Every floor boundary point must be inside the projector field')
                    CONFIG.write_text(json.dumps({'version':VERSION,'camera_index':camera_index,'projector_display_index':projector_index,'projector_field_camera':projector_field,'floor_boundary_camera':floor},indent=2))
                    print('Two-stage calibration saved to',CONFIG); break
            except ValueError as e: print(e)
    cap.release(); cv2.destroyWindow(window); cv2.destroyWindow(projector_window); cv2.destroyAllWindows()

def main():
    mandatory_update_check(); projector=choose_projector(); calibrate(choose_camera(),projector)
if __name__=='__main__': main()

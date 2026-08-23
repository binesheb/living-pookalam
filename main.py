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
    except Exception as exc:
        print(f'Update check unavailable: {exc}')

def cameras(limit=10):
    found=[]
    for i in range(limit):
        cap=cv2.VideoCapture(i)
        if cap.isOpened():
            ok,_=cap.read()
            if ok: found.append(i)
        cap.release()
    return found

def choose_camera():
    found=cameras()
    if not found: raise RuntimeError('No webcam found')
    print('Detected webcams:', ', '.join(map(str,found)))
    while True:
        value=input('Camera index: ').strip()
        if value.isdigit() and int(value) in found:return int(value)
        print('Choose one of:',found)

def projector_screens():
    screens=[]
    try:
        import ctypes
        user32=ctypes.windll.user32
        screens=list(range(max(1,user32.GetSystemMetrics(80))))
    except Exception:
        screens=[0]
    return screens

def choose_projector():
    screens=projector_screens()
    if len(screens)==1:
        print('Only one display detected. Using display 0 for the white calibration screen.')
        return 0
    print('Detected displays:', ', '.join(map(str,screens)))
    while True:
        value=input('Projector display index: ').strip()
        if value.isdigit() and int(value) in screens:return int(value)
        print('Choose one of:',screens)

def show_white_projector(display_index):
    name='Living Pookalam - Projector Alignment'
    cv2.namedWindow(name,cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
    # On Windows, OpenCV can move a fullscreen window to a secondary display.
    try:
        import ctypes
        user32=ctypes.windll.user32
        width=user32.GetSystemMetrics(0); height=user32.GetSystemMetrics(1)
        if display_index>0:
            cv2.moveWindow(name,width*(display_index),0)
    except Exception:
        pass
    white=np.full((1080,1920,3),255,dtype=np.uint8)
    cv2.imshow(name,white)
    cv2.waitKey(100)
    return name

def order_and_validate(points):
    if len(points)!=4: raise ValueError('Exactly four points required')
    pts=np.array(points,dtype=np.float32)
    area=cv2.contourArea(pts.reshape(-1,1,2))
    if abs(area)<100: raise ValueError('Selected area is too small')
    return pts

def calibrate(camera_index,projector_index):
    projector_window=show_white_projector(projector_index)
    cap=cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        cv2.destroyWindow(projector_window)
        raise RuntimeError('Cannot open selected webcam')
    points=[]; drag=[None]
    names=['TOP-LEFT','TOP-RIGHT','BOTTOM-RIGHT','BOTTOM-LEFT']
    window='Living Pookalam - Floor Calibration'
    cv2.namedWindow(window,cv2.WINDOW_NORMAL)
    def mouse(event,x,y,flags,param):
        if event==cv2.EVENT_LBUTTONDOWN:
            if len(points)<4: points.append([x,y])
            else:
                d=np.linalg.norm(np.array(points)-[x,y],axis=1); drag[0]=int(np.argmin(d)) if d.min()<30 else None
        elif event==cv2.EVENT_MOUSEMOVE and drag[0] is not None and flags&cv2.EVENT_FLAG_LBUTTON: points[drag[0]]=[x,y]
        elif event==cv2.EVENT_LBUTTONUP: drag[0]=None
    cv2.setMouseCallback(window,mouse)
    while True:
        ok,frame=cap.read()
        if not ok: continue
        for i,p in enumerate(points):
            cv2.circle(frame,tuple(map(int,p)),9,(0,0,255),-1)
            cv2.putText(frame,str(i+1),tuple(map(int,np.array(p)+[12,-12])),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
        if len(points)>1: cv2.polylines(frame,[np.array(points,np.int32)],len(points)==4,(0,255,0),2)
        step=names[len(points)] if len(points)<4 else 'DRAG TO ADJUST - S=SAVE, R=RESET, U=UNDO'
        cv2.putText(frame,'PROJECTOR WHITE SCREEN ON - Click: '+step,(20,35),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,0),2)
        cv2.imshow(window,frame); key=cv2.waitKey(1)&0xFF
        if key==27: break
        if key in (ord('r'),ord('R')): points.clear()
        if key in (ord('u'),ord('U')) and points: points.pop()
        if key in (ord('s'),ord('S')) and len(points)==4:
            try:
                pts=order_and_validate(points)
                CONFIG.write_text(json.dumps({'version':VERSION,'camera_index':camera_index,'projector_display_index':projector_index,'floor_points_camera':pts.tolist()},indent=2))
                print('Calibration saved to',CONFIG); break
            except ValueError as e: print(e)
    cap.release(); cv2.destroyWindow(window); cv2.destroyWindow(projector_window); cv2.destroyAllWindows()

def main():
    mandatory_update_check()
    projector=choose_projector()
    calibrate(choose_camera(),projector)
if __name__=='__main__': main()

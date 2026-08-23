import json, os, sys, subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import requests

VERSION='1.0.0'; ROOT=Path(__file__).resolve().parent; CONFIG=ROOT/'calibration.json'
VERSION_URL='https://raw.githubusercontent.com/binesheb/living-pookalam/main/version.txt'

def mandatory_update_check():
    try:
        remote=requests.get(VERSION_URL,timeout=5).text.strip()
        if remote and remote!=VERSION:
            subprocess.run(['git','pull','--ff-only'],cwd=ROOT,check=True); os.execv(sys.executable,[sys.executable,*sys.argv])
    except Exception as exc: print('Update check unavailable:',exc)

def cameras(limit=10):
    out=[]
    for i in range(limit):
        cap=cv2.VideoCapture(i)
        if cap.isOpened() and cap.read()[0]: out.append(i)
        cap.release()
    return out

def projector_geometry():
    import ctypes
    u=ctypes.windll.user32; pw=u.GetSystemMetrics(0); ph=u.GetSystemMetrics(1); vw=u.GetSystemMetrics(78); vh=u.GetSystemMetrics(79)
    if vw<=pw: raise RuntimeError('Connect projector in Extend display mode')
    return pw,0,vw-pw,vh

def calibrate(camera_index):
    x,y,w,h=projector_geometry(); pname='Living Pookalam - Projector'; cv2.namedWindow(pname,cv2.WINDOW_NORMAL); cv2.moveWindow(pname,x,y); cv2.setWindowProperty(pname,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN); cv2.imshow(pname,np.full((h,w,3),255,np.uint8))
    cap=cv2.VideoCapture(camera_index); points=[[],[]]; stage=0; drag=[None]; win='Living Pookalam - Calibration'; cv2.namedWindow(win)
    def mouse(e,a,b,f,p):
        active=points[stage]
        if e==cv2.EVENT_LBUTTONDOWN:
            if len(active)<4: active.append([a,b])
            elif np.linalg.norm(np.asarray(active)-[a,b],axis=1).min()<30: drag[0]=int(np.linalg.norm(np.asarray(active)-[a,b],axis=1).argmin())
        elif e==cv2.EVENT_MOUSEMOVE and drag[0] is not None and f&cv2.EVENT_FLAG_LBUTTON: active[drag[0]]=[a,b]
        elif e==cv2.EVENT_LBUTTONUP: drag[0]=None
    cv2.setMouseCallback(win,mouse)
    while True:
        ok,frame=cap.read()
        if not ok: continue
        for s,pts in enumerate(points):
            col=(0,255,255) if s==0 else (0,255,0); pre='P' if s==0 else 'F'
            for i,p in enumerate(pts): cv2.circle(frame,tuple(p),8,col,-1); cv2.putText(frame,f'{pre}{i+1}',(p[0]+10,p[1]-10),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
            if len(pts)>1: cv2.polylines(frame,[np.asarray(pts,np.int32)],len(pts)==4,col,2)
        cv2.putText(frame,('PROJECTOR FIELD' if stage==0 else 'FLOOR BOUNDARY')+f' - click point {len(points[stage])+1 if len(points[stage])<4 else "ready"} | S next/save | U undo | R reset | ESC cancel',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1)
        cv2.imshow(win,frame); k=cv2.waitKey(1)&255
        if k==27: break
        if k in (ord('r'),ord('R')): points[stage].clear()
        if k in (ord('u'),ord('U')) and points[stage]: points[stage].pop()
        if k in (ord('s'),ord('S')) and len(points[stage])==4:
            if stage==0: stage=1
            else:
                if not all(cv2.pointPolygonTest(np.asarray(points[0],np.float32),tuple(p),False)>=0 for p in points[1]): print('Floor must be inside projector field'); continue
                CONFIG.write_text(json.dumps({'camera_index':camera_index,'projector_field_camera':points[0],'floor_boundary_camera':points[1]},indent=2)); break
    cap.release(); cv2.destroyAllWindows()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Living Pookalam'); self.geometry('1000x700'); self.image_path=None; self.preview=None
        top=tk.Frame(self,padx=20,pady=20); top.pack(fill='x')
        tk.Label(top,text='LIVING POOKALAM',font=('Segoe UI',24,'bold')).pack(anchor='w')
        tk.Label(top,text='Select an image, calibrate the floor, then project.',font=('Segoe UI',11)).pack(anchor='w',pady=(0,15))
        bar=tk.Frame(top); bar.pack(anchor='w')
        tk.Button(bar,text='Select Image',command=self.select_image,width=18,height=2).pack(side='left',padx=(0,8))
        tk.Button(bar,text='Calibrate',command=self.start_calibration,width=18,height=2).pack(side='left')
        self.status=tk.Label(top,text='No image selected',anchor='w'); self.status.pack(fill='x',pady=12)
        self.canvas=tk.Label(self,text='IMAGE PREVIEW',font=('Segoe UI',16)); self.canvas.pack(expand=True,fill='both',padx=20,pady=20)
    def select_image(self):
        path=filedialog.askopenfilename(title='Select Pookalam Image',filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.webp'),('All files','*.*')])
        if not path: return
        try:
            img=Image.open(path).convert('RGB'); img.thumbnail((900,500)); self.preview=ImageTk.PhotoImage(img); self.canvas.configure(image=self.preview,text=''); self.image_path=path; self.status.configure(text=Path(path).name)
        except Exception as e: messagebox.showerror('Image Error',str(e))
    def start_calibration(self):
        found=cameras()
        if not found: messagebox.showerror('Camera','No webcam found'); return
        if len(found)==1: idx=found[0]
        else:
            value=tk.simpledialog.askinteger('Camera','Camera index: '+', '.join(map(str,found)),parent=self,minvalue=min(found),maxvalue=max(found));
            if value not in found: return
            idx=value
        try: self.withdraw(); calibrate(idx)
        except Exception as e: messagebox.showerror('Calibration Error',str(e))
        finally: self.deiconify()

def main(): mandatory_update_check(); App().mainloop()
if __name__=='__main__': main()

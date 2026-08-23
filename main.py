import json, os, sys, subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import cv2
import numpy as np
import requests

VERSION='1.0.1'; ROOT=Path(__file__).resolve().parent; CONFIG=ROOT/'calibration.json'
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
    u=ctypes.windll.user32; pw=u.GetSystemMetrics(0); vw=u.GetSystemMetrics(78); vh=u.GetSystemMetrics(79)
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
                if not all(cv2.pointPolygonTest(np.asarray(points[0],np.float32),tuple(p),False)>=0 for p in points[1]): continue
                CONFIG.write_text(json.dumps({'camera_index':camera_index,'projector_field_camera':points[0],'floor_boundary_camera':points[1]},indent=2)); break
    cap.release(); cv2.destroyAllWindows()

def project_image(image):
    if not CONFIG.exists(): raise RuntimeError('Calibrate first')
    cfg=json.loads(CONFIG.read_text()); x,y,pw,ph=projector_geometry()
    # The four floor points are an observed camera trapezoid representing an ideal physical square.
    # Map camera-space floor quad into normalized square coordinates, then place that square inside the projector field.
    floor=np.float32(cfg['floor_boundary_camera']); field=np.float32(cfg['projector_field_camera'])
    ideal=np.float32([[0,0],[1,0],[1,1],[0,1]])
    camera_to_floor=cv2.getPerspectiveTransform(floor,ideal)
    # Projector field is treated as the full projector rectangle; calibration establishes the camera-to-projector relation.
    proj_rect=np.float32([[0,0],[pw,0],[pw,ph],[0,ph]])
    camera_to_projector=cv2.getPerspectiveTransform(field,proj_rect)
    # Compose ideal-floor -> camera -> projector.
    floor_to_camera=np.linalg.inv(camera_to_floor); floor_to_projector=camera_to_projector @ floor_to_camera
    src=np.float32([[0,0],[image.shape[1]-1,0],[image.shape[1]-1,image.shape[0]-1],[0,image.shape[0]-1]])
    H=cv2.getPerspectiveTransform(src,np.float32([[0,0],[1,0],[1,1],[0,1]]))
    final=floor_to_projector @ H
    warped=cv2.warpPerspective(image,final,(pw,ph),flags=cv2.INTER_LINEAR,borderValue=(0,0,0))
    name='Living Pookalam - Projection'; cv2.namedWindow(name,cv2.WINDOW_NORMAL); cv2.moveWindow(name,x,y); cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN); cv2.imshow(name,warped)
    cv2.waitKey(0); cv2.destroyWindow(name)

class CropDialog(tk.Toplevel):
    def __init__(self,parent,path,done):
        super().__init__(parent); self.title('Crop Image'); self.done=done; self.original=Image.open(path).convert('RGB'); self.scale=min(900/self.original.width,600/self.original.height,1); self.display=self.original.resize((int(self.original.width*self.scale),int(self.original.height*self.scale)))
        self.canvas=tk.Canvas(self,width=self.display.width,height=self.display.height,cursor='crosshair'); self.canvas.pack(padx=10,pady=10); self.tkimg=ImageTk.PhotoImage(self.display); self.canvas.create_image(0,0,anchor='nw',image=self.tkimg); self.start=None; self.rect=None; self.box=None
        self.canvas.bind('<ButtonPress-1>',self.press); self.canvas.bind('<B1-Motion>',self.move); self.canvas.bind('<ButtonRelease-1>',self.release); tk.Button(self,text='Use Crop',command=self.accept).pack(pady=(0,10))
    def press(self,e): self.start=(e.x,e.y); self.rect=self.canvas.create_rectangle(e.x,e.y,e.x,e.y,outline='red',width=2)
    def move(self,e):
        if self.start: self.canvas.coords(self.rect,self.start[0],self.start[1],e.x,e.y)
    def release(self,e):
        if self.start: self.box=(self.start[0],self.start[1],e.x,e.y)
    def accept(self):
        if not self.box: self.done(self.original.copy()); self.destroy(); return
        x1,y1,x2,y2=self.box; x1,x2=sorted((x1,x2)); y1,y2=sorted((y1,y2)); box=[int(v/self.scale) for v in (x1,y1,x2,y2)]
        if box[2]-box[0]<2 or box[3]-box[1]<2: return
        self.done(self.original.crop(tuple(box))); self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Living Pookalam'); self.geometry('1000x760'); self.image=None; self.preview=None
        top=tk.Frame(self,padx=20,pady=20); top.pack(fill='x'); tk.Label(top,text='LIVING POOKALAM',font=('Segoe UI',24,'bold')).pack(anchor='w'); tk.Label(top,text='Crop → Calibrate → Project',font=('Segoe UI',11)).pack(anchor='w',pady=(0,15))
        bar=tk.Frame(top); bar.pack(anchor='w'); tk.Button(bar,text='Select & Crop Image',command=self.select_image,width=20,height=2).pack(side='left',padx=(0,8)); tk.Button(bar,text='Calibrate',command=self.start_calibration,width=16,height=2).pack(side='left',padx=8); tk.Button(bar,text='Project Image',command=self.project,width=16,height=2).pack(side='left')
        self.status=tk.Label(top,text='No image selected'); self.status.pack(anchor='w',pady=10); self.canvas=tk.Label(self,text='IMAGE PREVIEW',font=('Segoe UI',16)); self.canvas.pack(expand=True,fill='both',padx=20,pady=20)
    def set_image(self,img):
        self.image=img; p=img.copy(); p.thumbnail((900,520)); self.preview=ImageTk.PhotoImage(p); self.canvas.configure(image=self.preview,text=''); self.status.configure(text=f'Image ready: {img.width} × {img.height}')
    def select_image(self):
        path=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.webp')]);
        if path: CropDialog(self,path,self.set_image)
    def start_calibration(self):
        found=cameras();
        if not found: messagebox.showerror('Camera','No webcam found'); return
        idx=found[0] if len(found)==1 else simpledialog.askinteger('Camera','Camera index: '+', '.join(map(str,found)),parent=self)
        if idx not in found: return
        try: self.withdraw(); calibrate(idx); self.status.configure(text='Calibration saved')
        except Exception as e: messagebox.showerror('Calibration Error',str(e))
        finally: self.deiconify()
    def project(self):
        if self.image is None: messagebox.showerror('Image','Select and crop an image first'); return
        try: project_image(cv2.cvtColor(np.asarray(self.image),cv2.COLOR_RGB2BGR))
        except Exception as e: messagebox.showerror('Projection Error',str(e))

def main(): mandatory_update_check(); App().mainloop()
if __name__=='__main__': main()

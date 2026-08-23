import json, os, sys, subprocess, threading, time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import cv2
import numpy as np

VERSION='2.0.0'; ROOT=Path(__file__).resolve().parent; CONFIG=ROOT/'calibration.json'

def run_git_pull():
    r=subprocess.run(['git','pull','--ff-only'],cwd=ROOT,capture_output=True,text=True,timeout=60)
    return r.returncode==0,(r.stdout+r.stderr).strip()

def projector_geometry():
    import ctypes
    u=ctypes.windll.user32; pw=u.GetSystemMetrics(0); vh=u.GetSystemMetrics(79); vw=u.GetSystemMetrics(78)
    if vw<=pw: raise RuntimeError('Projector must be connected in Windows Extend mode')
    return pw,0,vw-pw,vh

def projector_window(name,image):
    x,y,w,h=projector_geometry(); cv2.namedWindow(name,cv2.WINDOW_NORMAL); cv2.resizeWindow(name,w,h); cv2.moveWindow(name,x,y); cv2.imshow(name,cv2.resize(image,(w,h))); cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN); return name

def cameras():
    out=[]
    for i in range(10):
        cap=cv2.VideoCapture(i,cv2.CAP_DSHOW)
        if cap.isOpened() and cap.read()[0]: out.append(i)
        cap.release()
    return out

def calibrate(idx):
    x,y,w,h=projector_geometry(); projector_window('Living Pookalam - Projector',np.full((h,w,3),255,np.uint8)); cap=cv2.VideoCapture(idx); pts=[[],[]]; stage=0; win='Calibration'
    def mouse(e,x,y,f,p):
        if e==cv2.EVENT_LBUTTONDOWN and len(pts[stage])<4: pts[stage].append([x,y])
    cv2.namedWindow(win); cv2.setMouseCallback(win,mouse)
    while True:
        ok,frame=cap.read()
        if not ok: continue
        for s,a in enumerate(pts):
            c=(0,255,255) if s==0 else (0,255,0)
            for i,p in enumerate(a): cv2.circle(frame,tuple(p),7,c,-1); cv2.putText(frame,str(i+1),(p[0]+8,p[1]-8),0,.6,c,2)
            if len(a)>1: cv2.polylines(frame,[np.array(a,np.int32)],len(a)==4,c,2)
        label='PROJECTOR FIELD' if stage==0 else 'FLOOR AREA'; cv2.putText(frame,label+' | click 4 corners | S next/save | U undo | R reset | ESC cancel',(15,30),0,.55,(255,255,255),2); cv2.imshow(win,frame); k=cv2.waitKey(1)&255
        if k==27: break
        if k in (ord('u'),ord('U')) and pts[stage]: pts[stage].pop()
        if k in (ord('r'),ord('R')): pts[stage].clear()
        if k in (ord('s'),ord('S')) and len(pts[stage])==4:
            if stage==0: stage=1
            else:
                if all(cv2.pointPolygonTest(np.array(pts[0],np.float32),tuple(p),False)>=0 for p in pts[1]): CONFIG.write_text(json.dumps({'camera_index':idx,'projector_field_camera':pts[0],'floor_boundary_camera':pts[1]},indent=2)); break
    cap.release(); cv2.destroyAllWindows()

def project_image(img):
    if not CONFIG.exists(): raise RuntimeError('Calibrate first')
    cfg=json.loads(CONFIG.read_text()); _,_,pw,ph=projector_geometry(); field=np.float32(cfg['projector_field_camera']); floor=np.float32(cfg['floor_boundary_camera']); unit=np.float32([[0,0],[1,0],[1,1],[0,1]]); rect=np.float32([[0,0],[pw,0],[pw,ph],[0,ph]])
    cam_to_proj=cv2.getPerspectiveTransform(field,rect); floor_to_cam=np.linalg.inv(cv2.getPerspectiveTransform(floor,unit)); floor_to_proj=cam_to_proj@floor_to_cam
    src=np.float32([[0,0],[img.shape[1]-1,0],[img.shape[1]-1,img.shape[0]-1],[0,img.shape[0]-1]]); H=floor_to_proj@cv2.getPerspectiveTransform(src,unit); warped=cv2.warpPerspective(img,H,(pw,ph),borderValue=(0,0,0)); name=projector_window('Living Pookalam - Projection',warped)
    while cv2.waitKey(30)&255 not in (27,ord('q'),ord('Q')): pass
    cv2.destroyWindow(name)

def vision_debug():
    if not CONFIG.exists(): raise RuntimeError('Calibrate first')
    c=json.loads(CONFIG.read_text()); cap=cv2.VideoCapture(c['camera_index']); field=np.float32(c['projector_field_camera']); floor=np.float32(c['floor_boundary_camera']); unit=np.float32([[0,0],[640,0],[640,640],[0,640]]); H=cv2.getPerspectiveTransform(floor,unit); prev=None
    while True:
        ok,frame=cap.read()
        if not ok: continue
        gray=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(7,7),0); motion=np.zeros_like(gray) if prev is None else cv2.threshold(cv2.absdiff(gray,prev),25,255,cv2.THRESH_BINARY)[1]; prev=gray
        mask=np.zeros_like(gray); cv2.fillPoly(mask,[field.astype(np.int32)],255); motion=cv2.bitwise_and(motion,mask); motion=cv2.dilate(motion,None,iterations=2)
        rectified=cv2.warpPerspective(frame,H,(640,640)); rgray=cv2.cvtColor(rectified,cv2.COLOR_BGR2GRAY); rmask=cv2.threshold(rgray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]; contours,_=cv2.findContours(rmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); data=[]
        for q in contours:
            a=cv2.contourArea(q)
            if a<500: continue
            x,y,w,h=cv2.boundingRect(q); data.append((round((x+w/2)/640,3),round((y+h/2)/640,3),round(a/(640*640),4))); cv2.rectangle(rectified,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.polylines(frame,[field.astype(np.int32)],True,(0,255,255),2); cv2.polylines(frame,[floor.astype(np.int32)],True,(0,255,0),2); cv2.putText(frame,f'MOTION: {int(np.count_nonzero(motion))} px | OBJECTS: {len(data)}',(15,30),0,.65,(0,0,255),2); cv2.imshow('Vision - Full Projected Area',frame); cv2.imshow('Vision - Rectified Floor',rectified)
        if cv2.waitKey(1)&255 in (27,ord('q'),ord('Q')): break
    cap.release(); cv2.destroyAllWindows()

class Crop(tk.Toplevel):
    def __init__(self,parent,path,done):
        super().__init__(parent); self.done=done; self.src=Image.open(path).convert('RGB'); self.s=min(900/self.src.width,600/self.src.height,1); d=self.src.resize((int(self.src.width*self.s),int(self.src.height*self.s))); self.c=tk.Canvas(self,width=d.width,height=d.height,cursor='crosshair'); self.c.pack(); self.i=ImageTk.PhotoImage(d); self.c.create_image(0,0,anchor='nw',image=self.i); self.a=None; self.box=None; self.r=None; self.c.bind('<Button-1>',self.down); self.c.bind('<B1-Motion>',self.drag); self.c.bind('<ButtonRelease-1>',self.up); tk.Button(self,text='Use Crop',command=self.ok).pack(pady=8)
    def down(self,e): self.a=(e.x,e.y); self.r=self.c.create_rectangle(e.x,e.y,e.x,e.y,outline='red',width=2)
    def drag(self,e):
        if self.a:self.c.coords(self.r,*self.a,e.x,e.y)
    def up(self,e): self.box=(*self.a,e.x,e.y)
    def ok(self):
        if self.box:
            x1,y1,x2,y2=self.box; x1,x2=sorted((x1,x2)); y1,y2=sorted((y1,y2)); b=tuple(int(v/self.s) for v in (x1,y1,x2,y2)); self.done(self.src.crop(b))
        else:self.done(self.src.copy())
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('Living Pookalam'); self.geometry('1050x760'); self.image=None; self.preview=None; top=tk.Frame(self,padx=20,pady=18); top.pack(fill='x'); tk.Label(top,text='LIVING POOKALAM',font=('Segoe UI',25,'bold')).pack(anchor='w'); tk.Label(top,text='Upload • Crop • Calibrate • Understand • Interact • Project',font=('Segoe UI',11)).pack(anchor='w'); bar=tk.Frame(top); bar.pack(anchor='w',pady=14)
        for text,cmd in [('Select & Crop',self.select),('Calibrate',self.cal),('Project',self.project),('Vision Debug',self.vision),('Update from GitHub',self.update)]: tk.Button(bar,text=text,command=cmd,width=18,height=2).pack(side='left',padx=3)
        self.status=tk.Label(top,text='Ready'); self.status.pack(anchor='w'); self.view=tk.Label(self,text='IMAGE PREVIEW',font=('Segoe UI',16)); self.view.pack(expand=True,fill='both',padx=20,pady=20)
    def select(self):
        p=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.webp')]);
        if p: Crop(self,p,self.setimg)
    def setimg(self,img): self.image=img; p=img.copy(); p.thumbnail((900,520)); self.preview=ImageTk.PhotoImage(p); self.view.configure(image=self.preview,text=''); self.status.configure(text=f'Image ready: {img.width} x {img.height}')
    def cal(self):
        cs=cameras();
        if not cs:return messagebox.showerror('Camera','No camera found')
        idx=cs[0] if len(cs)==1 else simpledialog.askinteger('Camera','Camera index: '+', '.join(map(str,cs)),parent=self)
        if idx in cs:
            self.withdraw()
            try: calibrate(idx); self.status.configure(text='Calibration saved')
            except Exception as e: messagebox.showerror('Calibration',str(e))
            self.deiconify()
    def project(self):
        if self.image is None:return messagebox.showerror('Image','Select an image first')
        self.withdraw()
        try: project_image(cv2.cvtColor(np.array(self.image),cv2.COLOR_RGB2BGR))
        except Exception as e: messagebox.showerror('Projection',str(e))
        self.deiconify()
    def vision(self):
        self.withdraw()
        try: vision_debug()
        except Exception as e: messagebox.showerror('Vision',str(e))
        self.deiconify()
    def update(self):
        self.status.configure(text='Updating from GitHub...'); self.update_idletasks()
        def work():
            try:
                ok,msg=run_git_pull(); self.after(0,lambda: messagebox.showinfo('GitHub Update','Update complete. Restart the application.\n\n'+msg) if ok else messagebox.showerror('GitHub Update',msg))
            except Exception as e:self.after(0,lambda: messagebox.showerror('GitHub Update',str(e)))
            self.after(0,lambda:self.status.configure(text='Ready'))
        threading.Thread(target=work,daemon=True).start()

def main(): App().mainloop()
if __name__=='__main__': main()

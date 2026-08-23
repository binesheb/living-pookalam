import json, subprocess, threading, time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import cv2, numpy as np

VERSION='2.4.0'; ROOT=Path(__file__).resolve().parent; CONFIG=ROOT/'calibration.json'
DEBUG_NAMES=['Debug - Camera','Debug - Scene Baseline','Debug - Field Difference','Debug - Field Mask','Debug - Floor Live','Debug - Floor Baseline','Debug - Floor Difference','Debug - Floor Mask','Interactive Pookalam - Learning Baseline']
def run_git_pull():
 r=subprocess.run(['git','pull','--ff-only'],cwd=ROOT,capture_output=True,text=True,timeout=60); return r.returncode==0,(r.stdout+r.stderr).strip()
def projector_geometry():
 import ctypes; u=ctypes.windll.user32; pw=u.GetSystemMetrics(0); vw=u.GetSystemMetrics(78); vh=u.GetSystemMetrics(79)
 if vw<=pw: raise RuntimeError('Projector must be connected in Windows Extend mode')
 return pw,0,vw-pw,vh
def projector_window(name,image):
 x,y,w,h=projector_geometry(); cv2.namedWindow(name,cv2.WINDOW_NORMAL); cv2.moveWindow(name,x,y); cv2.resizeWindow(name,w,h); cv2.imshow(name,cv2.resize(image,(w,h))); cv2.waitKey(50); cv2.moveWindow(name,x,y); cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN); cv2.waitKey(50); return name
def cameras():
 out=[]
 for i in range(10):
  cap=cv2.VideoCapture(i,cv2.CAP_DSHOW)
  if cap.isOpened() and cap.read()[0]: out.append(i)
  cap.release()
 return out
def calibration(idx):
 _,_,w,h=projector_geometry(); projector_window('LP Projector',np.full((h,w,3),255,np.uint8)); cap=cv2.VideoCapture(idx); pts=[[],[]]; stage=0; win='Calibration'
 def mouse(e,x,y,f,p):
  if e==cv2.EVENT_LBUTTONDOWN and len(pts[stage])<4: pts[stage].append([x,y])
 cv2.namedWindow(win); cv2.setMouseCallback(win,mouse)
 while True:
  ok,frame=cap.read()
  if not ok: continue
  for s,a in enumerate(pts):
   col=(0,255,255) if s==0 else (0,255,0)
   for i,p in enumerate(a): cv2.circle(frame,tuple(p),7,col,-1); cv2.putText(frame,str(i+1),(p[0]+8,p[1]-8),0,.6,col,2)
   if len(a)>1: cv2.polylines(frame,[np.array(a,np.int32)],len(a)==4,col,2)
  label='PROJECTOR FIELD' if stage==0 else 'FLOOR INTERACTION AREA'; cv2.putText(frame,label+' | 4 corners | S next/save | U undo | R reset | ESC cancel',(15,30),0,.55,(255,255,255),2); cv2.imshow(win,frame); k=cv2.waitKey(1)&255
  if k==27: break
  if k in (ord('u'),ord('U')) and pts[stage]: pts[stage].pop()
  if k in (ord('r'),ord('R')): pts[stage].clear()
  if k in (ord('s'),ord('S')) and len(pts[stage])==4:
   if stage==0: stage=1
   elif all(cv2.pointPolygonTest(np.array(pts[0],np.float32),tuple(p),False)>=0 for p in pts[1]): CONFIG.write_text(json.dumps({'camera_index':idx,'projector_field_camera':pts[0],'floor_boundary_camera':pts[1]},indent=2)); break
 cap.release(); cv2.destroyAllWindows()
def build_projection(img,cfg):
 _,_,pw,ph=projector_geometry(); field=np.float32(cfg['projector_field_camera']); floor=np.float32(cfg['floor_boundary_camera']); unit=np.float32([[0,0],[1,0],[1,1],[0,1]]); rect=np.float32([[0,0],[pw,0],[pw,ph],[0,ph]])
 cam_to_proj=cv2.getPerspectiveTransform(field,rect); floor_to_cam=np.linalg.inv(cv2.getPerspectiveTransform(floor,unit)); src=np.float32([[0,0],[img.shape[1]-1,0],[img.shape[1]-1,img.shape[0]-1],[0,img.shape[0]-1]])
 return cv2.warpPerspective(img,(cam_to_proj@floor_to_cam)@cv2.getPerspectiveTransform(src,unit),(pw,ph),borderValue=(0,0,0))
def learn_baseline(cap,field,Hfloor,stop_event,seconds=10,debug=False):
 samples=[]; floors=[]; start=time.time(); last=0
 while time.time()-start<seconds and not stop_event.is_set():
  ok,frame=cap.read()
  if not ok: continue
  now=time.time()
  if now-last<0.12: continue
  last=now; floor=cv2.warpPerspective(frame,Hfloor,(640,640)); samples.append(frame.copy()); floors.append(floor)
  remain=max(0,int(seconds-(now-start)+.99)); view=frame.copy(); cv2.polylines(view,[field.astype(np.int32)],True,(0,255,255),2); cv2.putText(view,f'LEARNING PROJECTED SCENE - KEEP CLEAR - {remain}s',(15,35),0,.8,(0,0,255),2)
  if debug: cv2.imshow('Interactive Pookalam - Learning Baseline',view); cv2.imshow('Debug - Camera',frame); cv2.imshow('Debug - Floor Live',floor)
  cv2.waitKey(1)
 if stop_event.is_set() or not samples:return None,None
 return np.median(np.stack(samples).astype(np.float32),axis=0).astype(np.uint8),np.median(np.stack(floors).astype(np.float32),axis=0).astype(np.uint8)
def difference(a,b,threshold=35):
 d=cv2.absdiff(cv2.GaussianBlur(cv2.cvtColor(a,cv2.COLOR_BGR2GRAY),(7,7),0),cv2.GaussianBlur(cv2.cvtColor(b,cv2.COLOR_BGR2GRAY),(7,7),0)); return d,cv2.threshold(d,threshold,255,cv2.THRESH_BINARY)[1]
def debug_close():
 for n in DEBUG_NAMES:
  try: cv2.destroyWindow(n)
  except: pass
def interaction_loop(img,stop_event,debug_event):
 if not CONFIG.exists(): raise RuntimeError('Calibrate first')
 cfg=json.loads(CONFIG.read_text()); _,_,pw,ph=projector_geometry(); stable=build_projection(img,cfg); pname=projector_window('Living Pookalam - Projection',stable); cap=cv2.VideoCapture(cfg['camera_index']); field=np.float32(cfg['projector_field_camera']); floor=np.float32(cfg['floor_boundary_camera']); F=np.float32([[0,0],[pw,0],[pw,ph],[0,ph]]); S=np.float32([[0,0],[640,0],[640,640],[0,640]]); Hfield=cv2.getPerspectiveTransform(field,F); Hfloor=cv2.getPerspectiveTransform(floor,S)
 scene_base,floor_base=learn_baseline(cap,field,Hfloor,stop_event,debug=debug_event.is_set())
 if scene_base is None: cap.release(); return
 kernel=np.ones((5,5),np.uint8); pulses=[]; frame_count=0; tick=time.time(); fps=0
 while not stop_event.is_set():
  ok,frame=cap.read()
  if not ok: continue
  debug=debug_event.is_set(); frame_count+=1
  if time.time()-tick>=1: fps=frame_count/(time.time()-tick); frame_count=0; tick=time.time()
  fdiff,motion=difference(frame,scene_base); fieldmask=np.zeros(motion.shape,np.uint8); cv2.fillPoly(fieldmask,[field.astype(np.int32)],255); motion=cv2.morphologyEx(cv2.bitwise_and(motion,fieldmask),cv2.MORPH_OPEN,kernel); motion=cv2.dilate(motion,None,iterations=2); cnt,_=cv2.findContours(motion,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); global_hits=[]
  for q in cnt:
   if cv2.contourArea(q)<250: continue
   m=cv2.moments(q)
   if not m['m00']:continue
   cx,cy=m['m10']/m['m00'],m['m01']/m['m00']; p=cv2.perspectiveTransform(np.float32([[[cx,cy]]]),Hfield)[0,0]; global_hits.append(p); pulses.append([float(p[0]),float(p[1]),time.time()])
  rectified=cv2.warpPerspective(frame,Hfloor,(640,640)); rdiff,rmask=difference(rectified,floor_base); rmask=cv2.morphologyEx(rmask,cv2.MORPH_OPEN,kernel); rmask=cv2.dilate(rmask,None,iterations=2); contours,_=cv2.findContours(rmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); interactions=[]; floor_debug=rectified.copy()
  for q in contours:
   if cv2.contourArea(q)<500:continue
   x,y,w,h=cv2.boundingRect(q); u,v=(x+w/2)/640,(y+h/2)/640; interactions.append((u,v)); cv2.rectangle(floor_debug,(x,y),(x+w,y+h),(0,255,0),2); cv2.putText(floor_debug,f'{u:.3f},{v:.3f}',(x,max(15,y-5)),0,.45,(0,255,0),1)
  effect=stable.copy(); now=time.time(); pulses=[z for z in pulses if now-z[2]<1.2]
  for x,y,t in pulses:
   age=now-t; radius=int(35+age*180); layer=effect.copy(); cv2.circle(layer,(int(x),int(y)),radius,(255,255,255),max(1,4-int(age*2))); effect=cv2.addWeighted(effect,.92,layer,.08,0)
  cv2.imshow(pname,effect)
  if debug:
   view=frame.copy(); cv2.polylines(view,[field.astype(np.int32)],True,(0,255,255),2); cv2.polylines(view,[floor.astype(np.int32)],True,(0,255,0),2); cv2.putText(view,f'DEBUG | FPS {fps:.1f} | FIELD {len(global_hits)} | FLOOR {len(interactions)}',(15,30),0,.65,(0,0,255),2)
   cv2.imshow('Debug - Camera',view); cv2.imshow('Debug - Scene Baseline',scene_base); cv2.imshow('Debug - Field Difference',fdiff); cv2.imshow('Debug - Field Mask',motion); cv2.imshow('Debug - Floor Live',floor_debug); cv2.imshow('Debug - Floor Baseline',floor_base); cv2.imshow('Debug - Floor Difference',rdiff); cv2.imshow('Debug - Floor Mask',rmask)
  else: debug_close()
  cv2.waitKey(1)
 cap.release(); debug_close(); cv2.destroyAllWindows()
class Crop(tk.Toplevel):
 def __init__(self,parent,path,done):
  super().__init__(parent); self.title('Crop Pookalam Image'); self.done=done; self.src=Image.open(path).convert('RGB'); self.s=min(900/self.src.width,600/self.src.height,1); d=self.src.resize((int(self.src.width*self.s),int(self.src.height*self.s))); self.c=tk.Canvas(self,width=d.width,height=d.height,cursor='crosshair'); self.c.pack(padx=10,pady=10); self.i=ImageTk.PhotoImage(d); self.c.create_image(0,0,anchor='nw',image=self.i); self.a=self.box=self.r=None; self.c.bind('<Button-1>',self.down); self.c.bind('<B1-Motion>',self.drag); self.c.bind('<ButtonRelease-1>',self.up); tk.Button(self,text='Use Crop',command=self.ok,width=18).pack(pady=8)
 def down(self,e): self.a=(e.x,e.y); self.r=self.c.create_rectangle(e.x,e.y,e.x,e.y)
 def drag(self,e):
  if self.a:self.c.coords(self.r,*self.a,e.x,e.y)
 def up(self,e): self.box=(*self.a,e.x,e.y)
 def ok(self):
  if self.box:
   x1,y1,x2,y2=self.box; x1,x2=sorted((x1,x2)); y1,y2=sorted((y1,y2)); self.done(self.src.crop(tuple(int(v/self.s) for v in (x1,y1,x2,y2))))
  else:self.done(self.src.copy())
  self.destroy()
class App(tk.Tk):
 def __init__(self):
  super().__init__(); self.title('Interactive Pookalam'); self.geometry('1120x780'); self.image=None; self.preview=None; self.stop=threading.Event(); self.debug=threading.Event(); self.worker=None; top=tk.Frame(self,padx=24,pady=20); top.pack(fill='x'); tk.Label(top,text='INTERACTIVE POOKALAM',font=('Segoe UI',26,'bold')).pack(anchor='w'); tk.Label(top,text='Stable projected reference + external interaction detection',font=('Segoe UI',11)).pack(anchor='w'); bar=tk.Frame(top); bar.pack(anchor='w',pady=16)
  for text,cmd in [('Select & Crop',self.select),('Calibrate Zones',self.cal),('Start Interactive',self.project),('Debug: OFF',self.toggle_debug),('Stop',self.stop_projection),('Close App',self.close_app),('Update from GitHub',self.update)]: tk.Button(bar,text=text,command=cmd,width=17,height=2).pack(side='left',padx=3)
  self.debug_button=bar.winfo_children()[-4]; self.status=tk.Label(top,text='Ready'); self.status.pack(anchor='w'); self.view=tk.Label(self,text='POOKALAM REFERENCE IMAGE',font=('Segoe UI',16)); self.view.pack(expand=True,fill='both',padx=20,pady=20); self.protocol('WM_DELETE_WINDOW',self.close_app)
 def toggle_debug(self):
  if self.debug.is_set(): self.debug.clear(); self.debug_button.configure(text='Debug: OFF'); debug_close(); self.status.configure(text='Debug mode disabled')
  else:self.debug.set(); self.debug_button.configure(text='Debug: ON'); self.status.configure(text='Debug mode enabled')
 def select(self):
  p=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp *.webp')]);
  if p:Crop(self,p,self.setimg)
 def setimg(self,img):
  self.image=img; p=img.copy(); p.thumbnail((1000,560)); self.preview=ImageTk.PhotoImage(p); self.view.configure(image=self.preview,text=''); self.status.configure(text=f'Reference image ready: {img.width} x {img.height}')
 def cal(self):
  cs=cameras()
  if not cs:return messagebox.showerror('Camera','No camera found')
  idx=cs[0] if len(cs)==1 else simpledialog.askinteger('Camera','Camera index: '+', '.join(map(str,cs)),parent=self)
  if idx in cs:
   try:self.withdraw(); calibration(idx); self.status.configure(text='Both interaction zones saved')
   except Exception as e:messagebox.showerror('Calibration',str(e))
   finally:self.deiconify()
 def project(self):
  if self.image is None:return messagebox.showerror('Image','Select a reference image first')
  if self.worker and self.worker.is_alive():return
  self.stop.clear(); img=cv2.cvtColor(np.array(self.image),cv2.COLOR_RGB2BGR); self.status.configure(text='Learning stable projected scene for 10 seconds - keep clear')
  def work():
   try:interaction_loop(img,self.stop,self.debug)
   except Exception as e:self.after(0,lambda:messagebox.showerror('Interactive Pookalam',str(e)))
   finally:self.after(0,lambda:self.status.configure(text='Stopped'))
  self.worker=threading.Thread(target=work,daemon=True); self.worker.start()
 def stop_projection(self):self.stop.set(); self.status.configure(text='Stopping...')
 def close_app(self):self.stop.set(); debug_close(); cv2.destroyAllWindows(); self.destroy()
 def update(self):
  self.status.configure(text='Updating from GitHub...'); self.update_idletasks()
  def work():
   try:
    ok,msg=run_git_pull(); self.after(0,lambda:messagebox.showinfo('GitHub Update','Update complete. Restart the application.\n\n'+msg) if ok else messagebox.showerror('GitHub Update',msg))
   except Exception as e:self.after(0,lambda:messagebox.showerror('GitHub Update',str(e)))
   self.after(0,lambda:self.status.configure(text='Ready'))
  threading.Thread(target=work,daemon=True).start()
def main():App().mainloop()
if __name__=='__main__':main()

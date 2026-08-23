import json,subprocess,threading,time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog,messagebox
from PIL import Image,ImageTk
import cv2,numpy as np
from auto_calibration import run as auto_run
VERSION='3.3.1';ROOT=Path(__file__).resolve().parent;CONFIG=ROOT/'calibration.json'
DEBUG_NAMES=['Debug - Camera','Debug - Floor Live','Debug - Pookalam Source','Debug - Pookalam Detection','LP Auto Calibration']
BG='#101522';PANEL='#192133';PANEL2='#222c40';TEXT='#eef3ff';MUTED='#9ba9c3';ACCENT='#f4b942';RED='#ef6b73';BLUE='#6395ff'
def projector_geometry():
 import ctypes;u=ctypes.windll.user32;pw=u.GetSystemMetrics(0);vw=u.GetSystemMetrics(78);vh=u.GetSystemMetrics(79)
 if vw<=pw:raise RuntimeError('Projector must be connected in Windows Extend mode')
 return pw,0,vw-pw,vh
def projector_window(name,image):
 x,y,w,h=projector_geometry();cv2.namedWindow(name,cv2.WINDOW_NORMAL);cv2.moveWindow(name,x,y);cv2.resizeWindow(name,w,h);cv2.imshow(name,cv2.resize(image,(w,h)));cv2.waitKey(30);cv2.setWindowProperty(name,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN);return name
def cameras():
 out=[]
 for i in range(10):
  c=cv2.VideoCapture(i,cv2.CAP_DSHOW)
  if c.isOpened() and c.read()[0]:out.append(i)
  c.release()
 return out
def calibration(idx):
 _,_,w,h=projector_geometry();projector_window('LP Projector',np.full((h,w,3),255,np.uint8));cap=cv2.VideoCapture(idx);pts=[[],[]];stage=0
 def mouse(e,x,y,f,p):
  if e==cv2.EVENT_LBUTTONDOWN and len(pts[stage])<4:pts[stage].append([x,y])
 cv2.namedWindow('Calibration');cv2.setMouseCallback('Calibration',mouse)
 while True:
  ok,fr=cap.read()
  if not ok:continue
  for s,a in enumerate(pts):
   col=(0,255,255) if s==0 else (0,255,0)
   for i,p in enumerate(a):cv2.circle(fr,tuple(p),7,col,-1);cv2.putText(fr,str(i+1),(p[0]+8,p[1]-8),0,.6,col,2)
   if len(a)>1:cv2.polylines(fr,[np.array(a,np.int32)],len(a)==4,col,2)
  cv2.putText(fr,('PROJECTOR FIELD' if stage==0 else 'FLOOR AREA')+' | click 4 corners | S next/save | U undo | ESC cancel',(12,30),0,.55,(255,255,255),2);cv2.imshow('Calibration',fr);k=cv2.waitKey(1)&255
  if k==27:break
  if k in(85,117) and pts[stage]:pts[stage].pop()
  if k in(83,115) and len(pts[stage])==4:
   if stage==0:stage=1
   else:CONFIG.write_text(json.dumps({'camera_index':idx,'projector_field_camera':pts[0],'floor_boundary_camera':pts[1]},indent=2));break
 cap.release();cv2.destroyAllWindows()
def learn_baseline(cap,field,Hfloor,stop_event,seconds=10,debug=False):
 samples=[];floors=[];start=time.perf_counter();last=0
 while time.perf_counter()-start<seconds and not stop_event.is_set():
  ok,f=cap.read()
  if not ok:continue
  now=time.perf_counter()
  if now-last<.12:continue
  last=now;samples.append(f.copy());floors.append(cv2.warpPerspective(f,Hfloor,(640,640)));cv2.waitKey(1)
 if stop_event.is_set() or not samples:return None,None
 return np.median(np.stack(samples),axis=0).astype(np.uint8),np.median(np.stack(floors),axis=0).astype(np.uint8)
def difference(a,b,threshold=35):
 d=cv2.absdiff(cv2.GaussianBlur(cv2.cvtColor(a,cv2.COLOR_BGR2GRAY),(7,7),0),cv2.GaussianBlur(cv2.cvtColor(b,cv2.COLOR_BGR2GRAY),(7,7),0));return d,cv2.threshold(d,threshold,255,cv2.THRESH_BINARY)[1]
def debug_close():
 for n in DEBUG_NAMES:
  try:cv2.destroyWindow(n)
  except:pass
def build_projection(img,cfg):
 _,_,pw,ph=projector_geometry()
 if img is None:return np.zeros((ph,pw,3),np.uint8)
 field=np.float32(cfg['projector_field_camera']);floor=np.float32(cfg['floor_boundary_camera']);H1=cv2.getPerspectiveTransform(field,np.float32([[0,0],[pw,0],[pw,ph],[0,ph]]));H2=np.linalg.inv(cv2.getPerspectiveTransform(floor,np.float32([[0,0],[1,0],[1,1],[0,1]])));src=np.float32([[0,0],[img.shape[1]-1,0],[img.shape[1]-1,img.shape[0]-1],[0,img.shape[0]-1]]);return cv2.warpPerspective(img,(H1@H2)@cv2.getPerspectiveTransform(src,np.float32([[0,0],[1,0],[1,1],[0,1]])),(pw,ph))
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('Living Pookalam');self.geometry('900x650');self.configure(bg=BG);self.image=None;self.worker=None;self.stop=threading.Event();self.debug=threading.Event()
  left=tk.Frame(self,bg=PANEL,width=280);left.pack(side='left',fill='y');tk.Label(left,text='LIVING\nPOOKALAM',font=('Segoe UI',24,'bold'),bg=PANEL,fg=TEXT).pack(pady=35)
  self.buttons=[('Upload & Crop',self.select,ACCENT,'#111'),('Calibrate Zones',self.cal,PANEL2,TEXT),('Auto Calibrate',self.auto_calibrate,BLUE,'white'),('Start Experience',self.project,ACCENT,'#111'),('Debug: OFF',self.toggle_debug,PANEL2,TEXT),('Stop Experience',self.stop_projection,RED,'white'),('Update from GitHub',self.update,PANEL2,TEXT),('Close',self.close_app,PANEL2,TEXT)]
  for title,cmd,bg,fg in self.buttons:tk.Button(left,text=title,command=cmd,bg=bg,fg=fg,relief='flat',padx=20,pady=12).pack(fill='x',padx=18,pady=4)
  self.status=tk.Label(self,text='Ready',font=('Segoe UI',15),bg=BG,fg=TEXT);self.status.pack(pady=35);self.view=tk.Label(self,text='No image uploaded — physical Pookalam detection will be used',bg=PANEL2,fg=MUTED,font=('Segoe UI',14),wraplength=500);self.view.pack(expand=True,fill='both',padx=40,pady=40)
 def set_state(self,text,*_):self.status.configure(text=text)
 def select(self):
  p=filedialog.askopenfilename(filetypes=[('Images','*.png *.jpg *.jpeg *.bmp')])
  if not p:return
  self.image=Image.open(p).convert('RGB');d=self.image.copy();d.thumbnail((500,500));self.preview=ImageTk.PhotoImage(d);self.view.configure(image=self.preview,text='')
 def cal(self):
  cs=cameras()
  if cs:threading.Thread(target=lambda:calibration(cs[0]),daemon=True).start()
 def auto_calibrate(self):
  if self.worker and self.worker.is_alive():return
  cs=cameras()
  if not cs:messagebox.showerror('Auto Calibration','No camera found');return
  idx=cs[0];self.stop.clear();self.set_state('Auto calibration: projecting and detecting markers...')
  def work():
   cap=cv2.VideoCapture(idx)
   try:
    _,_,pw,ph=projector_geometry();win=projector_window('LP Auto Calibration',np.full((ph,pw,3),255,np.uint8));result=auto_run(cap,lambda im:(cv2.imshow(win,cv2.resize(im,(pw,ph))),cv2.waitKey(1)),(pw,ph),stop=self.stop)
    if result is None or result['quality']<.35:raise RuntimeError('Marker detection quality too low. Reposition camera/projector and try again.')
    frame=None
    for _ in range(15):ok,frame=cap.read()
    if frame is None:raise RuntimeError('Camera frame unavailable')
    from pookalam_vision import detect_pookalam
    v=detect_pookalam(frame);c=np.array(v['center'],float);r=max(60,v['radius']);floor=np.array([[c[0]-r,c[1]-r],[c[0]+r,c[1]-r],[c[0]+r,c[1]+r],[c[0]-r,c[1]+r]],float)
    field=np.array(result['projector_field_camera'],float);floor[:,0]=np.clip(floor[:,0],field[:,0].min(),field[:,0].max());floor[:,1]=np.clip(floor[:,1],field[:,1].min(),field[:,1].max())
    CONFIG.write_text(json.dumps({'camera_index':idx,'projector_field_camera':result['projector_field_camera'],'floor_boundary_camera':floor.tolist(),'auto_calibrated':True,'quality':result['quality'],'pookalam_confidence':v['confidence']},indent=2));self.after(0,lambda:self.set_state(f"Auto calibration complete — projector {result['quality']:.0%}, Pookalam {v['confidence']:.0%}"))
   except Exception as e:self.after(0,lambda:messagebox.showerror('Auto Calibration',str(e)))
   finally:cap.release();cv2.destroyAllWindows()
  self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
 def project(self):
  if not CONFIG.exists():messagebox.showerror('Living Pookalam','Calibrate first');return
  from launcher import interaction_with_effects
  img=None if self.image is None else cv2.cvtColor(np.array(self.image),cv2.COLOR_RGB2BGR);self.stop.clear();self.worker=threading.Thread(target=lambda:interaction_with_effects(img,self.stop,self.debug,self.set_state),daemon=True);self.worker.start()
 def toggle_debug(self):
  if self.debug.is_set():self.debug.clear();self.set_state('Debug disabled')
  else:self.debug.set();self.set_state('Debug enabled')
 def stop_projection(self):self.stop.set();debug_close();cv2.destroyAllWindows();self.set_state('Experience stopped')
 def update(self):
  try:r=subprocess.run(['git','pull','--ff-only'],cwd=ROOT,capture_output=True,text=True,timeout=60);messagebox.showinfo('Update',r.stdout+r.stderr)
  except Exception as e:messagebox.showerror('Update',str(e))
 def close_app(self):self.stop_projection();self.destroy()
def main():App().mainloop()
if __name__=='__main__':main()

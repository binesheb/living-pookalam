"""Functional Windows 11 operator application for Living Pookalam.

This is the first hardware-testable application layer. It intentionally keeps
all installation state in a local profile so the same application can be reused
at multiple showrooms.
"""
from __future__ import annotations

import json, math, os, random, time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

BG="#07070b"; PANEL="#111118"; BORDER="#2b2b35"; TEXT="#eeeeee"
MUTED="#a9a9b5"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7272"
BASE=os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
STATE_FILE=os.path.join(BASE,"installation_profile.json")

DEFAULT={"camera_index":0,"projector_monitor":1,"projector_width":1920,"projector_height":1080,
         "homography":None,"source":"digital","image":"","pookalam":None}

def load_state():
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f: return {**DEFAULT,**json.load(f)}
    except Exception: return DEFAULT.copy()

def save_state(s):
    with open(STATE_FILE,"w",encoding="utf-8") as f: json.dump(s,f,indent=2)

def order4(points):
    p=np.float32(points); s=p.sum(1); d=np.diff(p,axis=1).reshape(-1)
    return np.array([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]],np.float32)

def detect_four_circles(frame):
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    gray=cv2.GaussianBlur(gray,(9,9),2)
    circles=cv2.HoughCircles(gray,cv2.HOUGH_GRADIENT,1.2,70,param1=100,param2=30,minRadius=10,maxRadius=90)
    if circles is None: return []
    raw=np.round(circles[0]).astype(int); out=[]
    for x,y,r in sorted(raw,key=lambda q:q[2],reverse=True):
        if all((x-a)**2+(y-b)**2>100**2 for a,b,_ in out): out.append((x,y,r))
        if len(out)==4: break
    return out

class ProjectorWindow:
    def __init__(self, app):
        self.app=app
        self.win=tk.Toplevel(app.root); self.win.overrideredirect(True); self.win.configure(bg="black")
        self.canvas=tk.Canvas(self.win,bg="black",highlightthickness=0); self.canvas.pack(fill="both",expand=True)
        self.win.bind("<Escape>",lambda e:self.app.stop_show())
        self.set_monitor()
    def set_monitor(self):
        mons=list(get_monitors()) if get_monitors else []
        idx=int(self.app.state.get("projector_monitor",1))
        if not mons: x=y=0; w=self.app.state["projector_width"]; h=self.app.state["projector_height"]
        else:
            m=mons[min(idx,len(mons)-1)]; x,y,w,h=m.x,m.y,m.width,m.height
        self.w,self.h=w,h; self.win.geometry(f"{w}x{h}+{x}+{y}"); self.win.attributes("-topmost",True)
    def clear(self): self.canvas.delete("all"); self.canvas.configure(bg="black")
    def targets(self):
        self.clear(); m=0.12; pts=[(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))]
        for i,(x,y) in enumerate(pts,1):
            r=min(self.w,self.h)*.028; self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline="gold",width=5); self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",24,"bold"))
    def render(self,source_image=None,center=None,radius=None,interaction=None):
        self.clear(); cx=self.w/2 if center is None else center[0]; cy=self.h/2 if center is None else center[1]; r=radius or min(self.w,self.h)*.30
        if source_image:
            im=Image.fromarray(cv2.cvtColor(source_image,cv2.COLOR_BGR2RGB)); ratio=min(self.w/im.width,self.h/im.height)*.82; im=im.resize((int(im.width*ratio),int(im.height*ratio)))
            self.photo=ImageTk.PhotoImage(im); self.canvas.create_image(cx,cy,image=self.photo)
        else:
            for rr,col,width in [(r,"#d66a2a",45),(r-50,"#f5c542",32),(r-85,"#d33b5b",24),(r-115,"#fff0a8",18)]: self.canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline=col,width=width)
            for i in range(40):
                a=2*math.pi*i/40+time.time()*.05; x=cx+math.cos(a)*(r-25); y=cy+math.sin(a)*(r-25); self.canvas.create_oval(x-7,y-7,x+7,y+7,fill="#ffb83d",outline="")
        if interaction:
            x,y,strength=interaction
            rr=30+strength*r*.7
            self.canvas.create_oval(x-rr,y-rr,x+rr,y+rr,outline="#ffe16a",width=8)
            for i in range(18):
                a=time.time()*.9+i*2*math.pi/18; px=cx+math.cos(a)*rr; py=cy+math.sin(a)*rr; self.canvas.create_oval(px-4,py-4,px+4,py+4,fill="#ffd45a",outline="")

class App:
    def __init__(self,root):
        self.root=root; self.state=load_state(); self.root.title("Living Pookalam — Windows 11"); self.root.geometry("1250x780"); self.root.configure(bg=BG); self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.cap=None; self.frame=None; self.projector=None; self.mode="idle"; self.source=self.state.get("source","digital"); self.image=None; self.photo=None; self.homography=None; self.segmented=False; self.interaction=None; self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False); self.particles=[]
        if self.state.get("homography") is not None: self.homography=np.float32(self.state["homography"])
        self.build(); self.start_camera(); self.tick()
    def build(self):
        header=tk.Frame(self.root,bg=BG); header.pack(fill="x",padx=24,pady=(18,10)); tk.Label(header,text="LIVING POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",27,"bold")).pack(anchor="w"); tk.Label(header,text="ONAM 2026 • WINDOWS 11 • HARDWARE TEST BUILD",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=24,pady=8)
        nav=tk.Frame(body,bg=PANEL,width=270); nav.pack(side="left",fill="y",padx=(0,14)); nav.pack_propagate(False)
        for label,cmd in [("DIGITAL POOKALAM",self.digital),("PHYSICAL POOKALAM",self.physical),("HYBRID",self.hybrid),("PROJECTOR TEST",self.projector_test),("4-POINT CALIBRATE",self.calibrate),("DETECT POOKALAM",self.detect),("INTERACTION TEST",self.interaction_test),("RUN SHOW",self.run_show),("STOP SHOW",self.stop_show)]: self.button(nav,label,cmd,label=="RUN SHOW")
        main=tk.Frame(body,bg=BG); main.pack(side="left",fill="both",expand=True)
        self.status=tk.StringVar(value="STARTING"); self.source_var=tk.StringVar(value="DIGITAL"); self.info=tk.StringVar(value="Camera: starting")
        p=tk.Frame(main,bg=PANEL); p.pack(fill="x"); tk.Label(p,text="SYSTEM STATUS",bg=PANEL,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=(10,2)); tk.Label(p,textvariable=self.status,bg=PANEL,fg=GREEN,font=("Consolas",18,"bold")).pack(anchor="w",padx=14,pady=(0,10))
        cards=tk.Frame(main,bg=BG); cards.pack(fill="x",pady=10); self.cards={}
        for n in ["WEBCAM","PROJECTOR","CALIBRATION","POOKALAM","INTERACTION"]: self.make_card(cards,n)
        pv=tk.Frame(main,bg="#030307"); pv.pack(fill="both",expand=True); tk.Label(pv,text="CAMERA PREVIEW",bg="#030307",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=8,pady=6); self.preview=tk.Label(pv,bg="#030307"); self.preview.pack(expand=True)
        tk.Label(main,textvariable=self.info,bg=BG,fg=MUTED,font=("Consolas",10)).pack(anchor="w",pady=7)
        self.root.bind("<Escape>",lambda e:self.stop_show()); self.root.bind("<c>",lambda e:self.calibrate()); self.root.bind("<r>",lambda e:self.run_show()); self.root.bind("<s>",lambda e:self.stop_show())
    def button(self,p,text,cmd,accent=False): tk.Button(p,text=text,command=cmd,bg="#3b3018" if accent else "#1a1a21",fg=GOLD if accent else TEXT,activebackground="#5a471e",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2).pack(fill="x",padx=14,pady=4)
    def make_card(self,p,n):
        f=tk.Frame(p,bg=PANEL); f.pack(side="left",fill="x",expand=True,padx=2); tk.Label(f,text=n,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(pady=(7,1)); v=tk.Label(f,text="READY",bg=PANEL,fg="#777784",font=("Consolas",9,"bold")); v.pack(pady=(0,7)); self.cards[n]=v
    def card(self,n,t,good=None): self.cards[n].configure(text=t,fg="#777784" if good is None else GREEN if good else RED)
    def start_camera(self):
        self.cap=cv2.VideoCapture(int(self.state.get("camera_index",0)),cv2.CAP_DSHOW); self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720); self.card("WEBCAM","ONLINE" if self.cap.isOpened() else "OFFLINE",self.cap.isOpened())
    def tick(self):
        if self.cap and self.cap.isOpened():
            ok,self.frame=self.cap.read()
            if ok:
                self.card("WEBCAM","ONLINE",True); self.update_preview();
                if self.mode in ("run","interaction"): self.process_interaction()
        if self.mode=="run" and self.projector: self.render()
        self.root.after(30,self.tick)
    def update_preview(self):
        if self.frame is None:return
        im=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB); im=cv2.resize(im,(720,405)); self.photo=ImageTk.PhotoImage(Image.fromarray(im)); self.preview.configure(image=self.photo)
    def projector_open(self):
        if not self.projector: self.projector=ProjectorWindow(self); self.card("PROJECTOR","ONLINE",True)
    def projector_test(self): self.projector_open(); self.projector.targets(); self.status.set("PROJECTOR TEST — FOUR TARGETS"); self.mode="projector_test"
    def calibrate(self):
        self.projector_open(); self.projector.targets(); self.mode="calibrate"; self.status.set("CALIBRATING — CAMERA DETECTS PROJECTED TARGETS"); self.card("CALIBRATION","SEARCHING",None)
    def check_calibration(self):
        if self.frame is None:return
        cs=detect_four_circles(self.frame)
        if len(cs)==4:
            cam=order4([(x,y) for x,y,r in cs]); pw,ph=self.projector.w,self.projector.h; m=.12; proj=np.float32([[pw*m,ph*m],[pw*(1-m),ph*m],[pw*(1-m),ph*(1-m)],[pw*m,ph*(1-m)]])
            H,_=cv2.findHomography(cam,proj,0)
            if H is not None:
                self.homography=H.astype(np.float32); self.state["homography"]=self.homography.tolist(); self.state["projector_width"]=pw; self.state["projector_height"]=ph; save_state(self.state); self.card("CALIBRATION","COMPLETE",True); self.status.set("CALIBRATION COMPLETE"); self.mode="idle"; self.projector.clear()
    def digital(self):
        path=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp"),("All files","*.*")])
        if path:
            self.image=cv2.imread(path); self.source="digital"; self.source_var.set("DIGITAL"); self.state["source"]="digital"; self.state["image"]=path; save_state(self.state); self.card("POOKALAM","DIGITAL",True); self.status.set("DIGITAL POOKALAM LOADED")
    def physical(self): self.source="physical"; self.source_var.set("PHYSICAL"); self.image=None; self.card("POOKALAM","PHYSICAL",True); self.status.set("PHYSICAL POOKALAM MODE")
    def hybrid(self): self.digital(); self.source="hybrid"; self.source_var.set("HYBRID"); self.state["source"]="hybrid"; save_state(self.state)
    def detect(self):
        if self.frame is None:return
        hsv=cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV); mask=((hsv[:,:,1]>55)&(hsv[:,:,2]>45)).astype(np.uint8)*255; mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((11,11),np.uint8)); contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        h,w=mask.shape; candidates=[c for c in contours if .02*w*h<cv2.contourArea(c)<.9*w*h]
        if not candidates:self.card("POOKALAM","NOT FOUND",False); self.status.set("NO CLEAR POOKALAM DETECTED"); return
        c=max(candidates,key=cv2.contourArea); M=cv2.moments(c); cx=M["m10"]/M["m00"]; cy=M["m01"]/M["m00"]; (x,y),r=cv2.minEnclosingCircle(c); self.state["pookalam"]={"camera_center":[cx,cy],"camera_radius":r,"area":float(cv2.contourArea(c))}; save_state(self.state); self.card("POOKALAM","DETECTED",True); self.status.set("POOKALAM DETECTED — REVIEW CAMERA VIEW")
    def interaction_test(self): self.mode="interaction"; self.card("INTERACTION","TESTING",None); self.status.set("INTERACTION TEST — MOVE IN CAMERA VIEW")
    def process_interaction(self):
        if self.frame is None:return
        small=cv2.resize(self.frame,(640,360)); mask=self.bg.apply(small,learningRate=.002); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8)); contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); c=max(contours,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction=None; return
        M=cv2.moments(c); x=M["m10"]/M["m00"]; y=M["m01"]/M["m00"]
        if self.homography is not None:
            q=cv2.perspectiveTransform(np.float32([[[x,y]]]),self.homography)[0,0]; x,y=float(q[0]),float(q[1])
        d=math.hypot(x-self.projector.w/2,y-self.projector.h/2); strength=max(0,min(1,1-d/(min(self.projector.w,self.projector.h)*.38))) if self.projector else 0; self.interaction=(x,y,strength)
    def render(self):
        if not self.projector:return
        cx=self.projector.w/2; cy=self.projector.h/2; r=min(self.projector.w,self.projector.h)*.30; self.projector.render(self.image if self.source=="digital" else None,(cx,cy),r,self.interaction)
    def run_show(self):
        if self.homography is None: messagebox.showwarning("Calibration required","Calibrate the projector/webcam before running the interactive show."); return
        self.projector_open(); self.mode="run"; self.card("CALIBRATION","LOCKED",True); self.card("INTERACTION","ACTIVE",True); self.status.set("SHOW RUNNING")
    def stop_show(self):
        self.mode="idle"; self.interaction=None; self.card("INTERACTION","READY",None); self.status.set("STOPPED");
        if self.projector:self.projector.clear()
    def close(self):
        self.stop_show();
        if self.cap:self.cap.release()
        self.root.destroy()

def launch():
    root=tk.Tk(); App(root); root.mainloop()

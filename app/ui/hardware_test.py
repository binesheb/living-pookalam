"""Full Windows 11 Living Pookalam operator application.

Hardware calibration is optional at startup. The app can be used in preview mode
before calibration, then projector/camera mapping can be locked later.
"""
from __future__ import annotations
import json, math, os, time
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from app.visuals.engine import Interaction, VisualEngine
try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

BG="#07070b"; PANEL="#111118"; BORDER="#2b2b35"; TEXT="#eeeeee"; MUTED="#a9a9b5"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7272"
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../..")); PROFILE=os.path.join(ROOT,"installation_profile.json")
DEFAULT={"camera_index":0,"projector_monitor":1,"homography":None,"projector_width":1920,"projector_height":1080,"source":"generated","image":"","pookalam":None,"effects":{}}

def load_state():
    try:
        with open(PROFILE,"r",encoding="utf-8") as f:return {**DEFAULT,**json.load(f)}
    except Exception:return DEFAULT.copy()

def save_state(s):
    with open(PROFILE,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)

def order4(points):
    p=np.float32(points);s=p.sum(1);d=np.diff(p,axis=1).reshape(-1)
    return np.array([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]],np.float32)

def detect_four_circles(frame):
    gray=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(9,9),2)
    circles=cv2.HoughCircles(gray,cv2.HOUGH_GRADIENT,1.2,70,param1=100,param2=30,minRadius=10,maxRadius=100)
    if circles is None:return []
    out=[]
    for x,y,r in np.round(circles[0]).astype(int):
        if all((x-a)**2+(y-b)**2>100**2 for a,b,_ in out):out.append((x,y,r))
        if len(out)==4:break
    return out

class DrawAdapter:
    def __init__(self,canvas):self.canvas=canvas
    def circle(self,x,y,r,fill,width=0):self.canvas.create_oval(x-r,y-r,x+r,y+r,fill=fill if width==0 else "",outline=fill,width=max(1,width))
    def ellipse(self,rect,fill,width=0):self.canvas.create_oval(*rect,fill=fill if width==0 else "",outline=fill,width=max(1,width))
    def line(self,points,fill,width=1):self.canvas.create_line(*[v for pt in points for v in pt],fill=fill,width=width,smooth=True)
    def polygon(self,points,fill):self.canvas.create_polygon(*[v for pt in points for v in pt],fill=fill)

class ProjectionWindow:
    def __init__(self,app):
        self.app=app;self.win=tk.Toplevel(app.root);self.win.overrideredirect(True);self.win.configure(bg="black");self.canvas=tk.Canvas(self.win,bg="black",highlightthickness=0);self.canvas.pack(fill="both",expand=True);self.win.bind("<Escape>",lambda e:app.stop_show());self.place()
    def place(self):
        mons=list(get_monitors()) if get_monitors else [];idx=int(self.app.state.get("projector_monitor",1));idx=min(idx,max(0,len(mons)-1))
        if mons:
            m=mons[idx];self.w,self.h=m.width,m.height;self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:self.w,self.h=self.app.state["projector_width"],self.app.state["projector_height"];self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost",True)
    def clear(self):self.canvas.delete("all");self.canvas.configure(bg="black")
    def targets(self):
        self.clear();m=.12;pts=[(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))];r=min(self.w,self.h)*.028
        for i,(x,y) in enumerate(pts,1):self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline=GOLD,width=5);self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",24,"bold"))
    def render(self,engine,interaction):
        self.clear();engine.render(DrawAdapter(self.canvas),self.w,self.h,interaction=interaction)

class App:
    def __init__(self,root):
        self.root=root;self.state=load_state();self.root.title("Living Pookalam — Windows 11");self.root.geometry("1280x820");self.root.configure(bg=BG);self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.cap=cv2.VideoCapture(int(self.state.get("camera_index",0)),cv2.CAP_DSHOW);self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280);self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
        self.frame=None;self.proj=None;self.mode="idle";self.H=np.float32(self.state["homography"]) if self.state.get("homography") else None;self.image=None;self.interaction=Interaction();self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False);self.engine=VisualEngine();self.last=time.perf_counter();self.build()
        for name,val in self.state.get("effects",{}).items():self.engine.set_effect(name,val)
        self.start_camera();self.tick()
    def build(self):
        head=tk.Frame(self.root,bg=BG);head.pack(fill="x",padx=24,pady=(16,8));tk.Label(head,text="LIVING POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",28,"bold")).pack(anchor="w");tk.Label(head,text="ONAM 2026  •  WINDOWS 11  •  FULL EXPERIENCE TEST",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w")
        body=tk.Frame(self.root,bg=BG);body.pack(fill="both",expand=True,padx=24,pady=8);nav=tk.Frame(body,bg=PANEL,width=280);nav.pack(side="left",fill="y",padx=(0,14));nav.pack_propagate(False)
        for text,cmd,accent in [("PROJECTOR TEST",self.projector_test,False),("CALIBRATE (LATER)",self.calibrate,False),("DIGITAL POOKALAM",self.digital,False),("PHYSICAL POOKALAM",self.physical,False),("HYBRID",self.hybrid,False),("DETECT / MAP",self.detect,False),("INTERACTION TEST",self.interaction_test,False),("RUN SHOW",self.run_show,True),("STOP SHOW",self.stop_show,False)]:self.button(nav,text,cmd,accent)
        tk.Frame(nav,bg=BORDER,height=1).pack(fill="x",padx=14,pady=10);tk.Label(nav,text="EFFECT LAYERS",bg=PANEL,fg=GOLD,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(0,5));self.effect_vars={}
        for name in self.engine.EFFECTS:
            v=tk.BooleanVar(value=self.engine.effects[name]);self.effect_vars[name]=v;tk.Checkbutton(nav,text=name.replace("_"," ").title(),variable=v,command=lambda n=name:self.toggle_effect(n),bg=PANEL,fg=TEXT,selectcolor="#1b1b22",activebackground=PANEL,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=16)
        tk.Button(nav,text="RESET EFFECTS",command=self.reset_effects,bg="#1a1a21",fg=TEXT,relief="flat").pack(fill="x",padx=14,pady=9)
        main=tk.Frame(body,bg=BG);main.pack(side="left",fill="both",expand=True);self.status=tk.StringVar(value="READY — CALIBRATION OPTIONAL");self.info=tk.StringVar(value="Camera: starting")
        s=tk.Frame(main,bg=PANEL);s.pack(fill="x");tk.Label(s,text="SYSTEM STATUS",bg=PANEL,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=(9,1));tk.Label(s,textvariable=self.status,bg=PANEL,fg=GREEN,font=("Consolas",17,"bold")).pack(anchor="w",padx=14,pady=(0,9))
        cards=tk.Frame(main,bg=BG);cards.pack(fill="x",pady=8);self.cards={}
        for n in ["WEBCAM","PROJECTOR","CALIBRATION","POOKALAM","INTERACTION"]:self.make_card(cards,n)
        pv=tk.Frame(main,bg="#030307");pv.pack(fill="both",expand=True);tk.Label(pv,text="CAMERA / FLOOR VIEW",bg="#030307",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=8,pady=5);self.preview=tk.Label(pv,bg="#030307");self.preview.pack(expand=True);tk.Label(main,textvariable=self.info,bg=BG,fg=MUTED,font=("Consolas",10)).pack(anchor="w",pady=6)
        self.root.bind("<Escape>",lambda e:self.stop_show());self.root.bind("<c>",lambda e:self.calibrate());self.root.bind("<r>",lambda e:self.run_show());self.root.bind("<s>",lambda e:self.stop_show())
    def button(self,p,text,cmd,accent=False):tk.Button(p,text=text,command=cmd,bg="#3b3018" if accent else "#1a1a21",fg=GOLD if accent else TEXT,activebackground="#5a471e",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2).pack(fill="x",padx=14,pady=4)
    def make_card(self,p,n):
        f=tk.Frame(p,bg=PANEL);f.pack(side="left",fill="x",expand=True,padx=2);tk.Label(f,text=n,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(pady=(6,1));v=tk.Label(f,text="READY",bg=PANEL,fg="#777784",font=("Consolas",9,"bold"));v.pack(pady=(0,6));self.cards[n]=v
    def card(self,n,text,good=None):self.cards[n].configure(text=text,fg="#777784" if good is None else GREEN if good else RED)
    def start_camera(self):self.card("WEBCAM","ONLINE" if self.cap.isOpened() else "OFFLINE",self.cap.isOpened())
    def tick(self):
        now=time.perf_counter();dt=min(.1,now-self.last);self.last=now
        if self.cap.isOpened():
            ok,self.frame=self.cap.read()
            if ok:self.card("WEBCAM","ONLINE",True);self.update_preview()
        if self.mode=="calibrate" and self.frame is not None:self.calibration_step()
        if self.mode in ("interaction","run") and self.frame is not None:self.track_interaction()
        self.engine.update(dt,self.interaction)
        if self.mode=="run" and self.proj:self.proj.render(self.engine,self.interaction)
        self.root.after(25,self.tick)
    def update_preview(self):
        im=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB);im=cv2.resize(im,(760,428));self.photo=ImageTk.PhotoImage(Image.fromarray(im));self.preview.configure(image=self.photo)
    def open_projector(self):
        if not self.proj:self.proj=ProjectionWindow(self);self.card("PROJECTOR","ONLINE",True)
    def projector_test(self):self.open_projector();self.proj.targets();self.mode="projector";self.status.set("PROJECTOR TEST — VERIFY SCREEN POSITION")
    def calibrate(self):self.open_projector();self.proj.targets();self.mode="calibrate";self.card("CALIBRATION","SEARCHING");self.status.set("CALIBRATION — AIM CAMERA AT PROJECTOR TARGETS")
    def calibration_step(self):
        cs=detect_four_circles(self.frame);self.info.set(f"Calibration targets: {len(cs)}/4")
        if len(cs)!=4:return
        cam=order4([(x,y) for x,y,r in cs]);m=.12;pw,ph=self.proj.w,self.proj.h;dst=np.float32([[pw*m,ph*m],[pw*(1-m),ph*m],[pw*(1-m),ph*(1-m)],[pw*m,ph*(1-m)]])
        H,_=cv2.findHomography(cam,dst,0)
        if H is not None:self.H=H.astype(np.float32);self.state.update({"homography":self.H.tolist(),"projector_width":pw,"projector_height":ph});save_state(self.state);self.card("CALIBRATION","COMPLETE",True);self.status.set("CALIBRATION COMPLETE — READY");self.mode="idle";self.proj.clear()
    def digital(self):
        p=filedialog.askopenfilename(title="Choose Pookalam image",filetypes=[("Images","*.png *.jpg *.jpeg *.webp"),("All files","*.*")])
        if p:self.image=cv2.imread(p);self.state.update({"source":"digital","image":p});save_state(self.state);self.card("POOKALAM","DIGITAL",True);self.status.set("DIGITAL POOKALAM LOADED")
    def physical(self):self.image=None;self.state["source"]="physical";save_state(self.state);self.card("POOKALAM","PHYSICAL",True);self.status.set("PHYSICAL POOKALAM — SEGMENTATION READY")
    def hybrid(self):self.digital();self.state["source"]="hybrid";save_state(self.state);self.status.set("HYBRID — PHYSICAL + DIGITAL EFFECTS")
    def detect(self):
        if self.frame is None:return
        hsv=cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV);mask=((hsv[:,:,1]>50)&(hsv[:,:,2]>45)).astype(np.uint8)*255;mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((9,9),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);h,w=mask.shape;cs=[c for c in cs if .015*w*h<cv2.contourArea(c)<.92*w*h]
        if not cs:self.card("POOKALAM","NOT FOUND",False);self.status.set("NO CLEAR POOKALAM — TRY BETTER LIGHTING");return
        c=max(cs,key=cv2.contourArea);M=cv2.moments(c);cx=M["m10"]/M["m00"];cy=M["m01"]/M["m00"];area=float(cv2.contourArea(c));self.state["pookalam"]={"camera_center":[cx,cy],"area":area,"bbox":list(map(int,cv2.boundingRect(c)))};save_state(self.state);self.card("POOKALAM","DETECTED",True);self.status.set("POOKALAM DETECTED — MASK LOCKED")
    def interaction_test(self):self.mode="interaction";self.interaction=Interaction();self.card("INTERACTION","TESTING");self.status.set("INTERACTION TEST — MOVE IN CAMERA VIEW")
    def track_interaction(self):
        small=cv2.resize(self.frame,(640,360));mask=self.bg.apply(small,learningRate=.002);mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(cs,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction=Interaction();self.card("INTERACTION","WAITING");return
        M=cv2.moments(c);x=M["m10"]/M["m00"]/640;y=M["m01"]/M["m00"]/360
        if self.H is not None and self.proj:
            q=cv2.perspectiveTransform(np.float32([[[x*640,y*360]]]),self.H)[0,0];x=float(q[0]/self.proj.w);y=float(q[1]/self.proj.h)
        strength=max(0,min(1,1-math.hypot(x-.5,y-.5)/.65));self.interaction=Interaction(max(0,min(1,x)),max(0,min(1,y)),strength,True);self.card("INTERACTION","ACTIVE",True)
    def run_show(self):self.open_projector();self.mode="run";self.card("CALIBRATION","LOCKED" if self.H is not None else "PREVIEW",self.H is not None);self.card("INTERACTION","ACTIVE",True);self.status.set("SHOW RUNNING — LIVE EXPERIENCE ENGINE")
    def stop_show(self):self.mode="idle";self.interaction=Interaction();self.card("INTERACTION","READY");self.status.set("STOPPED");self.proj.clear() if self.proj else None
    def toggle_effect(self,name):self.engine.set_effect(name,self.effect_vars[name].get());self.state.setdefault("effects",{})[name]=self.effect_vars[name].get();save_state(self.state)
    def reset_effects(self):
        self.engine.set_all(True)
        for n,v in self.effect_vars.items():v.set(True)
        self.state["effects"]={};save_state(self.state)
    def close(self):self.stop_show();self.cap.release();self.root.destroy()

def launch():
    root=tk.Tk();App(root);root.mainloop()

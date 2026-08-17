"""End-to-end Windows 11 hardware test application.

Purpose: first real test with webcam + projector. It provides:
- live camera preview
- projector target test
- automatic four-point camera->projector homography calibration
- digital image projection
- physical Pookalam colour segmentation
- simple person motion interaction
- persistent installation profile
"""
from __future__ import annotations
import json, math, os, time
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

BG="#07070b"; PANEL="#111118"; BORDER="#2b2b35"; TEXT="#eeeeee"; MUTED="#a9a9b5"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7272"
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../..")); PROFILE=os.path.join(ROOT,"installation_profile.json")
DEFAULT={"camera_index":0,"projector_monitor":1,"homography":None,"projector_width":1920,"projector_height":1080,"source":"physical","image":"","pookalam":None}

def load():
    try:
        with open(PROFILE,"r",encoding="utf-8") as f:return {**DEFAULT,**json.load(f)}
    except Exception:return DEFAULT.copy()
def save(s):
    with open(PROFILE,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)
def order4(p):
    p=np.float32(p); s=p.sum(1); d=np.diff(p,axis=1).reshape(-1); return np.array([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]],np.float32)
def circles(frame):
    g=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); g=cv2.GaussianBlur(g,(9,9),2)
    c=cv2.HoughCircles(g,cv2.HOUGH_GRADIENT,1.2,70,param1=100,param2=30,minRadius=10,maxRadius=90)
    if c is None:return []
    out=[]
    for x,y,r in np.round(c[0]).astype(int):
        if all((x-a)**2+(y-b)**2>100**2 for a,b,_ in out):out.append((x,y,r))
        if len(out)==4:break
    return out

class Projection:
    def __init__(self,app):
        self.app=app; self.win=tk.Toplevel(app.root); self.win.overrideredirect(True); self.win.configure(bg="black"); self.canvas=tk.Canvas(self.win,bg="black",highlightthickness=0); self.canvas.pack(fill="both",expand=True); self.win.bind("<Escape>",lambda e:app.stop()); self.place()
    def place(self):
        ms=list(get_monitors()) if get_monitors else []
        i=min(int(self.app.state.get("projector_monitor",1)),max(0,len(ms)-1))
        if ms:m=ms[i]; self.w,self.h=m.width,m.height; self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:self.w,self.h=self.app.state["projector_width"],self.app.state["projector_height"]; self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost",True)
    def clear(self):self.canvas.delete("all");self.canvas.configure(bg="black")
    def targets(self):
        self.clear();m=.12;pts=[(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))];r=min(self.w,self.h)*.028
        for i,(x,y) in enumerate(pts,1):self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline="#ffd45a",width=5);self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",24,"bold"))
    def show(self,image=None,interaction=None):
        self.clear();cx,cy=self.w/2,self.h/2;r=min(self.w,self.h)*.30
        if image is not None:
            im=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));q=min(self.w/im.width,self.h/im.height)*.82;im=im.resize((int(im.width*q),int(im.height*q)));self.photo=ImageTk.PhotoImage(im);self.canvas.create_image(cx,cy,image=self.photo)
        else:
            for rr,col,ww in [(r,"#d66a2a",45),(r-50,"#f5c542",32),(r-85,"#d33b5b",24),(r-115,"#fff0a8",18)]:self.canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline=col,width=ww)
        if interaction:
            x,y,s=interaction;rr=30+s*r*.7;self.canvas.create_oval(x-rr,y-rr,x+rr,y+rr,outline="#ffe16a",width=8)
            for i in range(18):
                a=time.time()*.9+i*2*math.pi/18;px=cx+math.cos(a)*rr;py=cy+math.sin(a)*rr;self.canvas.create_oval(px-4,py-4,px+4,py+4,fill="#ffd45a",outline="")

class App:
    def __init__(self,root):
        self.root=root;self.state=load();self.root.title("Living Pookalam — Hardware Test");self.root.geometry("1240x780");self.root.configure(bg=BG);self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.cap=cv2.VideoCapture(int(self.state["camera_index"]),cv2.CAP_DSHOW);self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280);self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720);self.frame=None;self.proj=None;self.mode="idle";self.H=np.float32(self.state["homography"]) if self.state.get("homography") else None;self.image=None;self.interaction=None;self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False)
        self.build();self.tick()
    def build(self):
        h=tk.Frame(self.root,bg=BG);h.pack(fill="x",padx=24,pady=(18,10));tk.Label(h,text="LIVING POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",27,"bold")).pack(anchor="w");tk.Label(h,text="ONAM 2026 • WINDOWS 11 • HARDWARE TEST",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w")
        b=tk.Frame(self.root,bg=BG);b.pack(fill="both",expand=True,padx=24,pady=8);n=tk.Frame(b,bg=PANEL,width=275);n.pack(side="left",fill="y",padx=(0,14));n.pack_propagate(False)
        for t,c in [("PROJECTOR TEST",self.projector_test),("4-POINT CALIBRATE",self.calibrate),("DIGITAL POOKALAM",self.digital),("PHYSICAL POOKALAM",self.physical),("DETECT POOKALAM",self.detect),("INTERACTION TEST",self.interaction_test),("RUN SHOW",self.run),("STOP",self.stop)]:self.btn(n,t,c,t=="RUN SHOW")
        m=tk.Frame(b,bg=BG);m.pack(side="left",fill="both",expand=True);self.status=tk.StringVar(value="STARTING");self.info=tk.StringVar(value="");p=tk.Frame(m,bg=PANEL);p.pack(fill="x");tk.Label(p,text="STATUS",bg=PANEL,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=(10,2));tk.Label(p,textvariable=self.status,bg=PANEL,fg=GREEN,font=("Consolas",18,"bold")).pack(anchor="w",padx=14,pady=(0,10));cards=tk.Frame(m,bg=BG);cards.pack(fill="x",pady=10);self.cards={}
        for x in ["WEBCAM","PROJECTOR","CALIBRATION","POOKALAM","INTERACTION"]:self.mkcard(cards,x)
        pv=tk.Frame(m,bg="#030307");pv.pack(fill="both",expand=True);tk.Label(pv,text="CAMERA VIEW",bg="#030307",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=8,pady=6);self.preview=tk.Label(pv,bg="#030307");self.preview.pack(expand=True);tk.Label(m,textvariable=self.info,bg=BG,fg=MUTED,font=("Consolas",10)).pack(anchor="w",pady=6)
        self.root.bind("<Escape>",lambda e:self.stop());self.root.bind("<c>",lambda e:self.calibrate());self.root.bind("<r>",lambda e:self.run());self.root.bind("<s>",lambda e:self.stop())
    def btn(self,p,t,c,a=False):tk.Button(p,text=t,command=c,bg="#3b3018" if a else "#1a1a21",fg=GOLD if a else TEXT,activebackground="#5a471e",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2).pack(fill="x",padx=14,pady=4)
    def mkcard(self,p,n):
        f=tk.Frame(p,bg=PANEL);f.pack(side="left",fill="x",expand=True,padx=2);tk.Label(f,text=n,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(pady=(7,1));v=tk.Label(f,text="READY",bg=PANEL,fg="#777784",font=("Consolas",9,"bold"));v.pack(pady=(0,7));self.cards[n]=v
    def card(self,n,t,g=None):self.cards[n].configure(text=t,fg="#777784" if g is None else GREEN if g else RED)
    def tick(self):
        ok,self.frame=self.cap.read() if self.cap.isOpened() else (False,None)
        if ok:self.card("WEBCAM","ONLINE",True);self.preview_frame()
        else:self.card("WEBCAM","OFFLINE",False)
        if self.mode=="calibrate" and ok:self.calibration_step()
        if self.mode in ("interaction","run") and ok:self.track()
        if self.mode=="run" and self.proj:self.proj.show(self.image if self.image is not None else None,self.interaction)
        self.root.after(30,self.tick)
    def preview_frame(self):
        im=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB);im=cv2.resize(im,(720,405));self.photo=ImageTk.PhotoImage(Image.fromarray(im));self.preview.configure(image=self.photo)
    def open_proj(self):
        if not self.proj:self.proj=Projection(self);self.card("PROJECTOR","ONLINE",True)
    def projector_test(self):self.open_proj();self.proj.targets();self.mode="projector";self.status.set("PROJECTOR TEST — CHECK THE FOUR TARGETS")
    def calibrate(self):self.open_proj();self.proj.targets();self.mode="calibrate";self.status.set("CALIBRATING — LOOKING FOR 4 PROJECTED TARGETS");self.card("CALIBRATION","SEARCHING")
    def calibration_step(self):
        cs=circles(self.frame)
        self.info.set(f"Calibration targets detected: {len(cs)}/4")
        if len(cs)!=4:return
        cam=order4([(x,y) for x,y,r in cs]);m=.12;pw,ph=self.proj.w,self.proj.h;dst=np.float32([[pw*m,ph*m],[pw*(1-m),ph*m],[pw*(1-m),ph*(1-m)],[pw*m,ph*(1-m)]])
        H,_=cv2.findHomography(cam,dst,0)
        if H is None:return
        self.H=H.astype(np.float32);self.state["homography"]=self.H.tolist();self.state["projector_width"]=pw;self.state["projector_height"]=ph;save(self.state);self.card("CALIBRATION","COMPLETE",True);self.status.set("CALIBRATION COMPLETE");self.mode="idle";self.proj.clear()
    def digital(self):
        p=filedialog.askopenfilename(title="Choose Pookalam",filetypes=[("Images","*.png *.jpg *.jpeg *.webp"),("All files","*.*")])
        if p:self.image=cv2.imread(p);self.state["source"]="digital";self.state["image"]=p;save(self.state);self.card("POOKALAM","DIGITAL",True);self.status.set("DIGITAL POOKALAM LOADED")
    def physical(self):self.image=None;self.state["source"]="physical";save(self.state);self.card("POOKALAM","PHYSICAL",True);self.status.set("PHYSICAL POOKALAM MODE")
    def detect(self):
        if self.frame is None:return
        hsv=cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV);mask=((hsv[:,:,1]>55)&(hsv[:,:,2]>45)).astype(np.uint8)*255;mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((11,11),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);h,w=mask.shape;cs=[c for c in cs if .02*w*h<cv2.contourArea(c)<.9*w*h]
        if not cs:self.card("POOKALAM","NOT FOUND",False);self.status.set("NO CLEAR POOKALAM DETECTED");return
        c=max(cs,key=cv2.contourArea);M=cv2.moments(c);cx=M["m10"]/M["m00"];cy=M["m01"]/M["m00"];self.state["pookalam"]={"camera_center":[cx,cy],"area":float(cv2.contourArea(c))};save(self.state);self.card("POOKALAM","DETECTED",True);self.status.set("POOKALAM DETECTED")
    def interaction_test(self):self.mode="interaction";self.card("INTERACTION","TESTING",None);self.status.set("INTERACTION TEST — MOVE IN FRONT OF CAMERA")
    def track(self):
        small=cv2.resize(self.frame,(640,360));mask=self.bg.apply(small,learningRate=.002);mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(cs,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction=None;return
        M=cv2.moments(c);x=M["m10"]/M["m00"];y=M["m01"]/M["m00"]
        if self.H is not None:q=cv2.perspectiveTransform(np.float32([[[x,y]]]),self.H)[0,0];x,y=float(q[0]),float(q[1])
        if self.proj:d=math.hypot(x-self.proj.w/2,y-self.proj.h/2);s=max(0,min(1,1-d/(min(self.proj.w,self.proj.h)*.38)));self.interaction=(x,y,s);self.card("INTERACTION","ACTIVE",True)
    def run(self):
        if self.H is None:messagebox.showwarning("Calibration required","Run 4-POINT CALIBRATE first.");return
        self.open_proj();self.mode="run";self.card("CALIBRATION","LOCKED",True);self.status.set("SHOW RUNNING")
    def stop(self):self.mode="idle";self.interaction=None;self.card("INTERACTION","READY");self.status.set("STOPPED");self.proj.clear() if self.proj else None
    def close(self):self.stop();self.cap.release();self.root.destroy()

def launch():
    root=tk.Tk();App(root);root.mainloop()

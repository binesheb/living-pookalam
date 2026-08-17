"""Living Pookalam full Windows 11 operator application.

Designed for first projector/webcam testing before physical calibration.
Calibration can be performed later and persisted per showroom profile.
"""
from __future__ import annotations
import json, math, os, random, time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageEnhance
try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

BG="#07070b"; PANEL="#111118"; TEXT="#eeeeee"; MUTED="#9c9ca8"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7272"
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../..")); PROFILE=os.path.join(ROOT,"installation_profile.json")
DEFAULT={"camera_index":0,"projector_monitor":1,"projector_width":1920,"projector_height":1080,"homography":None,"source":"generated","image":"","effects":{}}

def load_state():
    try:
        with open(PROFILE,"r",encoding="utf-8") as f:return {**DEFAULT,**json.load(f)}
    except Exception:return DEFAULT.copy()
def save_state(s):
    with open(PROFILE,"w",encoding="utf-8") as f:json.dump(s,f,indent=2)
def order4(points):
    p=np.float32(points);s=p.sum(1);d=np.diff(p,axis=1).reshape(-1)
    return np.array([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]],np.float32)
def find_circles(frame):
    g=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(9,9),2)
    c=cv2.HoughCircles(g,cv2.HOUGH_GRADIENT,1.2,70,param1=100,param2=30,minRadius=10,maxRadius=110)
    if c is None:return []
    out=[]
    for x,y,r in np.round(c[0]).astype(int):
        if all((x-a)**2+(y-b)**2>100**2 for a,b,_ in out):out.append((x,y,r))
        if len(out)==4:break
    return out

class Projector:
    def __init__(self,app):
        self.app=app;self.win=tk.Toplevel(app.root);self.win.overrideredirect(True);self.win.configure(bg="black");self.canvas=tk.Canvas(self.win,bg="black",highlightthickness=0);self.canvas.pack(fill="both",expand=True);self.win.bind("<Escape>",lambda e:app.stop());self.place();self.photo=None
    def place(self):
        ms=list(get_monitors()) if get_monitors else [];idx=int(self.app.state.get("projector_monitor",1));idx=min(idx,max(0,len(ms)-1))
        if ms:
            m=ms[idx];self.w,self.h=m.width,m.height;self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:self.w,self.h=self.app.state["projector_width"],self.app.state["projector_height"];self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost",True)
    def clear(self):self.canvas.delete("all");self.canvas.configure(bg="black")
    def targets(self):
        self.clear();m=.10;pts=[(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))];r=min(self.w,self.h)*.025
        for i,(x,y) in enumerate(pts,1):
            self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline=GOLD,width=5);self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",22,"bold"))
        self.canvas.create_text(self.w/2,self.h/2,text="LIVING POOKALAM • PROJECTOR CALIBRATION",fill=GOLD,font=("Segoe UI",28,"bold"))
    def image_layer(self,img):
        if img is None:return
        im=Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB));scale=min(self.w/im.width,self.h/im.height)*.82;im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS);self.photo=ImageTk.PhotoImage(im);self.canvas.create_image(self.w/2,self.h/2,image=self.photo)
    def render(self,app):
        self.clear();cx,cy=self.w/2,self.h/2;R=min(self.w,self.h)*.37;t=app.t
        if app.image is not None:self.image_layer(app.image)
        else:
            cols=["#d86b2c","#f3c442","#cf3f65","#fff0a8","#e58a32"]
            for i in range(7):self.canvas.create_oval(cx-R*(1-i*.10),cy-R*(1-i*.10),cx+R*(1-i*.10),cy+R*(1-i*.10),outline=cols[i%len(cols)],width=max(8,int(R*.035)))
            for i in range(40):
                a=2*math.pi*i/40+t*.06;r=R*.86;x=cx+math.cos(a)*r;y=cy+math.sin(a)*r;self.petal(x,y,a,R*.07,cols[i%len(cols)])
        # animation overlays
        if app.effects["glow"]:
            q=.5+.5*math.sin(t*1.6)
            for i in range(4):
                rr=R*(.72+i*.05+q*.012);self.canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline="#ffd45a",width=max(2,7-i),dash=(3,12))
        if app.effects["waves"]:
            for i in range(4):
                p=(t*.14+i*.25)%1;rr=R*(.12+p*.82);self.canvas.create_oval(cx-rr,cy-rr,cx+rr,cy+rr,outline="#ffe36d",width=max(1,int(5*(1-p))))
        if app.effects["lotus"]:self.lotus(cx,cy,R*.20,t)
        if app.effects["spiral"]:
            pts=[]
            for i in range(180):
                a=i*.13+t*.15;rr=R*.05+R*.78*i/179;pts.extend((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
            self.canvas.create_line(*pts,fill="#ffd45a",width=max(2,int(R*.006)),smooth=True)
        if app.effects["fireflies"]:
            for i in range(48):
                a=2*math.pi*i/48+t*(.025+(i%4)*.003);rr=R*(.35+.28*(math.sin(i*3.1)**2));x=cx+math.cos(a)*rr;y=cy+math.sin(a)*rr;q=.4+.6*(.5+.5*math.sin(t*3+i));self.canvas.create_oval(x-3*q,y-3*q,x+3*q,y+3*q,fill="#fff0a0",outline="")
        if app.effects["petals"]:
            for p in app.particles:
                if p[4]>0:self.petal(p[0]*self.w,p[1]*self.h,p[6],p[5],p[7])
        if app.interaction_active:
            x,y=app.interaction
            for i in range(6):
                p=(t*1.4+i*.18)%1;rr=R*(.03+p*.55);self.canvas.create_oval(x*self.w-rr,y*self.h-rr,x*self.w+rr,y*self.h+rr,outline="#fff07a",width=max(2,int(7*(1-p))))
            for i in range(28):
                a=2*math.pi*i/28+t*1.8;rr=R*(.08+.22*app.interaction_strength);px=x*self.w+math.cos(a)*rr;py=y*self.h+math.sin(a)*rr;self.canvas.create_oval(px-3,py-3,px+3,py+3,fill="#ffd45a",outline="")
    def petal(self,x,y,a,r,col):
        ux,uy=math.cos(a),math.sin(a);vx,vy=-uy,ux;pts=[(x+ux*r*1.8,y+uy*r*1.8),(x+vx*r*.7,y+vy*r*.7),(x-ux*r*.8,y-uy*r*.8),(x-vx*r*.7,y-vy*r*.7)];self.canvas.create_polygon(pts,fill=col,outline="")
    def lotus(self,cx,cy,r,t):
        for i in range(12):
            a=2*math.pi*i/12+t*.10;px=cx+math.cos(a)*r*.45;py=cy+math.sin(a)*r*.45;self.petal(px,py,a,r*.45,"#ff9bb0")
        self.canvas.create_oval(cx-r*.14,cy-r*.14,cx+r*.14,cy+r*.14,fill="#ffe58a",outline="")

class App:
    def __init__(self,root):
        self.root=root;self.state=load_state();self.root.title("Living Pookalam — Windows 11");self.root.geometry("1280x820");self.root.configure(bg=BG);self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.cap=cv2.VideoCapture(int(self.state.get("camera_index",0)),cv2.CAP_DSHOW);self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280);self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720);self.frame=None;self.projector=None;self.mode="idle";self.H=np.float32(self.state["homography"]) if self.state.get("homography") else None;self.image=None;self.t=0;self.last=time.perf_counter();self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False);self.interaction_active=False;self.interaction=(.5,.5);self.interaction_strength=0;self.particles=[]
        self.effects={"glow":True,"waves":True,"lotus":True,"spiral":True,"fireflies":True,"petals":True};self.build();self.start_camera();self.tick()
    def build(self):
        tk.Label(self.root,text="LIVING POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",28,"bold")).pack(anchor="w",padx=24,pady=(16,0));tk.Label(self.root,text="ONAM 2026 • FULL EXPERIENCE TEST • WINDOWS 11",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",padx=24)
        body=tk.Frame(self.root,bg=BG);body.pack(fill="both",expand=True,padx=24,pady=12);nav=tk.Frame(body,bg=PANEL,width=285);nav.pack(side="left",fill="y",padx=(0,14));nav.pack_propagate(False)
        for text,cmd,accent in [("PROJECTOR TEST",self.projector_test,False),("DIGITAL POOKALAM",self.digital,False),("PHYSICAL POOKALAM",self.physical,False),("HYBRID",self.hybrid,False),("DETECT / MAP",self.detect,False),("CALIBRATE LATER",self.calibrate,False),("INTERACTION TEST",self.interaction_test,False),("RUN SHOW",self.run,True),("STOP SHOW",self.stop,False)]:self.button(nav,text,cmd,accent)
        tk.Frame(nav,bg="#2b2b35",height=1).pack(fill="x",padx=14,pady=10);tk.Label(nav,text="LIVE EFFECTS",bg=PANEL,fg=GOLD,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=4)
        self.vars={}
        for n in self.effects:
            v=tk.BooleanVar(value=True);self.vars[n]=v;tk.Checkbutton(nav,text=n.title(),variable=v,command=lambda k=n:self.set_effect(k),bg=PANEL,fg=TEXT,selectcolor="#1c1c24",activebackground=PANEL,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=18)
        tk.Button(nav,text="RESET EFFECTS",command=self.reset_effects,bg="#1a1a21",fg=TEXT,relief="flat").pack(fill="x",padx=14,pady=10)
        main=tk.Frame(body,bg=BG);main.pack(side="left",fill="both",expand=True);self.status=tk.StringVar(value="READY — CALIBRATION OPTIONAL");self.info=tk.StringVar(value="")
        s=tk.Frame(main,bg=PANEL);s.pack(fill="x");tk.Label(s,text="SYSTEM STATUS",bg=PANEL,fg=GOLD,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=14,pady=(8,0));tk.Label(s,textvariable=self.status,bg=PANEL,fg=GREEN,font=("Consolas",17,"bold")).pack(anchor="w",padx=14,pady=(0,8))
        cards=tk.Frame(main,bg=BG);cards.pack(fill="x",pady=8);self.cards={}
        for n in ["WEBCAM","PROJECTOR","CALIBRATION","POOKALAM","INTERACTION"]:self.card_widget(cards,n)
        pv=tk.Frame(main,bg="#030307");pv.pack(fill="both",expand=True);tk.Label(pv,text="CAMERA / FLOOR VIEW",bg="#030307",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=8,pady=5);self.preview=tk.Label(pv,bg="#030307");self.preview.pack(expand=True);tk.Label(main,textvariable=self.info,bg=BG,fg=MUTED,font=("Consolas",10)).pack(anchor="w",pady=5)
        self.root.bind("<Escape>",lambda e:self.stop());self.root.bind("<r>",lambda e:self.run());self.root.bind("<s>",lambda e:self.stop())
    def button(self,p,text,cmd,accent=False):tk.Button(p,text=text,command=cmd,bg="#3b3018" if accent else "#1a1a21",fg=GOLD if accent else TEXT,activebackground="#5a471e",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2).pack(fill="x",padx=14,pady=4)
    def card_widget(self,p,n):
        f=tk.Frame(p,bg=PANEL);f.pack(side="left",fill="x",expand=True,padx=2);tk.Label(f,text=n,bg=PANEL,fg=MUTED,font=("Segoe UI",8,"bold")).pack(pady=(6,1));v=tk.Label(f,text="READY",bg=PANEL,fg="#777784",font=("Consolas",9,"bold"));v.pack(pady=(0,6));self.cards[n]=v
    def card(self,n,text,good=None):self.cards[n].configure(text=text,fg="#777784" if good is None else GREEN if good else RED)
    def start_camera(self):self.card("WEBCAM","ONLINE" if self.cap.isOpened() else "OFFLINE",self.cap.isOpened())
    def tick(self):
        now=time.perf_counter();dt=min(.1,now-self.last);self.last=now;self.t+=dt
        if self.cap.isOpened():
            ok,self.frame=self.cap.read()
            if ok:self.card("WEBCAM","ONLINE",True);self.preview_frame()
        if self.mode=="calibrate" and self.frame is not None:self.calibration_step()
        if self.mode in ("interaction","run") and self.frame is not None:self.track()
        if self.mode in ("interaction","run"):self.update_particles(dt)
        if self.mode=="run" and self.projector:self.projector.render(self)
        self.root.after(25,self.tick)
    def preview_frame(self):
        im=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB);im=cv2.resize(im,(760,428));self.preview_photo=ImageTk.PhotoImage(Image.fromarray(im));self.preview.configure(image=self.preview_photo)
    def open_projector(self):
        if not self.projector:self.projector=Projector(self);self.card("PROJECTOR","ONLINE",True)
    def projector_test(self):self.open_projector();self.projector.targets();self.mode="projector";self.status.set("PROJECTOR TEST — VERIFY FULL SCREEN")
    def calibrate(self):self.open_projector();self.projector.targets();self.mode="calibrate";self.card("CALIBRATION","SEARCHING");self.status.set("CALIBRATION — FOUR TARGETS")
    def calibration_step(self):
        cs=find_circles(self.frame);self.info.set(f"Calibration targets detected: {len(cs)}/4")
        if len(cs)!=4:return
        cam=order4([(x,y) for x,y,r in cs]);m=.10;dst=np.float32([[self.projector.w*m,self.projector.h*m],[self.projector.w*(1-m),self.projector.h*m],[self.projector.w*(1-m),self.projector.h*(1-m)],[self.projector.w*m,self.projector.h*(1-m)]]);H,_=cv2.findHomography(cam,dst,0)
        if H is not None:self.H=H.astype(np.float32);self.state.update({"homography":self.H.tolist(),"projector_width":self.projector.w,"projector_height":self.projector.h});save_state(self.state);self.card("CALIBRATION","COMPLETE",True);self.status.set("CALIBRATION COMPLETE");self.mode="idle";self.projector.clear()
    def digital(self):
        p=filedialog.askopenfilename(title="Choose Pookalam image",filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp"),("All files","*.*")])
        if not p:return
        img=cv2.imread(p,cv2.IMREAD_COLOR)
        if img is None:messagebox.showerror("Image","Unable to read image");return
        self.image=img;self.state.update({"source":"digital","image":p});save_state(self.state);self.card("POOKALAM","DIGITAL",True);self.status.set("DIGITAL POOKALAM LOADED — RUN SHOW")
    def physical(self):self.image=None;self.state["source"]="physical";save_state(self.state);self.card("POOKALAM","PHYSICAL",True);self.status.set("PHYSICAL POOKALAM MODE")
    def hybrid(self):
        self.digital()
        if self.image is not None:self.state["source"]="hybrid";save_state(self.state);self.status.set("HYBRID — IMAGE BASE + LIVE EFFECTS")
    def detect(self):
        if self.frame is None:return
        hsv=cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV);mask=((hsv[:,:,1]>50)&(hsv[:,:,2]>45)).astype(np.uint8)*255;mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((9,9),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);h,w=mask.shape;cs=[c for c in cs if .015*w*h<cv2.contourArea(c)<.92*w*h]
        if not cs:self.card("POOKALAM","NOT FOUND",False);self.status.set("NO CLEAR POOKALAM DETECTED");return
        c=max(cs,key=cv2.contourArea);M=cv2.moments(c);cx=M["m10"]/M["m00"];cy=M["m01"]/M["m00"];area=float(cv2.contourArea(c));self.state["pookalam"]={"camera_center":[cx,cy],"area":area,"bbox":list(map(int,cv2.boundingRect(c)))};save_state(self.state);self.card("POOKALAM","DETECTED",True);self.status.set("POOKALAM DETECTED — MASK READY")
    def interaction_test(self):self.mode="interaction";self.interaction_active=False;self.card("INTERACTION","TESTING");self.status.set("INTERACTION TEST — MOVE IN CAMERA VIEW")
    def track(self):
        small=cv2.resize(self.frame,(640,360));m=self.bg.apply(small,learningRate=.002);m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((5,5),np.uint8));m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8));cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(cs,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction_active=False;self.card("INTERACTION","WAITING");return
        M=cv2.moments(c);x=M["m10"]/M["m00"]/640;y=M["m01"]/M["m00"]/360
        if self.H is not None and self.projector:
            q=cv2.perspectiveTransform(np.float32([[[x*640,y*360]]]),self.H)[0,0];x=float(q[0]/self.projector.w);y=float(q[1]/self.projector.h)
        self.interaction=(max(0,min(1,x)),max(0,min(1,y)));self.interaction_strength=max(0,min(1,1-math.hypot(x-.5,y-.5)/.7));self.interaction_active=True;self.card("INTERACTION","ACTIVE",True)
    def update_particles(self,dt):
        if not self.effects["petals"]:return
        if random.random()<min(.7,dt*10):
            a=random.random()*math.tau;r=.16+random.random()*.38;self.particles.append([.5+math.cos(a)*r,.5+math.sin(a)*r,math.cos(a)*.025,math.sin(a)*.025,.8+random.random()*1.5,3+random.random()*4,a,random.choice(["#ffd45a","#ff9a70","#ffcad4","#fff0a8"])])
        alive=[]
        for p in self.particles:
            p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=0.012*dt;p[4]-=dt
            if p[4]>0:alive.append(p)
        self.particles=alive[-500:]
    def run(self):
        self.open_projector();self.mode="run";self.card("CALIBRATION","LOCKED" if self.H is not None else "PREVIEW",self.H is not None);self.card("INTERACTION","ACTIVE",True);self.status.set("SHOW RUNNING — LIVING POOKALAM")
    def stop(self):self.mode="idle";self.interaction_active=False;self.card("INTERACTION","READY");self.status.set("STOPPED");self.projector.clear() if self.projector else None
    def set_effect(self,n):self.effects[n]=self.vars[n].get();self.state.setdefault("effects",{})[n]=self.effects[n];save_state(self.state)
    def reset_effects(self):
        for n,v in self.vars.items():v.set(True);self.effects[n]=True
        self.state["effects"]={};save_state(self.state)
    def close(self):self.stop();self.cap.release();self.root.destroy()

def launch():
    root=tk.Tk();App(root);root.mainloop()

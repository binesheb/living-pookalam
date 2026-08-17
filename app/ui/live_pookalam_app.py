"""Live Pookalam Windows 11 operator application with Developer Mode."""
from __future__ import annotations
import json, math, os, time, tkinter as tk
from tkinter import filedialog, messagebox
import cv2, numpy as np
from PIL import Image, ImageTk
from app.visuals.engine import Interaction, VisualEngine
try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),"../..")); PROFILE=os.path.join(ROOT,"installation_profile.json")
BG="#06070a"; PANEL="#11141a"; PANEL2="#171c23"; BORDER="#2a313b"; TEXT="#f2f4f7"; MUTED="#98a2ae"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7474"; BLUE="#75b8ff"; PURPLE="#bd86ff"
DEFAULT={"camera_index":0,"projector_monitor":1,"projector_width":1920,"projector_height":1080,"homography":None,"source":"generated","image":"","pookalam":None,"effects":{},"showroom":"UNASSIGNED","dev_mode":True}

def load_state():
    try:
        with open(PROFILE,"r",encoding="utf-8") as f:return {**DEFAULT,**json.load(f)}
    except Exception:return DEFAULT.copy()
def save_state(state):
    with open(PROFILE,"w",encoding="utf-8") as f:json.dump(state,f,indent=2)
def order4(points):
    p=np.float32(points); s=p.sum(1); d=np.diff(p,axis=1).reshape(-1); return np.array([p[np.argmin(s)],p[np.argmin(d)],p[np.argmax(s)],p[np.argmax(d)]],np.float32)
def detect_calibration_circles(frame):
    gray=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(9,9),2); circles=cv2.HoughCircles(gray,cv2.HOUGH_GRADIENT,1.2,70,param1=100,param2=30,minRadius=10,maxRadius=100)
    if circles is None:return []
    out=[]
    for x,y,r in np.round(circles[0]).astype(int):
        if all((x-a)**2+(y-b)**2>100**2 for a,b,_ in out):out.append((int(x),int(y),int(r)))
        if len(out)==4:break
    return out

def segment_pookalam(frame):
    if frame is None:return None,None,0.0
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV); mask=((hsv[:,:,1]>=50)&(hsv[:,:,2]>=45)).astype(np.uint8)*255
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((9,9),np.uint8)); mask=cv2.GaussianBlur(mask,(5,5),0); _,mask=cv2.threshold(mask,80,255,cv2.THRESH_BINARY)
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); h,w=mask.shape; candidates=[c for c in contours if .015*w*h<cv2.contourArea(c)<.92*w*h]
    if not candidates:return mask,None,0.0
    c=max(candidates,key=cv2.contourArea); area=float(cv2.contourArea(c)); x,y,bw,bh=cv2.boundingRect(c); fill=area/max(1,bw*bh); coverage=min(1.0,area/(w*h*.30)); per=cv2.arcLength(c,True); circ=0 if per<=0 else min(1.0,4*math.pi*area/(per*per)); conf=max(0,min(1,.5*fill+.3*coverage+.2*circ)); return mask,c,conf

class DrawAdapter:
    def __init__(self,canvas):self.canvas=canvas
    def circle(self,x,y,r,fill,width=0):self.canvas.create_oval(x-r,y-r,x+r,y+r,fill=fill if width==0 else "",outline=fill,width=max(1,width))
    def ellipse(self,rect,fill,width=0):self.canvas.create_oval(*rect,fill=fill if width==0 else "",outline=fill,width=max(1,width))
    def line(self,points,fill,width=1):self.canvas.create_line(*[v for pt in points for v in pt],fill=fill,width=width,smooth=True)
    def polygon(self,points,fill):self.canvas.create_polygon(*[v for pt in points for v in pt],fill=fill)

class ProjectionWindow:
    def __init__(self,app):
        self.app=app; self.win=tk.Toplevel(app.root); self.win.overrideredirect(True); self.win.configure(bg="black"); self.canvas=tk.Canvas(self.win,bg="black",highlightthickness=0); self.canvas.pack(fill="both",expand=True); self.win.bind("<Escape>",lambda _e:app.stop_show()); self.w=int(app.state["projector_width"]); self.h=int(app.state["projector_height"]); self.place()
    def place(self):
        mons=list(get_monitors()) if get_monitors else []; idx=int(self.app.state.get("projector_monitor",1))
        if mons:
            idx=min(max(0,idx),len(mons)-1); m=mons[idx]; self.w,self.h=m.width,m.height; self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost",True)
    def clear(self):self.canvas.delete("all")
    def grid(self):
        self.clear()
        for i in range(1,10):
            x=self.w*i/10; y=self.h*i/10; self.canvas.create_line(x,0,x,self.h,fill="#262c35"); self.canvas.create_line(0,y,self.w,y,fill="#262c35")
        self.canvas.create_text(self.w/2,self.h/2,text="LIVE POOKALAM • MAPPING TEST",fill=GOLD,font=("Segoe UI",28,"bold"))
    def targets(self):
        self.clear(); m=.12; pts=[(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))]; r=min(self.w,self.h)*.028
        for i,(x,y) in enumerate(pts,1):self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline=GOLD,width=5);self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",24,"bold"))
        self.canvas.create_text(self.w/2,self.h*.5,text="PROJECTOR CALIBRATION",fill=GOLD,font=("Segoe UI",28,"bold"))
    def render(self,engine,interaction,image=None,debug_contour=None,debug_mask=None):
        self.clear(); engine.render(DrawAdapter(self.canvas),self.w,self.h,interaction=interaction)
        if self.app.state.get("source")=="digital" and image is not None:
            try:
                im=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB)); im.thumbnail((int(self.w*.72),int(self.h*.72)),Image.Resampling.LANCZOS); self.photo=ImageTk.PhotoImage(im); self.canvas.create_image(self.w/2,self.h/2,image=self.photo)
            except Exception:pass
        if self.app.dev_mode and debug_contour is not None:
            pts=debug_contour.reshape(-1,2).astype(np.float32)
            if self.app.H is not None:
                mapped=cv2.perspectiveTransform(pts.reshape(-1,1,2),self.app.H).reshape(-1,2); mapped[:,0]*=self.w/max(1,self.app.state.get("projector_width",1920)); mapped[:,1]*=self.h/max(1,self.app.state.get("projector_height",1080))
            else:
                ch,cw=self.app.frame.shape[:2] if self.app.frame is not None else (720,1280); mapped=pts.copy(); mapped[:,0]=mapped[:,0]/cw*self.w; mapped[:,1]=mapped[:,1]/ch*self.h
            poly=[(float(x),float(y)) for x,y in mapped]
            if len(poly)>=2:self.canvas.create_line(*[v for p in poly for v in p],fill=PURPLE,width=5,smooth=True)
            self.canvas.create_text(40,40,text="DEV • POOKALAM EDGE",anchor="nw",fill=PURPLE,font=("Segoe UI",18,"bold")); self.canvas.create_text(40,72,text="Real camera segmentation",anchor="nw",fill=TEXT,font=("Segoe UI",11))

class LivePookalamApp:
    NAV=[("HOME","home"),("SOURCE","source"),("CALIBRATE","calibrate"),("DETECT","detect"),("EXPERIENCE","experience"),("RUN SHOW","run")]
    def __init__(self,root):
        self.root=root; self.state=load_state(); self.mode="home"; self.dev_mode=bool(self.state.get("dev_mode",True)); self.root.title("Live Pookalam — developed by bnsh.eb"); self.root.geometry("1440x900"); self.root.configure(bg=BG); self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.cap=cv2.VideoCapture(int(self.state.get("camera_index",0)),cv2.CAP_DSHOW); self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720); self.frame=None; self.image=None; self.proj=None; self.H=np.float32(self.state["homography"]) if self.state.get("homography") else None; self.interaction=Interaction(); self.engine=VisualEngine(); self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False); self.last=time.perf_counter(); self.debug_contour=None; self.debug_mask=None; self.build_ui(); self.apply_saved_effects(); self.tick()
    def build_ui(self):
        header=tk.Frame(self.root,bg=BG); header.pack(fill="x",padx=26,pady=(18,10)); brand=tk.Frame(header,bg=BG); brand.pack(side="left"); tk.Label(brand,text="LIVE POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",28,"bold")).pack(anchor="w"); tk.Label(brand,text="Interactive Projection Experience • ONAM 2026",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w"); tk.Label(header,text="developed by bnsh.eb",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(side="left",padx=30,pady=(0,4)); self.dev_var=tk.BooleanVar(value=self.dev_mode); tk.Checkbutton(header,text="DEVELOPER MODE",variable=self.dev_var,command=self.toggle_dev_mode,bg=BG,fg=PURPLE if self.dev_mode else MUTED,selectcolor="#20242b",activebackground=BG,activeforeground=PURPLE,font=("Segoe UI",10,"bold")).pack(side="right")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=26,pady=8); self.nav=tk.Frame(body,bg=PANEL,width=250); self.nav.pack(side="left",fill="y",padx=(0,16)); self.nav.pack_propagate(False); tk.Label(self.nav,text="SHOW WORKFLOW",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(18,8)); self.nav_buttons={}
        for label,key in self.NAV:
            b=tk.Button(self.nav,text=label,command=lambda k=key:self.show_page(k),bg=PANEL2,fg=TEXT,activebackground="#2b313a",activeforeground="white",relief="flat",anchor="w",font=("Segoe UI",11,"bold"),height=2); b.pack(fill="x",padx=12,pady=3); self.nav_buttons[key]=b
        tk.Frame(self.nav,bg=BORDER,height=1).pack(fill="x",padx=12,pady=14); tk.Label(self.nav,text="SYSTEM",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(0,7)); self.sysvar=tk.StringVar(value="Starting"); tk.Label(self.nav,textvariable=self.sysvar,bg=PANEL,fg=GREEN,font=("Consolas",10),justify="left").pack(anchor="w",padx=18); tk.Label(self.nav,text="F11 Fullscreen\nESC Stop show\nC Calibration\nR Run show",bg=PANEL,fg=MUTED,font=("Consolas",9),justify="left").pack(side="bottom",anchor="w",padx=18,pady=18); self.main=tk.Frame(body,bg=BG); self.main.pack(side="left",fill="both",expand=True); self.root.bind("<Escape>",lambda _e:self.stop_show()); self.root.bind("<F11>",lambda _e:self.toggle_fullscreen()); self.root.bind("<c>",lambda _e:self.show_page("calibrate")); self.root.bind("<r>",lambda _e:self.run_show()); self.show_page("home")
    def toggle_dev_mode(self): self.dev_mode=bool(self.dev_var.get()); self.state["dev_mode"]=self.dev_mode; save_state(self.state)
    def clear_main(self):
        for w in self.main.winfo_children():w.destroy()
    def title(self,t,s):tk.Label(self.main,text=t,bg=BG,fg=TEXT,font=("Segoe UI",24,"bold")).pack(anchor="w"); tk.Label(self.main,text=s,bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",pady=(2,14))
    def card(self,parent,title,value,colour=TEXT):
        f=tk.Frame(parent,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); f.pack(side="left",fill="both",expand=True,padx=4); tk.Label(f,text=title,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=(10,3)); tk.Label(f,text=value,bg=PANEL2,fg=colour,font=("Consolas",14,"bold")).pack(anchor="w",padx=12,pady=(0,10))
    def action(self,parent,text,cmd,primary=False):tk.Button(parent,text=text,command=cmd,bg="#4a3a18" if primary else PANEL2,fg=GOLD if primary else TEXT,activebackground="#624d20",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2,padx=14).pack(side="left",padx=4)
    def show_page(self,key):
        self.mode=key; self.clear_main()
        for k,b in self.nav_buttons.items():b.configure(bg="#3a301c" if k==key else PANEL2,fg=GOLD if k==key else TEXT)
        getattr(self,"page_"+key)()
    def page_home(self):
        self.title("Ready to make the Pookalam come alive.","Workflow: Source → Calibrate → Detect → Experience → Run. Developer Mode exposes real geometry on the projector.")
        cards=tk.Frame(self.main,bg=BG);cards.pack(fill="x",pady=4); self.card(cards,"WEBCAM","ONLINE" if self.cap.isOpened() else "OFFLINE",GREEN if self.cap.isOpened() else RED); self.card(cards,"PROJECTOR","READY",GREEN); self.card(cards,"CALIBRATION","SAVED" if self.H is not None else "NOT SET",GREEN if self.H is not None else GOLD); self.card(cards,"SOURCE",str(self.state.get("source","generated")).upper(),BLUE); self.card(cards,"MODE","DEVELOPER" if self.dev_mode else "SHOW",PURPLE if self.dev_mode else GREEN)
        tk.Label(self.main,text="WORKFLOW",bg=BG,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(22,7)); q=tk.Frame(self.main,bg=BG);q.pack(fill="x")
        for t,c,p in [("1 SOURCE",lambda:self.show_page("source"),False),("2 CALIBRATE",lambda:self.show_page("calibrate"),False),("3 DETECT",lambda:self.show_page("detect"),False),("4 EXPERIENCE",lambda:self.show_page("experience"),False),("5 RUN SHOW",self.run_show,True)]:self.action(q,t,c,p)
        f=tk.Frame(self.main,bg="#030407");f.pack(fill="both",expand=True,pady=18);tk.Label(f,text="LIVE CAMERA / FLOOR PREVIEW",bg="#030407",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=10,pady=8);self.preview=tk.Label(f,bg="#030407");self.preview.pack(expand=True)
    def page_source(self):
        self.title("Choose the Pookalam source.","Digital is the best development canvas; Physical and Hybrid are for the real installation."); modes=tk.Frame(self.main,bg=BG);modes.pack(fill="x",pady=10)
        for n,d,c in [("DIGITAL","Upload a Pookalam image and project it.",self.digital),("PHYSICAL","Use the real flower Pookalam as the canvas.",self.physical),("HYBRID","Use the real Pookalam plus projected digital effects.",self.hybrid)]:
            f=tk.Frame(modes,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER);f.pack(side="left",fill="both",expand=True,padx=5);tk.Label(f,text=n,bg=PANEL2,fg=GOLD,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=18,pady=(18,5));tk.Label(f,text=d,bg=PANEL2,fg=MUTED,font=("Segoe UI",10),wraplength=250,justify="left").pack(anchor="w",padx=18,pady=4);self.action(f,"SELECT",c)
    def page_calibrate(self):
        self.title("Calibrate the installation.","Four projected targets establish the camera → projector mapping for the floor plane.");box=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER);box.pack(fill="x",pady=8);tk.Label(box,text="INSTALLATION CALIBRATION",bg=PANEL,fg=GOLD,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=18,pady=(15,5));tk.Label(box,text="Put the camera where it will stay. Extend the projector in Windows. Start calibration and keep all four targets visible.",bg=PANEL,fg=TEXT,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=18,pady=5);row=tk.Frame(box,bg=PANEL);row.pack(anchor="w",padx=14,pady=12);self.action(row,"START CALIBRATION",self.calibrate,True);self.action(row,"PROJECTOR GRID",self.projector_test);self.action(row,"CLEAR SAVED MAP",self.clear_calibration);result=tk.Frame(self.main,bg=PANEL2);result.pack(fill="x",pady=10);tk.Label(result,text="CURRENT MAP",bg=PANEL2,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(12,2));tk.Label(result,text="CALIBRATED" if self.H is not None else "NOT CALIBRATED — DEVELOPER MODE AND VISUAL TESTING STILL AVAILABLE",bg=PANEL2,fg=GREEN if self.H is not None else GOLD,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(0,12))
    def page_detect(self):
        self.title("Detect the real Pookalam.","Developer Mode projects the real detected edge/contour so we can evaluate the segmentation before defining final interaction.");row=tk.Frame(self.main,bg=BG);row.pack(fill="x",pady=8);self.action(row,"DETECT NOW",self.detect,True);self.action(row,"SHOW EDGE ON PROJECTOR",self.dev_edge_preview);self.action(row,"INTERACTION TEST",self.interaction_test);f=tk.Frame(self.main,bg="#030407");f.pack(fill="both",expand=True,pady=10);self.detect_preview=tk.Label(f,bg="#030407");self.detect_preview.pack(expand=True);self.update_detect_preview()
        p=self.state.get("pookalam");tk.Label(self.main,text=(f"LOCKED • area {p.get('area',0):.0f} px² • confidence {p.get('confidence',0):.0%}" if p else "Not locked"),bg=BG,fg=GREEN if p else MUTED,font=("Consolas",11,"bold")).pack(anchor="w")
    def page_experience(self):
        self.title("Compose the living experience.","Build the visual language now. Interaction behavior is intentionally left open for later decisions.");grid=tk.Frame(self.main,bg=BG);grid.pack(fill="x")
        for i,n in enumerate(self.engine.EFFECTS):
            if i%3==0:row=tk.Frame(grid,bg=BG);row.pack(fill="x",pady=4)
            v=tk.BooleanVar(value=self.engine.effects[n]);tk.Checkbutton(row,text=n.replace("_"," ").title(),variable=v,command=lambda name=n,var=v:self.set_effect(name,var.get()),bg=PANEL2,fg=TEXT,selectcolor="#232831",activebackground=PANEL2,activeforeground=TEXT,font=("Segoe UI",10),anchor="w",width=24).pack(side="left",fill="x",expand=True,padx=4,ipady=8)
        controls=tk.Frame(self.main,bg=PANEL);controls.pack(fill="x",pady=14);tk.Label(controls,text="MASTER",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(side="left",padx=14);self.action(controls,"ALL ON",lambda:self.set_all(True));self.action(controls,"ALL OFF",lambda:self.set_all(False));self.action(controls,"RESET",self.reset_effects)
    def page_run(self):
        self.title("Run Live Pookalam.","Turn Developer Mode off for the clean show surface. In Developer Mode, the detected physical boundary remains visible.");box=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER);box.pack(fill="x",pady=8);tk.Label(box,text="LIVE POOKALAM",bg=PANEL,fg=GOLD,font=("Segoe UI",20,"bold")).pack(anchor="w",padx=18,pady=(18,3));tk.Label(box,text="DEVELOPER DIAGNOSTIC" if self.dev_mode else "SHOW MODE",bg=PANEL,fg=PURPLE if self.dev_mode else GREEN,font=("Consolas",18,"bold")).pack(anchor="w",padx=18,pady=(0,14));row=tk.Frame(self.main,bg=BG);row.pack(fill="x",pady=10);self.action(row,"RUN SHOW",self.run_show,True);self.action(row,"STOP",self.stop_show);self.action(row,"PROJECTOR TEST",self.projector_test);self.action(row,"INTERACTION TEST",self.interaction_test)
    def update_preview(self):
        if self.frame is None or not hasattr(self,"preview"):return
        im=cv2.cvtColor(cv2.resize(self.frame,(820,460)),cv2.COLOR_BGR2RGB);self.photo=ImageTk.PhotoImage(Image.fromarray(im));self.preview.configure(image=self.photo)
    def update_detect_preview(self):
        if not hasattr(self,"detect_preview") or self.frame is None:return
        im=self.frame.copy();p=self.state.get("pookalam")
        if p:
            x,y=p["camera_center"];cv2.circle(im,(int(x),int(y)),18,(0,255,0),3);x0,y0,w,h=p["bbox"];cv2.rectangle(im,(x0,y0),(x0+w,y0+h),(0,255,0),3);cv2.putText(im,"POOKALAM LOCKED",(x0,max(30,y0-10)),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,0),2)
        im=cv2.cvtColor(cv2.resize(im,(900,506)),cv2.COLOR_BGR2RGB);self.detect_photo=ImageTk.PhotoImage(Image.fromarray(im));self.detect_preview.configure(image=self.detect_photo)
    def tick(self):
        now=time.perf_counter();dt=min(.1,now-self.last);self.last=now
        if self.cap.isOpened():
            ok,self.frame=self.cap.read()
            if ok:
                self.sysvar.set("WEBCAM ONLINE\nPROJECTOR READY\nCALIBRATION %s\nMODE %s"%("SAVED" if self.H is not None else "NOT SET","DEVELOPER" if self.dev_mode else "SHOW"));self.update_preview();self.update_detect_preview();
                if self.dev_mode and self.proj and self.mode in ("run","detect"):self.debug_mask,self.debug_contour,self.debug_confidence=segment_pookalam(self.frame)
        if self.mode in ("interaction","run"):self.track_interaction()
        self.engine.update(dt,self.interaction)
        if self.mode=="run" and self.proj:self.proj.render(self.engine,self.interaction,self.image,self.debug_contour if self.dev_mode else None,self.debug_mask if self.dev_mode else None)
        self.root.after(25,self.tick)
    def open_projector(self):
        if not self.proj:self.proj=ProjectionWindow(self)
    def projector_test(self):self.open_projector();self.proj.grid();self.show_page("run")
    def calibrate(self):self.open_projector();self.proj.targets();self.mode="calibrate";self.calibration_started=time.time();self.status_message("CALIBRATION TARGETS VISIBLE")
    def calibration_step(self):
        if self.frame is None or not self.proj:return
        cs=detect_calibration_circles(self.frame);self.status_message(f"CALIBRATION TARGETS {len(cs)}/4")
        if len(cs)!=4:return
        cam=order4([(x,y) for x,y,_ in cs]);m=.12;pw,ph=self.proj.w,self.proj.h;dst=np.float32([[pw*m,ph*m],[pw*(1-m),ph*m],[pw*(1-m),ph*(1-m)],[pw*m,ph*(1-m)]]);H,_=cv2.findHomography(cam,dst,0)
        if H is not None:self.H=H.astype(np.float32);self.state.update({"homography":self.H.tolist(),"projector_width":pw,"projector_height":ph});save_state(self.state);self.mode="home";self.proj.clear();self.show_page("calibrate")
    def digital(self):
        p=filedialog.askopenfilename(title="Choose Pookalam image",filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp")]);
        if not p:return
        self.image=cv2.imread(p);self.state.update({"source":"digital","image":p});save_state(self.state);self.show_page("experience")
    def physical(self):self.image=None;self.state["source"]="physical";save_state(self.state);self.show_page("detect")
    def hybrid(self):self.digital();self.state["source"]="hybrid";save_state(self.state)
    def detect(self):
        if self.frame is None:return
        mask,contour,confidence=segment_pookalam(self.frame)
        if contour is None:messagebox.showwarning("Pookalam not found","Keep the full Pookalam visible and use consistent lighting.");return
        M=cv2.moments(contour);cx=M["m10"]/M["m00"];cy=M["m01"]/M["m00"];area=float(cv2.contourArea(contour));bbox=cv2.boundingRect(contour);self.state["pookalam"]={"camera_center":[cx,cy],"area":area,"bbox":list(map(int,bbox)),"confidence":confidence};save_state(self.state);self.show_page("detect")
    def dev_edge_preview(self):
        if not self.dev_mode:messagebox.showinfo("Developer Mode","Enable DEVELOPER MODE first.");return
        if self.frame is None:return
        self.open_projector();self.mode="run";self.debug_mask,self.debug_contour,self.debug_confidence=segment_pookalam(self.frame);self.proj.render(self.engine,Interaction(),self.image,self.debug_contour,self.debug_mask)
    def interaction_test(self):self.mode="interaction";self.interaction=Interaction();self.show_page("run")
    def track_interaction(self):
        small=cv2.resize(self.frame,(640,360));mask=self.bg.apply(small,learningRate=.002);mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8));cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);c=max(cs,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction=Interaction();return
        M=cv2.moments(c);x=M["m10"]/M["m00"]/640;y=M["m01"]/M["m00"]/360
        if self.H is not None and self.proj:q=cv2.perspectiveTransform(np.float32([[[x*640,y*360]]]),self.H)[0,0];x=float(q[0]/self.proj.w);y=float(q[1]/self.proj.h)
        strength=max(0,min(1,1-math.hypot(x-.5,y-.5)/.72));self.interaction=Interaction(max(0,min(1,x)),max(0,min(1,y)),strength,True)
    def run_show(self):self.open_projector();self.mode="run";self.show_page("run")
    def stop_show(self):self.mode="home";self.interaction=Interaction();self.debug_contour=None;self.debug_mask=None;self.proj.clear() if self.proj else None
    def clear_calibration(self):self.H=None;self.state["homography"]=None;save_state(self.state);self.show_page("calibrate")
    def set_effect(self,name,value):self.engine.set_effect(name,value);self.state.setdefault("effects",{})[name]=value;save_state(self.state)
    def apply_saved_effects(self):
        for n,v in self.state.get("effects",{}).items():self.engine.set_effect(n,v)
    def set_all(self,value):self.engine.set_all(value);self.state["effects"]={n:value for n in self.engine.EFFECTS};save_state(self.state)
    def reset_effects(self):self.set_all(True)
    def status_message(self,text):self.sysvar.set(text)
    def toggle_fullscreen(self):self.root.attributes("-fullscreen",not bool(self.root.attributes("-fullscreen")))
    def close(self):
        try:self.stop_show();self.cap.release()
        finally:self.root.destroy()

def launch():
    root=tk.Tk();LivePookalamApp(root);root.mainloop()

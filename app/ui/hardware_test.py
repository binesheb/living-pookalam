"""Live Pookalam Windows 11 operator application.

Guided workflow:
  1. HOME / system check
  2. SOURCE / digital, physical or hybrid
  3. CALIBRATE / optional installation mapping
  4. DETECT / lock physical Pookalam geometry
  5. EXPERIENCE / compose effect layers
  6. RUN / safe full-screen show

Designed for repeated showroom deployment. Calibration and installation state
are persisted locally; application logic remains shared across showrooms.
"""
from __future__ import annotations

import json, math, os, time
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageOps

from app.visuals.engine import Interaction, VisualEngine
try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PROFILE = os.path.join(ROOT, "installation_profile.json")
BG, PANEL, PANEL2, BORDER = "#07080b", "#11141a", "#171b22", "#2a3039"
TEXT, MUTED, GOLD, GREEN, RED, BLUE = "#f4f5f7", "#9ba3ae", "#ffd45a", "#70e89a", "#ff7474", "#75b8ff"
DEFAULT = {
    "camera_index": 0, "projector_monitor": 1, "projector_width": 1920,
    "projector_height": 1080, "homography": None, "source": "generated",
    "image": "", "pookalam": None, "effects": {}, "showroom": "UNASSIGNED"
}


def load_state():
    try:
        with open(PROFILE, "r", encoding="utf-8") as f:
            s = json.load(f)
        return {**DEFAULT, **s}
    except Exception:
        return DEFAULT.copy()


def save_state(state):
    with open(PROFILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def order4(points):
    p = np.float32(points)
    s, d = p.sum(1), np.diff(p, axis=1).reshape(-1)
    return np.array([p[np.argmin(s)], p[np.argmin(d)], p[np.argmax(s)], p[np.argmax(d)]], np.float32)


def detect_four_circles(frame):
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (9, 9), 2)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, 70, param1=100, param2=30, minRadius=10, maxRadius=100)
    if circles is None:
        return []
    out = []
    for x, y, r in np.round(circles[0]).astype(int):
        if all((x-a)**2 + (y-b)**2 > 100**2 for a, b, _ in out):
            out.append((x, y, r))
        if len(out) == 4:
            break
    return out


class DrawAdapter:
    def __init__(self, canvas): self.canvas = canvas
    def circle(self, x, y, r, fill, width=0):
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill if width == 0 else "", outline=fill, width=max(1, width))
    def ellipse(self, rect, fill, width=0):
        self.canvas.create_oval(*rect, fill=fill if width == 0 else "", outline=fill, width=max(1, width))
    def line(self, points, fill, width=1):
        self.canvas.create_line(*[v for pt in points for v in pt], fill=fill, width=width, smooth=True)
    def polygon(self, points, fill):
        self.canvas.create_polygon(*[v for pt in points for v in pt], fill=fill)


class ProjectionWindow:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.configure(bg="black")
        self.canvas = tk.Canvas(self.win, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.bind("<Escape>", lambda e: app.stop_show())
        self.w = app.state["projector_width"]; self.h = app.state["projector_height"]
        self.place()

    def place(self):
        mons = list(get_monitors()) if get_monitors else []
        idx = int(self.app.state.get("projector_monitor", 1))
        if mons:
            idx = min(idx, len(mons)-1)
            m = mons[idx]; self.w, self.h = m.width, m.height
            self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:
            self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost", True)

    def clear(self): self.canvas.delete("all")

    def targets(self):
        self.clear(); m = .12
        pts = [(self.w*m,self.h*m),(self.w*(1-m),self.h*m),(self.w*(1-m),self.h*(1-m)),(self.w*m,self.h*(1-m))]
        r = min(self.w,self.h)*.028
        for i,(x,y) in enumerate(pts,1):
            self.canvas.create_oval(x-r,y-r,x+r,y+r,fill="white",outline=GOLD,width=5)
            self.canvas.create_text(x,y,text=str(i),fill="black",font=("Segoe UI",24,"bold"))
        self.canvas.create_text(self.w/2,self.h*.5,text="PROJECTOR CALIBRATION",fill=GOLD,font=("Segoe UI",28,"bold"))

    def grid(self):
        self.clear()
        for i in range(1,10):
            x=self.w*i/10; self.canvas.create_line(x,0,x,self.h,fill="#262c35",width=1)
            y=self.h*i/10; self.canvas.create_line(0,y,self.w,y,fill="#262c35",width=1)
        self.canvas.create_text(self.w/2,self.h/2,text="LIVE POOKALAM • MAPPING TEST",fill=GOLD,font=("Segoe UI",28,"bold"))

    def render(self, engine, interaction, image=None):
        self.clear()
        if image is not None:
            try:
                im = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                im.thumbnail((int(self.w*.72), int(self.h*.72)), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(im)
                self.canvas.create_image(self.w/2,self.h/2,image=self.photo)
            except Exception: pass
        engine.render(DrawAdapter(self.canvas), self.w, self.h, interaction=interaction)


class App:
    NAV = [("HOME","home"),("SOURCE","source"),("CALIBRATE","calibrate"),("DETECT","detect"),("EXPERIENCE","experience"),("RUN SHOW","run")]
    def __init__(self, root):
        self.root=root; self.state=load_state(); self.mode="home"; self.running=True
        self.root.title("Live Pookalam — developed by bnsh.eb"); self.root.geometry("1440x900"); self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.cap=cv2.VideoCapture(int(self.state.get("camera_index",0)),cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,1280); self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
        self.frame=None; self.image=None; self.proj=None; self.H=np.float32(self.state["homography"]) if self.state.get("homography") else None
        self.interaction=Interaction(); self.engine=VisualEngine(); self.bg=cv2.createBackgroundSubtractorMOG2(history=250,varThreshold=28,detectShadows=False)
        self.last=time.perf_counter(); self.build_ui(); self.apply_saved_effects(); self.tick()

    def build_ui(self):
        header=tk.Frame(self.root,bg=BG); header.pack(fill="x",padx=26,pady=(18,10))
        brand=tk.Frame(header,bg=BG); brand.pack(side="left")
        tk.Label(brand,text="LIVE POOKALAM",bg=BG,fg=GOLD,font=("Segoe UI",28,"bold")).pack(anchor="w")
        tk.Label(brand,text="Interactive Projection Experience  •  ONAM 2026",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w")
        tk.Label(header,text="developed by bnsh.eb",bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(side="right",anchor="s")

        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=26,pady=8)
        self.nav=tk.Frame(body,bg=PANEL,width=250); self.nav.pack(side="left",fill="y",padx=(0,16)); self.nav.pack_propagate(False)
        tk.Label(self.nav,text="SHOW WORKFLOW",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(18,8))
        self.nav_buttons={}
        for label,key in self.NAV:
            b=tk.Button(self.nav,text=label,command=lambda k=key:self.show_page(k),bg=PANEL2,fg=TEXT,activebackground="#2b313a",activeforeground="white",relief="flat",anchor="w",font=("Segoe UI",11,"bold"),height=2)
            b.pack(fill="x",padx=12,pady=3); self.nav_buttons[key]=b
        tk.Frame(self.nav,bg=BORDER,height=1).pack(fill="x",padx=12,pady=14)
        tk.Label(self.nav,text="SYSTEM",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(0,7))
        self.sysvar=tk.StringVar(value="Starting")
        tk.Label(self.nav,textvariable=self.sysvar,bg=PANEL,fg=GREEN,font=("Consolas",10),justify="left").pack(anchor="w",padx=18)
        tk.Label(self.nav,text="F11  Full screen\nESC  Stop show\nC    Calibration\nR    Run show",bg=PANEL,fg=MUTED,font=("Consolas",9),justify="left").pack(side="bottom",anchor="w",padx=18,pady=18)

        self.main=tk.Frame(body,bg=BG); self.main.pack(side="left",fill="both",expand=True)
        self.build_home(); self.show_page("home")
        self.root.bind("<Escape>",lambda e:self.stop_show()); self.root.bind("<F11>",lambda e:self.toggle_fullscreen()); self.root.bind("<c>",lambda e:self.show_page("calibrate")); self.root.bind("<r>",lambda e:self.run_show())

    def clear_main(self):
        for w in self.main.winfo_children(): w.destroy()

    def title(self, title, subtitle):
        tk.Label(self.main,text=title,bg=BG,fg=TEXT,font=("Segoe UI",24,"bold")).pack(anchor="w")
        tk.Label(self.main,text=subtitle,bg=BG,fg=MUTED,font=("Segoe UI",10)).pack(anchor="w",pady=(2,14))

    def card(self,parent,title,value,colour=TEXT):
        f=tk.Frame(parent,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); f.pack(side="left",fill="both",expand=True,padx=4)
        tk.Label(f,text=title,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=(10,3))
        tk.Label(f,text=value,bg=PANEL2,fg=colour,font=("Consolas",14,"bold")).pack(anchor="w",padx=12,pady=(0,10))

    def action(self,parent,text,cmd,primary=False):
        tk.Button(parent,text=text,command=cmd,bg="#4a3a18" if primary else PANEL2,fg=GOLD if primary else TEXT,activebackground="#624d20",activeforeground="white",relief="flat",font=("Segoe UI",10,"bold"),height=2,padx=14).pack(side="left",padx=4)

    def build_home(self): pass

    def show_page(self,key):
        self.mode=key; self.clear_main(); self.nav_buttons[key].configure(bg="#3a301c",fg=GOLD)
        for k,b in self.nav_buttons.items():
            if k!=key:b.configure(bg=PANEL2,fg=TEXT)
        getattr(self,"page_"+key)()

    def page_home(self):
        self.title("Ready to make the Pookalam come alive.","A guided operator workflow. Calibration can be done later.")
        status=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); status.pack(fill="x",pady=(0,12))
        tk.Label(status,text="SYSTEM READY",bg=PANEL,fg=GREEN,font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=(14,2))
        tk.Label(status,text="Start with a digital Pookalam to test the complete visual engine, or choose Physical when the floor installation is ready.",bg=PANEL,fg=TEXT,font=("Segoe UI",11),wraplength=850,justify="left").pack(anchor="w",padx=18,pady=(0,14))
        cards=tk.Frame(self.main,bg=BG); cards.pack(fill="x",pady=4)
        self.card(cards,"WEBCAM","ONLINE" if self.cap.isOpened() else "OFFLINE",GREEN if self.cap.isOpened() else RED)
        self.card(cards,"PROJECTOR","READY",GREEN)
        self.card(cards,"CALIBRATION","SAVED" if self.H is not None else "NOT REQUIRED",GREEN if self.H is not None else GOLD)
        self.card(cards,"SOURCE",str(self.state.get("source","generated")).upper(),BLUE)
        self.card(cards,"SHOWROOM",self.state.get("showroom","UNASSIGNED"),TEXT)
        tk.Label(self.main,text="QUICK START",bg=BG,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(22,7))
        q=tk.Frame(self.main,bg=BG); q.pack(fill="x")
        for t,c in [("1  Choose Pookalam",lambda:self.show_page("source")),("2  Test Projector",self.projector_test),("3  Calibrate Later",lambda:self.show_page("calibrate")),("4  Run Experience",self.run_show)]: self.action(q,t,c,t.startswith("4"))
        self.show_preview_panel()

    def show_preview_panel(self):
        f=tk.Frame(self.main,bg="#030407",height=360); f.pack(fill="both",expand=True,pady=18)
        tk.Label(f,text="LIVE CAMERA / FLOOR PREVIEW",bg="#030407",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=10,pady=8)
        self.preview=tk.Label(f,bg="#030407"); self.preview.pack(expand=True)

    def page_source(self):
        self.title("Choose the Pookalam source.","The visual engine is shared. Only the source of the physical canvas changes.")
        modes=tk.Frame(self.main,bg=BG); modes.pack(fill="x",pady=10)
        for name,desc,cmd in [("DIGITAL","Upload an image. Ideal for development and effect design.",self.digital), ("PHYSICAL","Use the real flower Pookalam detected by the webcam.",self.physical), ("HYBRID","Keep the real Pookalam and add digital light/effects.",self.hybrid)]:
            f=tk.Frame(modes,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); f.pack(side="left",fill="both",expand=True,padx=5)
            tk.Label(f,text=name,bg=PANEL2,fg=GOLD,font=("Segoe UI",14,"bold")).pack(anchor="w",padx=18,pady=(18,5)); tk.Label(f,text=desc,bg=PANEL2,fg=MUTED,font=("Segoe UI",10),wraplength=250,justify="left").pack(anchor="w",padx=18,pady=4); self.action(f,"SELECT",cmd)
        info=tk.Frame(self.main,bg=PANEL); info.pack(fill="x",pady=18)
        tk.Label(info,text="CURRENT SOURCE",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(12,2)); tk.Label(info,text=str(self.state.get("source","generated")).upper(),bg=PANEL,fg=GREEN,font=("Consolas",18,"bold")).pack(anchor="w",padx=18,pady=(0,12))

    def page_calibrate(self):
        self.title("Calibrate only when you are ready.","Four projected targets establish the camera → projector floor mapping. The saved profile can be reused.")
        box=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); box.pack(fill="x",pady=8)
        tk.Label(box,text="INSTALLATION CALIBRATION",bg=PANEL,fg=GOLD,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=18,pady=(15,5))
        tk.Label(box,text="1. Extend the projector in Windows.  2. Put the camera where it will stay.  3. Click Start Calibration.  4. Keep all four targets visible.",bg=PANEL,fg=TEXT,font=("Segoe UI",10),wraplength=850,justify="left").pack(anchor="w",padx=18,pady=5)
        row=tk.Frame(box,bg=PANEL); row.pack(anchor="w",padx=14,pady=12); self.action(row,"START CALIBRATION",self.calibrate,True); self.action(row,"PROJECTOR GRID",self.projector_test); self.action(row,"CLEAR SAVED MAP",self.clear_calibration)
        result=tk.Frame(self.main,bg=PANEL2); result.pack(fill="x",pady=10); tk.Label(result,text="CURRENT",bg=PANEL2,fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="w",padx=18,pady=(12,2)); tk.Label(result,text="CALIBRATED" if self.H is not None else "NOT CALIBRATED — PREVIEW MODE AVAILABLE",bg=PANEL2,fg=GREEN if self.H is not None else GOLD,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=18,pady=(0,12))

    def page_detect(self):
        self.title("Find and lock the Pookalam.","Detection uses the camera view. The contour is the primary geometry; centre and radius are derived from it.")
        row=tk.Frame(self.main,bg=BG); row.pack(fill="x",pady=8); self.action(row,"DETECT NOW",self.detect,True); self.action(row,"INTERACTION TEST",self.interaction_test); self.action(row,"SHOW CAMERA",self.show_page_home)
        f=tk.Frame(self.main,bg="#030407"); f.pack(fill="both",expand=True,pady=10); self.detect_preview=tk.Label(f,bg="#030407"); self.detect_preview.pack(expand=True); self.update_detect_preview()
        p=self.state.get("pookalam")
        tk.Label(self.main,text=("LOCKED • area %.0f px²"%p.get("area",0)) if p else "Not locked",bg=BG,fg=GREEN if p else MUTED,font=("Consolas",11,"bold")).pack(anchor="w")

    def show_page_home(self): self.show_page("home")

    def page_experience(self):
        self.title("Compose the living experience.","Each layer can be switched independently. Effects are designed in normalized Pookalam space.")
        grid=tk.Frame(self.main,bg=BG); grid.pack(fill="x")
        for i,name in enumerate(self.engine.EFFECTS):
            r=i//3; c=i%3
            if c==0: row=tk.Frame(grid,bg=BG); row.pack(fill="x",pady=4)
            v=tk.BooleanVar(value=self.engine.effects[name])
            cb=tk.Checkbutton(row,text=name.replace("_"," ").title(),variable=v,command=lambda n=name,x=v:self.set_effect(n,x.get()),bg=PANEL2,fg=TEXT,selectcolor="#232831",activebackground=PANEL2,activeforeground=TEXT,font=("Segoe UI",10),anchor="w",width=24)
            cb.pack(side="left",fill="x",expand=True,padx=4,ipady=8)
        controls=tk.Frame(self.main,bg=PANEL); controls.pack(fill="x",pady=14); tk.Label(controls,text="MASTER",bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")).pack(side="left",padx=14); self.action(controls,"ALL ON",lambda:self.set_all(True)); self.action(controls,"ALL OFF",lambda:self.set_all(False)); self.action(controls,"RESET",self.reset_effects)

    def page_run(self):
        self.title("Show control.","Once RUN is pressed, the projector window becomes the experience surface. ESC always stops safely.")
        status=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); status.pack(fill="x",pady=8)
        tk.Label(status,text="LIVE POOKALAM",bg=PANEL,fg=GOLD,font=("Segoe UI",20,"bold")).pack(anchor="w",padx=18,pady=(18,3)); tk.Label(status,text="READY" if self.mode!="run" else "RUNNING",bg=PANEL,fg=GREEN,font=("Consolas",18,"bold")).pack(anchor="w",padx=18,pady=(0,14))
        row=tk.Frame(self.main,bg=BG); row.pack(fill="x",pady=10); self.action(row,"RUN SHOW",self.run_show,True); self.action(row,"STOP",self.stop_show); self.action(row,"PROJECTOR TEST",self.projector_test); self.action(row,"INTERACTION TEST",self.interaction_test)
        notes=tk.Frame(self.main,bg=PANEL2); notes.pack(fill="x",pady=12); tk.Label(notes,text="FINAL-DAY INTENT",bg=PANEL2,fg=GOLD,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18,pady=(12,4)); tk.Label(notes,text="Turn on projector → turn on webcam → start Live Pookalam → verify profile → RUN SHOW.",bg=PANEL2,fg=TEXT,font=("Segoe UI",11)).pack(anchor="w",padx=18,pady=(0,14))

    def update_preview(self):
        if self.frame is None or not hasattr(self,"preview"): return
        im=cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB); im=cv2.resize(im,(820,460)); self.photo=ImageTk.PhotoImage(Image.fromarray(im)); self.preview.configure(image=self.photo)

    def update_detect_preview(self):
        if not hasattr(self,"detect_preview") or self.frame is None:return
        im=self.frame.copy(); p=self.state.get("pookalam")
        if p:
            x,y=p["camera_center"]; cv2.circle(im,(int(x),int(y)),18,(0,255,0),3); x0,y0,w,h=p["bbox"]; cv2.rectangle(im,(x0,y0),(x0+w,y0+h),(0,255,0),3); cv2.putText(im,"POOKALAM LOCKED",(x0,max(30,y0-10)),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,0),2)
        im=cv2.cvtColor(cv2.resize(im,(900,506)),cv2.COLOR_BGR2RGB); self.detect_photo=ImageTk.PhotoImage(Image.fromarray(im)); self.detect_preview.configure(image=self.detect_photo)

    def tick(self):
        now=time.perf_counter(); dt=min(.1,now-self.last); self.last=now
        if self.cap.isOpened():
            ok,self.frame=self.cap.read()
            if ok:
                self.sysvar.set("WEBCAM  ONLINE\nPROJECTOR  READY\nCALIBRATION  %s" % ("SAVED" if self.H is not None else "NOT SET"))
                self.update_preview(); self.update_detect_preview()
        if self.mode in ("interaction","run"): self.track_interaction()
        self.engine.update(dt,self.interaction)
        if self.mode=="run" and self.proj:self.proj.render(self.engine,self.interaction,self.image)
        self.root.after(25,self.tick)

    def open_projector(self):
        if not self.proj:self.proj=ProjectionWindow(self)

    def projector_test(self): self.open_projector(); self.proj.grid(); self.show_page("run")

    def calibrate(self):
        self.open_projector(); self.proj.targets(); self.mode="calibrate"; self.calibration_started=time.time(); messagebox.showinfo("Calibration","Keep all four projected targets visible to the webcam.\n\nThe software will detect them automatically and save the mapping when four stable points are found.")

    def calibration_step(self):
        if self.frame is None or not self.proj:return
        cs=detect_four_circles(self.frame)
        if len(cs)!=4:return
        cam=order4([(x,y) for x,y,r in cs]); m=.12; pw,ph=self.proj.w,self.proj.h
        dst=np.float32([[pw*m,ph*m],[pw*(1-m),ph*m],[pw*(1-m),ph*(1-m)],[pw*m,ph*(1-m)]])
        H,_=cv2.findHomography(cam,dst,0)
        if H is not None:
            self.H=H.astype(np.float32); self.state.update({"homography":self.H.tolist(),"projector_width":pw,"projector_height":ph}); save_state(self.state); self.mode="home"; self.proj.clear(); messagebox.showinfo("Calibration Complete","Camera → projector mapping saved to the installation profile.")

    def digital(self):
        p=filedialog.askopenfilename(title="Choose Pookalam image",filetypes=[("Images","*.png *.jpg *.jpeg *.webp *.bmp")])
        if not p:return
        self.image=cv2.imread(p); self.state.update({"source":"digital","image":p}); save_state(self.state); self.show_page("experience")

    def physical(self): self.image=None; self.state["source"]="physical"; save_state(self.state); self.show_page("detect")
    def hybrid(self): self.digital(); self.state["source"]="hybrid"; save_state(self.state)

    def detect(self):
        if self.frame is None:return
        hsv=cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV); mask=((hsv[:,:,1]>50)&(hsv[:,:,2]>45)).astype(np.uint8)*255
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((9,9),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); h,w=mask.shape; contours=[c for c in contours if .015*w*h<cv2.contourArea(c)<.92*w*h]
        if not contours: messagebox.showwarning("Pookalam not found","Try better lighting and keep the full Pookalam visible to the camera."); return
        c=max(contours,key=cv2.contourArea); M=cv2.moments(c); cx=M["m10"]/M["m00"]; cy=M["m01"]/M["m00"]; area=float(cv2.contourArea(c)); bbox=cv2.boundingRect(c)
        self.state["pookalam"]={"camera_center":[cx,cy],"area":area,"bbox":list(map(int,bbox))}; save_state(self.state); self.show_page("detect")

    def interaction_test(self): self.mode="interaction"; self.interaction=Interaction(); self.show_page("run")

    def track_interaction(self):
        if self.frame is None:return
        small=cv2.resize(self.frame,(640,360)); mask=self.bg.apply(small,learningRate=.002); mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((5,5),np.uint8)); mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8)); cs,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); c=max(cs,key=cv2.contourArea,default=None)
        if c is None or cv2.contourArea(c)<1500:self.interaction=Interaction();return
        M=cv2.moments(c); x=M["m10"]/M["m00"]/640; y=M["m01"]/M["m00"]/360
        if self.H is not None and self.proj:
            q=cv2.perspectiveTransform(np.float32([[[x*640,y*360]]]),self.H)[0,0]; x=float(q[0]/self.proj.w); y=float(q[1]/self.proj.h)
        strength=max(0,min(1,1-math.hypot(x-.5,y-.5)/.72)); self.interaction=Interaction(max(0,min(1,x)),max(0,min(1,y)),strength,True)

    def run_show(self):
        self.open_projector(); self.mode="run"; self.show_page("run")
        if self.proj and self.image is None:self.proj.grid()

    def stop_show(self):
        self.mode="home"; self.interaction=Interaction()
        if self.proj:self.proj.clear()

    def clear_calibration(self):
        self.H=None; self.state["homography"]=None; save_state(self.state); self.show_page("calibrate")

    def set_effect(self,name,value): self.engine.set_effect(name,value); self.state.setdefault("effects",{})[name]=value; save_state(self.state)
    def apply_saved_effects(self):
        for n,v in self.state.get("effects",{}).items():self.engine.set_effect(n,v)
    def set_all(self,value):
        self.engine.set_all(value); self.state["effects"]={n:value for n in self.engine.EFFECTS}; save_state(self.state)
    def reset_effects(self): self.set_all(True)
    def toggle_fullscreen(self): self.root.attributes("-fullscreen",not bool(self.root.attributes("-fullscreen")))
    def close(self):
        self.running=False
        try:self.stop_show(); self.cap.release()
        finally:self.root.destroy()


def launch():
    root=tk.Tk(); App(root); root.mainloop()

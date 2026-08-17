"""Automated realtime calibration workflow for Live Pookalam."""
from __future__ import annotations
import time
import cv2
import tkinter as tk
import numpy as np
from PIL import Image, ImageTk
from app.calibration.engine import LiveCalibrator
from app.ui.live_pookalam_app import LivePookalamApp, launch as _base_launch, save_state

BG="#06070a"; PANEL="#11141a"; PANEL2="#171c23"; BORDER="#2a313b"; TEXT="#f2f4f7"; MUTED="#98a2ae"; GOLD="#ffd45a"; GREEN="#72f59a"; RED="#ff7474"; BLUE="#75b8ff"
STABLE_FRAMES=8; TARGET_TIMEOUT=12.0; SUCCESS_HOLD=2.0

def _hex(bgr):
    b,g,r=bgr; return f"#{r:02x}{g:02x}{b:02x}"

def _project_active_target(self):
    if self.proj is None or not getattr(self,"calibrator",None): return
    self.proj.clear(); target=self.calibrator.active_target()
    if target is None: return
    x,y=target.projector_xy; radius=max(30,int(min(self.proj.w,self.proj.h)*.035)); colour=_hex(target.color_bgr)
    self.proj.canvas.create_oval(x-radius,y-radius,x+radius,y+radius,fill=colour,outline="white",width=5)
    self.proj.canvas.create_oval(x-radius*.45,y-radius*.45,x+radius*.45,y+radius*.45,fill="white",outline=colour,width=3)
    self.proj.canvas.create_text(self.proj.w/2,self.proj.h*.08,text=f"CALIBRATION • {target.index+1}/4 • {target.name}",fill="white",font=("Segoe UI",24,"bold"))
    self.proj.canvas.create_text(self.proj.w/2,self.proj.h*.92,text="AUTOMATIC CALIBRATION — DO NOT MOVE CAMERA OR PROJECTOR",fill="white",font=("Segoe UI",12,"bold"))

def _project_success(self,error):
    if self.proj is None:return
    self.proj.clear(); self.proj.canvas.create_text(self.proj.w/2,self.proj.h*.43,text="CALIBRATION COMPLETE",fill=GREEN,font=("Segoe UI",42,"bold")); self.proj.canvas.create_text(self.proj.w/2,self.proj.h*.52,text=f"MAP VERIFIED • ERROR {error:.1f}px",fill="white",font=("Segoe UI",20,"bold"))

def _page_calibrate(self: LivePookalamApp):
    self.title("Calibrate the installation.","Automatic four-point camera → projector calibration. Run it again whenever the projector or webcam moves.")
    status=tk.Frame(self.main,bg=PANEL,highlightthickness=1,highlightbackground=BORDER); status.pack(fill="x",pady=(0,10))
    self.calib_status=tk.StringVar(value="READY — PRESS CALIBRATE"); tk.Label(status,textvariable=self.calib_status,bg=PANEL,fg=GOLD,font=("Segoe UI",13,"bold")).pack(anchor="w",padx=16,pady=(12,2))
    self.calib_info=tk.StringVar(value="Webcam is live. The saved map is not changed until a complete sequence succeeds."); tk.Label(status,textvariable=self.calib_info,bg=PANEL,fg=MUTED,font=("Consolas",10)).pack(anchor="w",padx=16,pady=(0,12))
    actions=tk.Frame(self.main,bg=BG); actions.pack(fill="x",pady=(0,10)); self.action(actions,"CALIBRATE",self.calibrate,True); self.action(actions,"PROJECTOR GRID",self.projector_test); self.action(actions,"STOP CALIBRATION",self.stop_calibration); self.action(actions,"CLEAR SAVED MAP",self.clear_calibration)
    work=tk.Frame(self.main,bg=BG); work.pack(fill="both",expand=True)
    left=tk.Frame(work,bg="#030407",highlightthickness=1,highlightbackground=BORDER); left.pack(side="left",fill="both",expand=True,padx=(0,6)); tk.Label(left,text="LIVE WEBCAM FEED • REAL-TIME CALIBRATION INPUT",bg="#030407",fg=MUTED,font=("Segoe UI",9,"bold")).pack(anchor="nw",padx=10,pady=8); self.calib_preview=tk.Label(left,bg="#030407"); self.calib_preview.pack(expand=True,fill="both",padx=8,pady=(0,8))
    right=tk.Frame(work,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER,width=320); right.pack(side="right",fill="y",padx=(6,0)); right.pack_propagate(False); tk.Label(right,text="AUTOMATED SEQUENCE",bg=PANEL2,fg=GOLD,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=16,pady=(16,8))
    self.calib_target_labels=[]
    for i,name in enumerate(("TOP LEFT","TOP RIGHT","BOTTOM RIGHT","BOTTOM LEFT"),1):
        var=tk.StringVar(value=f"{i}  {name:<13} WAITING"); lbl=tk.Label(right,textvariable=var,bg=PANEL2,fg=RED,font=("Consolas",10,"bold"),anchor="w"); lbl.pack(fill="x",padx=16,pady=5); self.calib_target_labels.append((var,lbl))
    tk.Frame(right,bg=BORDER,height=1).pack(fill="x",padx=16,pady=14); self.calib_progress=tk.StringVar(value="0 / 4 targets locked"); tk.Label(right,textvariable=self.calib_progress,bg=PANEL2,fg=BLUE,font=("Consolas",12,"bold")).pack(anchor="w",padx=16); self.calib_map_var=tk.StringVar(value="SAVED MAP: "+("VALID" if self.H is not None else "NONE")); tk.Label(right,textvariable=self.calib_map_var,bg=PANEL2,fg=GREEN if self.H is not None else GOLD,font=("Consolas",11,"bold")).pack(anchor="w",padx=16,pady=(12,0))
    tk.Label(right,text="The projector shows one marker at a time.\nThe webcam must see the active colour.\n\n8 stable frames are required before each point is locked.\n\nIf a sequence fails, the previous map remains active.",bg=PANEL2,fg=MUTED,font=("Segoe UI",9),justify="left").pack(anchor="w",padx=16,pady=20)
    self._update_calibration_preview()

def _update_calibration_preview(self: LivePookalamApp):
    if not hasattr(self,"calib_preview") or self.frame is None:return
    frame=self.frame.copy(); observation=None
    if getattr(self,"calib_running",False) and getattr(self,"calibrator",None): observation=self.calibrator.detect_active(frame)
    if observation is not None:
        x,y=map(int,observation.camera_xy); cv2.circle(frame,(x,y),30,(0,255,0),3); cv2.circle(frame,(x,y),5,(0,255,0),-1); cv2.putText(frame,f"ACTIVE TARGET {observation.index+1} • STABLE {len(self.calibrator.candidate_history)}/{STABLE_FRAMES}",(20,38),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,0),2)
    elif getattr(self,"calib_running",False): cv2.putText(frame,"WAITING FOR ACTIVE CALIBRATION TARGET",(20,38),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,180,255),2)
    if getattr(self,"calibrator",None):
        for i,(var,lbl) in enumerate(self.calib_target_labels):
            if i in self.calibrator.observations: var.set(f"{i+1}  {self.calibrator.targets[i].name:<13} LOCKED"); lbl.configure(fg=GREEN)
            elif self.calibrator.active_index==i and self.calib_running: var.set(f"{i+1}  {self.calibrator.targets[i].name:<13} {len(self.calibrator.candidate_history)}/{STABLE_FRAMES}"); lbl.configure(fg=GOLD)
            else: var.set(f"{i+1}  {self.calibrator.targets[i].name:<13} WAITING"); lbl.configure(fg=RED)
        self.calib_progress.set(f"{len(self.calibrator.observations)} / 4 targets locked")
    rgb=cv2.cvtColor(cv2.resize(frame,(900,506)),cv2.COLOR_BGR2RGB); self.calib_photo=ImageTk.PhotoImage(Image.fromarray(rgb)); self.calib_preview.configure(image=self.calib_photo)

def _calibrate(self: LivePookalamApp):
    self.open_projector(); self.calibrator=LiveCalibrator(self.proj.w,self.proj.h); self.calibrator.begin(); self.calib_running=True; self.calib_started=time.monotonic(); self.calib_target_started=self.calib_started; self.mode="calibrate"; _project_active_target(self); self.calib_status.set("CALIBRATING — AUTOMATIC 1 → 2 → 3 → 4 SEQUENCE"); self.calib_info.set("Target 1 is active. Keep the projector and webcam still.")

def _stop_calibration(self: LivePookalamApp):
    self.calib_running=False
    if self.proj is not None:self.proj.clear()
    if hasattr(self,"calib_status"):self.calib_status.set("CALIBRATION STOPPED — SAVED MAP UNCHANGED")
    if hasattr(self,"calib_info"):self.calib_info.set("Press CALIBRATE to run the complete sequence again.")

def _process_calibration(self: LivePookalamApp):
    if not getattr(self,"calib_running",False) or self.frame is None:return
    cal=self.calibrator
    if cal is None or cal.finished():return
    target=cal.active_target()
    if target is None:return
    now=time.monotonic()
    if now-self.calib_target_started>TARGET_TIMEOUT:
        self.calib_running=False
        if self.proj is not None:self.proj.clear()
        self.calib_status.set("CALIBRATION FAILED — TARGET TIMEOUT"); self.calib_info.set(f"Could not lock {target.name}. The previous map is still active. Press CALIBRATE to retry."); return
    obs=cal.detect_active(self.frame)
    if obs is None:return
    if cal.accept_observation(obs,stable_frames=STABLE_FRAMES):
        if cal.finished():
            result=cal.build_result()
            if result is None or not np.isfinite(result.homography).all() or result.reprojection_error>20.0:
                self.calib_running=False
                if self.proj is not None:self.proj.clear()
                self.calib_status.set("CALIBRATION REJECTED — MAP QUALITY CHECK FAILED"); self.calib_info.set("The previous saved map remains active. Press CALIBRATE to retry."); return
            self.H=result.homography; self.state["homography"]=self.H.tolist(); self.state["projector_width"]=int(self.proj.w); self.state["projector_height"]=int(self.proj.h); self.state["calibration_error_px"]=float(result.reprojection_error); self.state["calibration_timestamp"]=time.time(); save_state(self.state); self.calib_running=False; self.calib_status.set("CALIBRATION COMPLETE — MAP SAVED"); self.calib_info.set(f"Camera → projector map accepted. Reprojection error: {result.reprojection_error:.1f}px"); self.calib_map_var.set("SAVED MAP: VALID"); _project_success(self,result.reprojection_error); self.calib_success_until=now+SUCCESS_HOLD
        else:
            self.calib_target_started=now; _project_active_target(self); self.calib_info.set(f"Target {cal.active_index+1} active. Locking automatically when stable.")

def _tick(self: LivePookalamApp):
    getattr(self,"_original_tick")()
    if self.mode=="calibrate":self._process_calibration(); self._update_calibration_preview()

def install():
    if getattr(LivePookalamApp,"_realtime_calibration_installed",False):return
    LivePookalamApp.page_calibrate=_page_calibrate; LivePookalamApp.calibrate=_calibrate; LivePookalamApp.stop_calibration=_stop_calibration; LivePookalamApp._update_calibration_preview=_update_calibration_preview; LivePookalamApp._original_tick=LivePookalamApp.tick; LivePookalamApp.tick=_tick; LivePookalamApp._realtime_calibration_installed=True

def launch(): install(); _base_launch()

__all__=["install","launch"]

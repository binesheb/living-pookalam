"""Production UI extension for the existing field console.

Keeps the approved field UI intact while adding the Analyse step and the full
pattern-aware Living Effects browser. The extension subclasses instead of
rewriting the stable calibration/service workflow.
"""
from __future__ import annotations

import os
import time
import tkinter as tk
import cv2
from PIL import Image, ImageTk

from app.ui.field_ui import FieldConsole, ProjectionWindow, DrawAdapter
from app.vision.pattern_analyzer import analyze
from app.visuals.effect_library import CATEGORIES, PRESETS, effects_by_category

BG="#090711"; PANEL2="#171526"; PANEL3="#201b32"; BORDER="#2b2540"; TEXT="#f4f1fa"; MUTED="#9c95aa"; PURPLE="#8b35ff"; GREEN="#32e875"; GOLD="#ffd24a"; CYAN="#2fd8ff"


class PatternProjectionWindow(ProjectionWindow):
    def _digital_image(self):
        if self.app.state.get("source") != "digital": return None
        path=self.app.state.get("image","")
        if not path or not os.path.exists(path): return None
        return cv2.imread(path)

    def render(self, interaction=None, contour=None, pattern=None, image=None):
        self.clear()
        digital=self._digital_image()
        if digital is not None:
            rgb=cv2.cvtColor(digital,cv2.COLOR_BGR2RGB)
            im=Image.fromarray(rgb); im.thumbnail((int(self.w*.82),int(self.h*.82)),Image.Resampling.LANCZOS)
            self.base_photo=ImageTk.PhotoImage(im)
            self.canvas.create_image(self.w/2,self.h/2,image=self.base_photo)
            old_base=self.app.engine.effects.get("base",False); self.app.engine.effects["base"]=False
            try:self.app.engine.render(DrawAdapter(self.canvas),self.w,self.h,interaction=interaction,pattern=pattern)
            finally:self.app.engine.effects["base"]=old_base
        else:
            # Physical/hybrid: don't invent a second Pookalam over the real flowers.
            old_base=self.app.engine.effects.get("base",False); self.app.engine.effects["base"]=self.app.state.get("source")=="generated"
            try:self.app.engine.render(DrawAdapter(self.canvas),self.w,self.h,interaction=interaction,pattern=pattern)
            finally:self.app.engine.effects["base"]=old_base
        if self.app.dev_mode and contour is not None:
            pts=contour.reshape(-1,2).astype("float32")
            if self.app.H is not None:mapped=cv2.perspectiveTransform(pts.reshape(-1,1,2),self.app.H).reshape(-1,2)
            else:
                ch,cw=self.app.frame.shape[:2]; mapped=pts.copy(); mapped[:,0]=mapped[:,0]/max(1,cw)*self.w; mapped[:,1]=mapped[:,1]/max(1,ch)*self.h
            mapped[:,0]*=self.w/max(1,self.app.state.get("projector_width",self.w)); mapped[:,1]*=self.h/max(1,self.app.state.get("projector_height",self.h))
            poly=[(float(x),float(y)) for x,y in mapped]
            if len(poly)>=2:self.canvas.create_line(*[v for p in poly for v in p],fill=PURPLE,width=5,smooth=True)
            self.canvas.create_text(36,32,text="DEV • REAL POOKALAM EDGE",anchor="nw",fill=PURPLE,font=("Segoe UI",18,"bold"))


class FieldExperienceConsole(FieldConsole):
    NAV=[("⌂","HOME","home"),("▣","SOURCE","source"),("◎","CALIBRATE","calibrate"),("◉","ANALYSE","analyze"),("◉","DETECT","detect"),("✦","EFFECTS","experience"),("▶","RUN SHOW","run")]

    def __init__(self, root):
        self.pattern=None; self._last_analysis=0.0
        super().__init__(root)

    def open_projector(self):
        if self.proj is None or not self.proj.win.winfo_exists(): self.proj=PatternProjectionWindow(self)
        self.proj.place()

    def _source_frame(self):
        if self.state.get("source")=="digital" and self.state.get("image"):
            try:
                image=cv2.imread(self.state["image"])
                if image is not None:return image
            except Exception:pass
        return self.frame

    def analyse_pattern(self, force=False):
        now=time.monotonic()
        if not force and now-self._last_analysis<0.35:return
        source=self._source_frame()
        if source is None:return
        try:
            self.pattern=analyze(source); self._last_analysis=now
            self.contour=self.pattern.contour; self.confidence=self.pattern.confidence
        except Exception:self.pattern=None

    def tick(self):
        super().tick(); self.analyse_pattern()
        if self.showing and self.proj is not None and self.frame is not None:
            try:self.proj.render(self.interaction,self.contour,self.pattern)
            except Exception:pass
        if self.page=="analyze" and hasattr(self,"analysis_preview"):self._update_analysis_preview()

    def page_analyze(self):
        self.page_title("Analyse", "Understand the real Pookalam before assigning visual effects."); self.analyse_pattern(force=True); p=self.pattern
        row=tk.Frame(self.main,bg=BG); row.pack(fill="x")
        cards=[("CONFIDENCE",f"{p.confidence:.0%}" if p else "—",GREEN),("RINGS",str(len(p.rings)) if p else "—",CYAN),("SYMMETRY",f"{p.symmetry_order}-fold" if p else "—",GOLD),("COLOURS",str(len(p.dominant_colours)) if p else "—",PURPLE)]
        for title,value,color in cards:
            f=tk.Frame(row,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); f.pack(side="left",fill="both",expand=True,padx=4); tk.Label(f,text=title,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=(10,2)); tk.Label(f,text=value,bg=PANEL2,fg=color,font=("Segoe UI",15,"bold")).pack(anchor="w",padx=12,pady=(0,10))
        bar=tk.Frame(self.main,bg=BG); bar.pack(fill="x",pady=8); self.button(bar,"ANALYSE NOW",lambda:self.analyse_pattern(True),True).pack(side="left",padx=4); self.button(bar,"SHOW REAL EDGE",self.show_edge).pack(side="left",padx=4)
        panel=tk.Frame(self.main,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); panel.pack(fill="both",expand=True); self.analysis_preview=tk.Label(panel,bg="#020204"); self.analysis_preview.pack(fill="both",expand=True,padx=8,pady=8); self._update_analysis_preview()

    def _update_analysis_preview(self):
        if not hasattr(self,"analysis_preview") or self.frame is None:return
        frame=self.frame.copy(); p=self.pattern
        if p is not None and p.contour is not None:
            cv2.drawContours(frame,[p.contour],-1,(210,110,255),4); cx,cy=map(int,p.centre); cv2.circle(frame,(cx,cy),8,(0,255,255),-1); cv2.putText(frame,f"EDGE  CONF {p.confidence:.0%}  {p.symmetry_order}-FOLD",(20,35),cv2.FONT_HERSHEY_SIMPLEX,.75,(210,110,255),2)
        rgb=cv2.cvtColor(cv2.resize(frame,(900,506)),cv2.COLOR_BGR2RGB); self.analysis_photo=ImageTk.PhotoImage(Image.fromarray(rgb)); self.analysis_preview.configure(image=self.analysis_photo)

    def page_experience(self):
        self.page_title("Living Effects", "A real-time effect editor driven by Pookalam edges, rings, colour regions and interaction.")
        body=tk.Frame(self.main,bg=BG); body.pack(fill="both",expand=True)
        left=tk.Frame(body,bg=PANEL2,width=320,highlightthickness=1,highlightbackground=BORDER); left.pack(side="left",fill="y",padx=(0,6)); left.pack_propagate(False); tk.Label(left,text="EFFECT LIBRARY",bg=PANEL2,fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=(14,8))
        preset=tk.Frame(left,bg=PANEL2); preset.pack(fill="x",padx=10,pady=(0,8))
        for name in PRESETS:tk.Button(preset,text=name.replace("_"," "),command=lambda n=name:self.apply_preset(n),bg=PANEL3,fg=GOLD,relief="flat",font=("Segoe UI",8,"bold")).pack(fill="x",pady=2)
        scroll=tk.Canvas(left,bg=PANEL2,highlightthickness=0); scroll.pack(fill="both",expand=True,padx=8); inner=tk.Frame(scroll,bg=PANEL2); scroll.create_window((0,0),window=inner,anchor="nw"); self.effect_vars={}
        for category in CATEGORIES:
            tk.Label(inner,text=category,bg=PANEL2,fg=PURPLE,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=6,pady=(10,4))
            for spec in effects_by_category()[category]:
                var=tk.BooleanVar(value=bool(self.engine.effects.get(spec.id,False))); self.effect_vars[spec.id]=var; tk.Checkbutton(inner,text=spec.name,variable=var,command=lambda eid=spec.id,v=var:self.engine.set_effect(eid,v.get()),bg=PANEL2,fg=TEXT,selectcolor=PANEL3,activebackground=PANEL2,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=6,pady=1)
        inner.update_idletasks(); scroll.configure(scrollregion=scroll.bbox("all"))
        right=tk.Frame(body,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER); right.pack(side="left",fill="both",expand=True); tk.Label(right,text="LIVE EFFECT PREVIEW",bg=PANEL2,fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=10); self.effect_canvas=tk.Canvas(right,bg="#020204",highlightthickness=0); self.effect_canvas.pack(fill="both",expand=True,padx=10,pady=8)
        controls=tk.Frame(right,bg=PANEL2); controls.pack(fill="x",padx=14,pady=8); self.intensity=tk.DoubleVar(value=self.engine.intensity*100); self.speed=tk.DoubleVar(value=self.engine.speed*100)
        for label,var,attr in (("INTENSITY",self.intensity,"intensity"),("SPEED",self.speed,"speed")):
            tk.Label(controls,text=label,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(side="left",padx=(0,4)); tk.Scale(controls,from_=0,to=150,variable=var,orient="horizontal",command=lambda v,a=attr:setattr(self.engine,a,float(v)/100),bg=PANEL2,fg=TEXT,troughcolor=PANEL3,highlightthickness=0,length=170).pack(side="left",padx=(0,16))
        tk.Button(controls,text="ALL OFF",command=lambda:self.set_all(False),bg=PANEL3,fg=TEXT,relief="flat").pack(side="right",padx=3); tk.Button(controls,text="ALL ON",command=lambda:self.set_all(True),bg=PANEL3,fg=GOLD,relief="flat").pack(side="right",padx=3)

    def apply_preset(self,name):
        self.engine.apply_preset(PRESETS[name]);
        for eid,var in self.effect_vars.items():var.set(bool(self.engine.effects.get(eid,False)))

    def set_all(self,enabled):
        self.engine.set_all(enabled)
        for eid,var in getattr(self,"effect_vars",{}).items():var.set(bool(enabled))


def launch():
    import tkinter as tk
    root=tk.Tk(); FieldExperienceConsole(root); root.mainloop()

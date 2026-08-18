"""Field UI integration for pattern analysis and the Living Effects editor."""
from __future__ import annotations

import time
import tkinter as tk
from dataclasses import replace

import cv2
import numpy as np
from PIL import Image, ImageTk

from app.rendering.compositor import build_projection_mask, map_contour_to_projector, prepare_digital_layer
from app.ui.live_pookalam_app import DrawAdapter, LivePookalamApp, ProjectionWindow
from app.vision.pattern_analyzer import analyze
from app.visuals.effect_library import CATEGORIES, PRESETS, effects_by_category
from app.visuals.masking import MaskedDrawAdapter

BG="#06070a"; PANEL="#11141a"; PANEL2="#171c23"; PANEL3="#20252d"; BORDER="#2a313b"; TEXT="#f2f4f7"; MUTED="#98a2ae"; GOLD="#ffd45a"; GREEN="#72f59a"; PURPLE="#bd86ff"; BLUE="#75b8ff"


def _fit_values(src_w, src_h, out_w, out_h, fraction=.78):
    scale=min(out_w/max(1,src_w),out_h/max(1,src_h))*fraction; nw=max(1,int(round(src_w*scale))); nh=max(1,int(round(src_h*scale)))
    return scale,(out_w-nw)/2,(out_h-nh)/2,nw,nh


def _projector_geometry(self, pattern):
    if pattern is None or pattern.contour is None or self.proj is None:return None,None
    source=self.state.get("source"); H=self.H if source=="physical" else None
    mapped=map_contour_to_projector(pattern.contour,(pattern.height,pattern.width),(self.proj.w,self.proj.h),H)
    if mapped is None:return None,None
    mask=build_projection_mask(mapped,(self.proj.w,self.proj.h),edge_margin=8)
    if mask is None:return None,None
    centre_pt=np.asarray(pattern.centre,dtype=np.float32).reshape(1,1,2)
    if H is not None: centre=cv2.perspectiveTransform(centre_pt,np.asarray(H,dtype=np.float32)).reshape(2)
    else:
        scale,ox,oy,_,_=_fit_values(pattern.width,pattern.height,self.proj.w,self.proj.h); centre=np.array([pattern.centre[0]*scale+ox,pattern.centre[1]*scale+oy])
    radius=float(np.max(np.linalg.norm(mapped-centre.reshape(1,2),axis=1)))
    projected=replace(pattern,width=self.proj.w,height=self.proj.h,centre=(float(centre[0]),float(centre[1])),radius=radius,contour=mapped)
    return projected,mask


def _projector_render(self,engine,interaction,image=None,debug_contour=None,debug_mask=None,pattern=None):
    self.clear(); source=self.app.state.get("source","generated"); projected_pattern,mask=_projector_geometry(self.app,pattern)
    engine.set_effect("base",source=="generated")
    if source=="digital" and image is not None and pattern is not None and pattern.contour is not None:
        try:
            prepared=prepare_digital_layer(image,pattern.contour,(self.w,self.h))
            if prepared is not None:
                layer,centre=prepared; self.photo=ImageTk.PhotoImage(layer); self.canvas.create_image(centre[0],centre[1],image=self.photo)
        except Exception:pass
    if source=="generated":
        engine.render(DrawAdapter(self.canvas),self.w,self.h,interaction=interaction,pattern=projected_pattern)
    elif mask is not None:
        engine.render(MaskedDrawAdapter(DrawAdapter(self.canvas),mask),self.w,self.h,interaction=interaction,pattern=projected_pattern)
    if self.app.dev_mode and debug_contour is not None:
        mapped=map_contour_to_projector(debug_contour,self.app.frame.shape if self.app.frame is not None else (720,1280),(self.w,self.h),self.app.H if source=="physical" else None)
        if mapped is not None and len(mapped)>=2:
            poly=[(float(x),float(y)) for x,y in mapped]; self.canvas.create_line(*[v for p in poly for v in p],fill=PURPLE,width=5,smooth=True)
        self.canvas.create_text(40,40,text="DEV • REAL POOKALAM EDGE",anchor="nw",fill=PURPLE,font=("Segoe UI",18,"bold")); self.canvas.create_text(40,72,text="MASKED PROJECTOR SPACE",anchor="nw",fill=TEXT,font=("Segoe UI",11))


def _page_analyze(self:LivePookalamApp):
    self.title("Analyse","Understand the Pookalam before assigning effects. Analysis is live and deterministic.")
    row=tk.Frame(self.main,bg=BG);row.pack(fill="x",pady=(0,10));p=getattr(self,"pattern",None)
    for title,value,colour in [("CONFIDENCE",f"{p.confidence*100:.0f}%" if p else "—",GREEN),("RINGS",str(len(p.rings)) if p else "—",BLUE),("SYMMETRY",f"{p.symmetry_order}-fold" if p else "—",GOLD),("COLOURS",str(len(p.dominant_colours)) if p else "—",PURPLE)]:
        f=tk.Frame(row,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER);f.pack(side="left",fill="both",expand=True,padx=4);tk.Label(f,text=title,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=(10,2));tk.Label(f,text=value,bg=PANEL2,fg=colour,font=("Consolas",15,"bold")).pack(anchor="w",padx=12,pady=(0,10))
    bar=tk.Frame(self.main,bg=BG);bar.pack(fill="x",pady=4);self.action(bar,"ANALYSE NOW",lambda:self._analyse_pattern(force=True),True);self.action(bar,"SHOW REAL EDGE",self.show_edge)
    body=tk.Frame(self.main,bg=BG);body.pack(fill="both",expand=True);preview=tk.Frame(body,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER);preview.pack(side="left",fill="both",expand=True,padx=(0,6));self.analysis_preview=tk.Label(preview,bg="#020204");self.analysis_preview.pack(fill="both",expand=True,padx=8,pady=8)
    info=tk.Frame(body,bg=PANEL2,width=280,highlightthickness=1,highlightbackground=BORDER);info.pack(side="right",fill="y");info.pack_propagate(False);tk.Label(info,text="DETECTED STRUCTURE",bg=PANEL2,fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=14);text="No pattern yet." if p is None else f"Centre\n  {p.centre[0]:.0f}, {p.centre[1]:.0f}\n\nRadius\n  {p.radius:.0f}px\n\nBoundary\n  {len(p.contour) if p.contour is not None else 0} points\n\nConfidence\n  {p.confidence:.2%}";tk.Label(info,text=text,bg=PANEL2,fg=MUTED,justify="left",font=("Consolas",9)).pack(anchor="w",padx=14)


def _page_experience(self:LivePookalamApp):
    self.title("Living Effects","Pattern-aware effects inspired by modern video editors, driven by the actual Pookalam geometry.")
    body=tk.Frame(self.main,bg=BG);body.pack(fill="both",expand=True);left=tk.Frame(body,bg=PANEL2,width=300,highlightthickness=1,highlightbackground=BORDER);left.pack(side="left",fill="y",padx=(0,6));left.pack_propagate(False);tk.Label(left,text="EFFECT LIBRARY",bg=PANEL2,fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=(14,8));preset_bar=tk.Frame(left,bg=PANEL2);preset_bar.pack(fill="x",padx=10,pady=(0,8))
    for name in PRESETS:tk.Button(preset_bar,text=name.replace("_"," "),command=lambda n=name:self._apply_effect_preset(n),bg=PANEL3,fg=GOLD,relief="flat",font=("Segoe UI",8,"bold")).pack(fill="x",pady=2)
    canvas=tk.Canvas(left,bg=PANEL2,highlightthickness=0);canvas.pack(fill="both",expand=True,padx=8);inner=tk.Frame(canvas,bg=PANEL2);canvas.create_window((0,0),window=inner,anchor="nw");self.effect_vars={}
    for category in CATEGORIES:
        tk.Label(inner,text=category,bg=PANEL2,fg=PURPLE,font=("Segoe UI",8,"bold")).pack(anchor="w",padx=6,pady=(10,4))
        for spec in effects_by_category()[category]:
            var=tk.BooleanVar(value=bool(self.engine.effects.get(spec.id,False)));self.effect_vars[spec.id]=var;tk.Checkbutton(inner,text=spec.name,variable=var,command=lambda eid=spec.id,v=var:self.engine.set_effect(eid,v.get()),bg=PANEL2,fg=TEXT,selectcolor=PANEL3,activebackground=PANEL2,activeforeground=TEXT,font=("Segoe UI",9)).pack(anchor="w",padx=6,pady=1)
    inner.update_idletasks();canvas.configure(scrollregion=canvas.bbox("all"));right=tk.Frame(body,bg=PANEL2,highlightthickness=1,highlightbackground=BORDER);right.pack(side="left",fill="both",expand=True);tk.Label(right,text="LIVE EFFECT PREVIEW",bg=PANEL2,fg=TEXT,font=("Segoe UI",11,"bold")).pack(anchor="w",padx=14,pady=10);self.effect_canvas=tk.Canvas(right,bg="#020204",highlightthickness=0);self.effect_canvas.pack(fill="both",expand=True,padx=10,pady=8)
    controls=tk.Frame(right,bg=PANEL2);controls.pack(fill="x",padx=14,pady=8);self.effect_intensity=tk.DoubleVar(value=self.engine.intensity*100);self.effect_speed=tk.DoubleVar(value=self.engine.speed*100)
    for label,var,callback in [("INTENSITY",self.effect_intensity,lambda v:setattr(self.engine,"intensity",float(v)/100)),("SPEED",self.effect_speed,lambda v:setattr(self.engine,"speed",float(v)/100))]:tk.Label(controls,text=label,bg=PANEL2,fg=MUTED,font=("Segoe UI",8,"bold")).pack(side="left",padx=(0,5));tk.Scale(controls,from_=0,to=150,variable=var,orient="horizontal",command=callback,bg=PANEL2,fg=TEXT,troughcolor=PANEL3,highlightthickness=0,length=180).pack(side="left",padx=(0,18))
    tk.Button(controls,text="ALL OFF",command=lambda:self._set_all_effects(False),bg=PANEL3,fg=TEXT,relief="flat").pack(side="right",padx=3);tk.Button(controls,text="ALL ON",command=lambda:self._set_all_effects(True),bg=PANEL3,fg=GOLD,relief="flat").pack(side="right",padx=3)


def _analyse_pattern(self,force=False):
    now=time.monotonic()
    if not force and now-getattr(self,"_last_pattern_analysis",0)<0.35:return
    source=self.image if self.state.get("source")=="digital" and self.image is not None else self.frame
    if source is None:return
    try:self.pattern=analyze(source);self._last_pattern_analysis=now;self.debug_contour=self.pattern.contour;self.debug_mask=self.pattern.mask;self._update_analysis_preview()
    except Exception:self.pattern=None


def _update_analysis_preview(self):
    if not hasattr(self,"analysis_preview"):return
    source=self.image if self.state.get("source")=="digital" and self.image is not None else self.frame
    if source is None:return
    frame=source.copy()
    if getattr(self,"pattern",None) is not None and self.pattern.contour is not None:
        cv2.drawContours(frame,[self.pattern.contour],-1,(220,130,255),4);cx,cy=map(int,self.pattern.centre);cv2.circle(frame,(cx,cy),8,(0,255,255),-1);cv2.putText(frame,f"CONF {self.pattern.confidence:.0%}  {self.pattern.symmetry_order}-FOLD",(20,35),cv2.FONT_HERSHEY_SIMPLEX,.75,(220,130,255),2)
    rgb=cv2.cvtColor(cv2.resize(frame,(900,506)),cv2.COLOR_BGR2RGB);self.analysis_photo=ImageTk.PhotoImage(Image.fromarray(rgb));self.analysis_preview.configure(image=self.analysis_photo)


def _update_effect_preview(self):
    if not hasattr(self,"effect_canvas") or not self.effect_canvas.winfo_exists():return
    self.effect_canvas.delete("all");w=max(320,self.effect_canvas.winfo_width());h=max(240,self.effect_canvas.winfo_height());p=getattr(self,"pattern",None)
    if p is None:return
    mapped=map_contour_to_projector(p.contour,(p.height,p.width),(w,h),None);mask=build_projection_mask(mapped,(w,h),edge_margin=8)
    if mask is None:return
    projected=replace(p,width=w,height=h,contour=mapped,centre=(w/2,h/2),radius=min(w,h)*.34);self.engine.set_effect("base",False);self.engine.update(1/30,self.interaction);self.engine.render(MaskedDrawAdapter(DrawAdapter(self.effect_canvas),mask),w,h,interaction=self.interaction,pattern=projected)


def _apply_effect_preset(self,name):
    self.engine.apply_preset(PRESETS[name]);self.engine.set_effect("base",False)
    for eid,var in getattr(self,"effect_vars",{}).items():var.set(bool(self.engine.effects.get(eid,False)))


def _set_all_effects(self,enabled):
    self.engine.set_all(enabled);self.engine.set_effect("base",False)
    for eid,var in getattr(self,"effect_vars",{}).items():var.set(bool(self.engine.effects.get(eid,False)))


def _experience_tick(self):
    _orig=getattr(LivePookalamApp,"_experience_original_tick",None)
    if _orig is not None:_orig(self)
    self._analyse_pattern();self._update_effect_preview()
    if getattr(self,"showing",False) and getattr(self,"proj",None) is not None:
        try:self.proj.render(self.engine,self.interaction,image=self.image,debug_contour=self.debug_contour,debug_mask=self.debug_mask,pattern=getattr(self,"pattern",None))
        except Exception:pass


def install():
    if getattr(LivePookalamApp,"_experience_installed",False):return
    LivePookalamApp._experience_original_tick=LivePookalamApp.tick;LivePookalamApp.tick=_experience_tick;LivePookalamApp.page_analyze=_page_analyze;LivePookalamApp.page_experience=_page_experience;LivePookalamApp._analyse_pattern=_analyse_pattern;LivePookalamApp._update_analysis_preview=_update_analysis_preview;LivePookalamApp._update_effect_preview=_update_effect_preview;LivePookalamApp._apply_effect_preset=_apply_effect_preset;LivePookalamApp._set_all_effects=_set_all_effects;LivePookalamApp.NAV=[("HOME","home"),("SOURCE","source"),("CALIBRATE","calibrate"),("ANALYSE","analyze"),("DETECT","detect"),("EFFECTS","experience"),("RUN SHOW","run")];ProjectionWindow.render=_projector_render;LivePookalamApp._experience_installed=True

__all__=["install"]

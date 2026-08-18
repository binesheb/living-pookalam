"""Field UI integration for pattern analysis and the Living Effects editor."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk

from app.ui.live_pookalam_app import DrawAdapter, LivePookalamApp, ProjectionWindow
from app.vision.pattern_analyzer import analyze
from app.visuals.effect_library import CATEGORIES, EFFECTS, PRESETS, effects_by_category

BG = "#06070a"
PANEL = "#11141a"
PANEL2 = "#171c23"
PANEL3 = "#20252d"
BORDER = "#2a313b"
TEXT = "#f2f4f7"
MUTED = "#98a2ae"
GOLD = "#ffd45a"
GREEN = "#72f59a"
PURPLE = "#bd86ff"
BLUE = "#75b8ff"


def _projector_render(self, engine, interaction, image=None, debug_contour=None, debug_mask=None, pattern=None):
    self.clear()
    engine.render(DrawAdapter(self.canvas), self.w, self.h, interaction=interaction, pattern=pattern)
    # A digital source is a BASE LAYER. Effects are rendered after it in the
    # next compositor pass; keep the image small enough for Tkinter preview.
    if self.app.state.get("source") == "digital" and image is not None:
        try:
            im = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            im.thumbnail((int(self.w * .78), int(self.h * .78)), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(im)
            self.canvas.create_image(self.w / 2, self.h / 2, image=self.photo)
        except Exception:
            pass
    if self.app.dev_mode and debug_contour is not None:
        pts = debug_contour.reshape(-1, 2).astype("float32")
        if self.app.H is not None:
            mapped = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), self.app.H).reshape(-1, 2)
            mapped[:, 0] *= self.w / max(1, self.app.state.get("projector_width", 1920))
            mapped[:, 1] *= self.h / max(1, self.app.state.get("projector_height", 1080))
        else:
            ch, cw = self.app.frame.shape[:2] if self.app.frame is not None else (720, 1280)
            mapped = pts.copy(); mapped[:, 0] = mapped[:, 0] / cw * self.w; mapped[:, 1] = mapped[:, 1] / ch * self.h
        poly = [(float(x), float(y)) for x, y in mapped]
        if len(poly) >= 2:
            self.canvas.create_line(*[v for p in poly for v in p], fill=PURPLE, width=5, smooth=True)
        self.canvas.create_text(40, 40, text="DEV • REAL POOKALAM EDGE", anchor="nw", fill=PURPLE, font=("Segoe UI", 18, "bold"))


def _page_analyze(self: LivePookalamApp):
    self.title("Analyse", "Understand the Pookalam before assigning effects. Analysis is live and deterministic.")
    row = tk.Frame(self.main, bg=BG); row.pack(fill="x", pady=(0, 10))
    for title, value, colour in [
        ("CONFIDENCE", f"{getattr(self, 'pattern', None).confidence * 100:.0f}%" if getattr(self, 'pattern', None) else "—", GREEN),
        ("RINGS", str(len(getattr(self, 'pattern', None).rings)) if getattr(self, 'pattern', None) else "—", BLUE),
        ("SYMMETRY", f"{getattr(self, 'pattern', None).symmetry_order}-fold" if getattr(self, 'pattern', None) else "—", GOLD),
        ("COLOURS", str(len(getattr(self, 'pattern', None).dominant_colours)) if getattr(self, 'pattern', None) else "—", PURPLE),
    ]:
        f = tk.Frame(row, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); f.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(f, text=title, bg=PANEL2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(f, text=value, bg=PANEL2, fg=colour, font=("Consolas", 15, "bold")).pack(anchor="w", padx=12, pady=(0, 10))
    bar = tk.Frame(self.main, bg=BG); bar.pack(fill="x", pady=4)
    self.action(bar, "ANALYSE NOW", lambda: self._analyse_pattern(force=True), True)
    self.action(bar, "SHOW REAL EDGE", self.show_edge)
    body = tk.Frame(self.main, bg=BG); body.pack(fill="both", expand=True)
    preview = tk.Frame(body, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); preview.pack(side="left", fill="both", expand=True, padx=(0, 6))
    self.analysis_preview = tk.Label(preview, bg="#020204"); self.analysis_preview.pack(fill="both", expand=True, padx=8, pady=8)
    info = tk.Frame(body, bg=PANEL2, width=280, highlightthickness=1, highlightbackground=BORDER); info.pack(side="right", fill="y"); info.pack_propagate(False)
    tk.Label(info, text="DETECTED STRUCTURE", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=14)
    p = getattr(self, "pattern", None)
    text = "No pattern yet." if p is None else (
        f"Centre\n  {p.centre[0]:.0f}, {p.centre[1]:.0f}\n\nRadius\n  {p.radius:.0f}px\n\nBoundary\n  {len(p.contour) if p.contour is not None else 0} points\n\nConfidence\n  {p.confidence:.2%}"
    )
    tk.Label(info, text=text, bg=PANEL2, fg=MUTED, justify="left", font=("Consolas", 9)).pack(anchor="w", padx=14)


def _page_experience(self: LivePookalamApp):
    self.title("Living Effects", "Pattern-aware effects inspired by modern video editors, but driven by real Pookalam geometry.")
    body = tk.Frame(self.main, bg=BG); body.pack(fill="both", expand=True)
    left = tk.Frame(body, bg=PANEL2, width=300, highlightthickness=1, highlightbackground=BORDER); left.pack(side="left", fill="y", padx=(0, 6)); left.pack_propagate(False)
    tk.Label(left, text="EFFECT LIBRARY", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
    preset_bar = tk.Frame(left, bg=PANEL2); preset_bar.pack(fill="x", padx=10, pady=(0, 8))
    for name in PRESETS:
        tk.Button(preset_bar, text=name.replace("_", " "), command=lambda n=name: self._apply_effect_preset(n), bg=PANEL3, fg=GOLD, relief="flat", font=("Segoe UI", 8, "bold")).pack(fill="x", pady=2)
    canvas = tk.Canvas(left, bg=PANEL2, highlightthickness=0); canvas.pack(fill="both", expand=True, padx=8)
    inner = tk.Frame(canvas, bg=PANEL2); canvas.create_window((0, 0), window=inner, anchor="nw")
    self.effect_vars = {}
    for category in CATEGORIES:
        tk.Label(inner, text=category, bg=PANEL2, fg=PURPLE, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=6, pady=(10, 4))
        for spec in effects_by_category()[category]:
            var = tk.BooleanVar(value=bool(self.engine.effects.get(spec.id, False)))
            self.effect_vars[spec.id] = var
            tk.Checkbutton(inner, text=spec.name, variable=var, command=lambda eid=spec.id, v=var: self.engine.set_effect(eid, v.get()), bg=PANEL2, fg=TEXT, selectcolor=PANEL3, activebackground=PANEL2, activeforeground=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=6, pady=1)
    inner.update_idletasks(); canvas.configure(scrollregion=canvas.bbox("all"))

    right = tk.Frame(body, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); right.pack(side="left", fill="both", expand=True)
    tk.Label(right, text="LIVE EFFECT PREVIEW", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=10)
    self.effect_canvas = tk.Canvas(right, bg="#020204", highlightthickness=0); self.effect_canvas.pack(fill="both", expand=True, padx=10, pady=8)
    controls = tk.Frame(right, bg=PANEL2); controls.pack(fill="x", padx=14, pady=8)
    self.effect_intensity = tk.DoubleVar(value=self.engine.intensity * 100)
    self.effect_speed = tk.DoubleVar(value=self.engine.speed * 100)
    for label, var, callback in [("INTENSITY", self.effect_intensity, lambda v: setattr(self.engine, "intensity", float(v)/100)), ("SPEED", self.effect_speed, lambda v: setattr(self.engine, "speed", float(v)/100))]:
        tk.Label(controls, text=label, bg=PANEL2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 5)); tk.Scale(controls, from_=0, to=150, variable=var, orient="horizontal", command=callback, bg=PANEL2, fg=TEXT, troughcolor=PANEL3, highlightthickness=0, length=180).pack(side="left", padx=(0, 18))
    tk.Button(controls, text="ALL OFF", command=lambda: self._set_all_effects(False), bg=PANEL3, fg=TEXT, relief="flat").pack(side="right", padx=3)
    tk.Button(controls, text="ALL ON", command=lambda: self._set_all_effects(True), bg=PANEL3, fg=GOLD, relief="flat").pack(side="right", padx=3)


def _analyse_pattern(self, force=False):
    now = time.monotonic()
    if not force and now - getattr(self, "_last_pattern_analysis", 0) < 0.35:
        return
    source = self.image if self.state.get("source") == "digital" and self.image is not None else self.frame
    if source is None: return
    try:
        self.pattern = analyze(source)
        self._last_pattern_analysis = now
        self.debug_contour = self.pattern.contour
        self.debug_mask = self.pattern.mask
        self._update_analysis_preview()
    except Exception:
        self.pattern = None


def _update_analysis_preview(self):
    if not hasattr(self, "analysis_preview") or self.frame is None: return
    frame = self.frame.copy()
    if getattr(self, "pattern", None) is not None and self.pattern.contour is not None:
        cv2.drawContours(frame, [self.pattern.contour], -1, (220, 130, 255), 4)
        cx, cy = map(int, self.pattern.centre); cv2.circle(frame, (cx, cy), 8, (0, 255, 255), -1)
        cv2.putText(frame, f"CONF {self.pattern.confidence:.0%}  {self.pattern.symmetry_order}-FOLD", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, .75, (220, 130, 255), 2)
    rgb = cv2.cvtColor(cv2.resize(frame, (900, 506)), cv2.COLOR_BGR2RGB)
    self.analysis_photo = ImageTk.PhotoImage(Image.fromarray(rgb)); self.analysis_preview.configure(image=self.analysis_photo)


def _apply_effect_preset(self, name):
    self.engine.apply_preset(PRESETS[name])
    for eid, var in getattr(self, "effect_vars", {}).items(): var.set(bool(self.engine.effects.get(eid, False)))


def _set_all_effects(self, enabled):
    self.engine.set_all(enabled)
    for eid, var in getattr(self, "effect_vars", {}).items(): var.set(bool(enabled))


def _experience_tick(self):
    _orig = getattr(LivePookalamApp, "_experience_original_tick", None)
    if _orig is not None:
        _orig(self)
    self._analyse_pattern()
    if getattr(self, "showing", False) and getattr(self, "proj", None) is not None:
        try:
            self.proj.render(self.engine, self.interaction, image=self.image, debug_contour=self.debug_contour, debug_mask=self.debug_mask, pattern=getattr(self, "pattern", None))
        except Exception:
            pass


def install() -> None:
    if getattr(LivePookalamApp, "_experience_installed", False): return
    # Preserve the calibration_field tick wrapper if present.
    LivePookalamApp._experience_original_tick = LivePookalamApp.tick
    LivePookalamApp.tick = _experience_tick
    LivePookalamApp.page_analyze = _page_analyze
    LivePookalamApp.page_experience = _page_experience
    LivePookalamApp._analyse_pattern = _analyse_pattern
    LivePookalamApp._update_analysis_preview = _update_analysis_preview
    LivePookalamApp._apply_effect_preset = _apply_effect_preset
    LivePookalamApp._set_all_effects = _set_all_effects
    LivePookalamApp.NAV = [("HOME", "home"), ("SOURCE", "source"), ("CALIBRATE", "calibrate"), ("ANALYSE", "analyze"), ("DETECT", "detect"), ("EFFECTS", "experience"), ("RUN SHOW", "run")]
    ProjectionWindow.render = _projector_render
    LivePookalamApp._experience_installed = True


__all__ = ["install"]

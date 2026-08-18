"""Field-ready Live Pookalam operator console.

The UI mirrors the approved Live Pookalam mockup: dark control-room layout,
purple accent, workflow navigation, live camera/projector previews, calibration
status, effects, show control, developer diagnostics and field-service tools.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
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

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PROFILE = os.path.join(ROOT, "installation_profile.json")

BG = "#090711"
PANEL = "#11101c"
PANEL2 = "#171526"
PANEL3 = "#201b32"
BORDER = "#2b2540"
TEXT = "#f4f1fa"
MUTED = "#9c95aa"
PURPLE = "#8b35ff"
PURPLE2 = "#6e24d8"
GREEN = "#32e875"
RED = "#ff5e6c"
CYAN = "#2fd8ff"
GOLD = "#ffd24a"

DEFAULT = {
    "camera_index": 0,
    "projector_monitor": 1,
    "projector_width": 1920,
    "projector_height": 1080,
    "homography": None,
    "source": "generated",
    "image": "",
    "showroom": "Default",
    "dev_mode": True,
    "effects": {},
}


def load_state():
    try:
        with open(PROFILE, "r", encoding="utf-8") as f:
            return {**DEFAULT, **json.load(f)}
    except Exception:
        return DEFAULT.copy()


def save_state(state):
    with open(PROFILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def segment_pookalam(frame):
    if frame is None:
        return None, None, 0.0
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] >= 50) & (hsv[:, :, 2] >= 45)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape
    candidates = [c for c in contours if 0.015 * w * h < cv2.contourArea(c) < 0.92 * w * h]
    if not candidates:
        return mask, None, 0.0
    c = max(candidates, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    x, y, bw, bh = cv2.boundingRect(c)
    fill = area / max(1, bw * bh)
    coverage = min(1.0, area / (w * h * 0.30))
    per = cv2.arcLength(c, True)
    circ = 0 if per <= 0 else min(1.0, 4 * math.pi * area / (per * per))
    confidence = max(0.0, min(1.0, 0.5 * fill + 0.3 * coverage + 0.2 * circ))
    return mask, c, confidence


class DrawAdapter:
    def __init__(self, canvas):
        self.canvas = canvas

    def circle(self, x, y, r, fill, width=0):
        self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                fill=fill if width == 0 else "", outline=fill,
                                width=max(1, width))

    def ellipse(self, rect, fill, width=0):
        self.canvas.create_oval(*rect, fill=fill if width == 0 else "",
                                outline=fill, width=max(1, width))

    def line(self, points, fill, width=1):
        self.canvas.create_line(*[v for p in points for v in p], fill=fill,
                                width=width, smooth=True)

    def polygon(self, points, fill):
        self.canvas.create_polygon(*[v for p in points for v in p], fill=fill)


class ProjectionWindow:
    TARGETS = [("MAGENTA", "#ff19d6"), ("CYAN", "#22e6ff"),
               ("YELLOW", "#ffe52e"), ("GREEN", "#31ff75")]

    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("LIVE POOKALAM — PROJECTOR")
        self.win.configure(bg="black")
        self.win.overrideredirect(True)
        self.canvas = tk.Canvas(self.win, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.bind("<Escape>", lambda _e: self.app.stop_show())
        self.w, self.h = 1920, 1080
        self.place()

    def place(self):
        mons = list(get_monitors()) if get_monitors else []
        idx = int(self.app.state.get("projector_monitor", 1))
        if mons:
            idx = min(max(0, idx), len(mons)-1)
            m = mons[idx]
            self.w, self.h = m.width, m.height
            self.win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        else:
            self.win.geometry(f"{self.w}x{self.h}+0+0")
        self.win.attributes("-topmost", True)

    def clear(self):
        self.canvas.delete("all")

    def black(self):
        self.clear()

    def grid(self):
        self.clear()
        for i in range(1, 10):
            x, y = self.w*i/10, self.h*i/10
            self.canvas.create_line(x, 0, x, self.h, fill="#22202c")
            self.canvas.create_line(0, y, self.w, y, fill="#22202c")
        self.canvas.create_text(self.w/2, self.h/2, text="LIVE POOKALAM • MAPPING TEST",
                                fill=TEXT, font=("Segoe UI", 28, "bold"))

    def target(self, index):
        self.clear()
        margin = 0.12
        pts = [(self.w*margin, self.h*margin),
               (self.w*(1-margin), self.h*margin),
               (self.w*(1-margin), self.h*(1-margin)),
               (self.w*margin, self.h*(1-margin))]
        x, y = pts[index]
        name, color = self.TARGETS[index]
        r = min(self.w, self.h) * 0.032
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="white", width=5)
        self.canvas.create_text(x, y, text=str(index+1), fill="black",
                                font=("Segoe UI", 24, "bold"))
        self.canvas.create_text(self.w/2, self.h*0.50,
                                text=f"CALIBRATING  •  TARGET {index+1}  {name}",
                                fill=color, font=("Segoe UI", 26, "bold"))

    def render(self, interaction=None, contour=None):
        self.clear()
        self.app.engine.render(DrawAdapter(self.canvas), self.w, self.h,
                                interaction=interaction or Interaction())
        if self.app.dev_mode and contour is not None:
            pts = contour.reshape(-1, 2).astype(np.float32)
            if self.app.H is not None:
                mapped = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), self.app.H).reshape(-1, 2)
            else:
                ch, cw = self.app.frame.shape[:2]
                mapped = pts.copy()
                mapped[:, 0] = mapped[:, 0] / max(1, cw) * self.w
                mapped[:, 1] = mapped[:, 1] / max(1, ch) * self.h
            mapped[:, 0] *= self.w / max(1, self.app.state.get("projector_width", self.w))
            mapped[:, 1] *= self.h / max(1, self.app.state.get("projector_height", self.h))
            poly = [(float(x), float(y)) for x, y in mapped]
            if len(poly) >= 2:
                self.canvas.create_line(*[v for p in poly for v in p], fill=PURPLE,
                                        width=5, smooth=True)
            self.canvas.create_text(36, 32, text="DEV • REAL POOKALAM EDGE",
                                    anchor="nw", fill=PURPLE,
                                    font=("Segoe UI", 18, "bold"))


class FieldConsole:
    NAV = [("⌂", "HOME", "home"), ("▣", "SOURCE", "source"),
           ("◎", "CALIBRATE", "calibrate"), ("◉", "DETECT", "detect"),
           ("✦", "EXPERIENCE", "experience"), ("▶", "RUN SHOW", "run")]

    def __init__(self, root):
        self.root = root
        self.state = load_state()
        self.page = "home"
        self.dev_mode = bool(self.state.get("dev_mode", True))
        self.root.title("LIVE POOKALAM — Interactive Projection Experience")
        self.root.geometry("1536x980")
        self.root.minsize(1180, 760)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda _e: self.stop_show())
        self.root.bind("<F11>", lambda _e: self.toggle_fullscreen())
        self.cap = cv2.VideoCapture(int(self.state.get("camera_index", 0)), cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.frame = None
        self.preview_photo = None
        self.proj = None
        self.showing = False
        self.H = np.float32(self.state["homography"]) if self.state.get("homography") else None
        self.engine = VisualEngine()
        self.interaction = Interaction()
        self.contour = None
        self.confidence = 0.0
        self.calib_index = -1
        self.calib_history = []
        self.calib_started = 0.0
        self.build()
        self.tick()

    # ---------- common UI ----------
    def button(self, parent, text, command, primary=False, width=None):
        b = tk.Button(parent, text=text, command=command,
                       bg=PURPLE if primary else PANEL3,
                       fg="white" if primary else TEXT,
                       activebackground=PURPLE2, activeforeground="white",
                       relief="flat", bd=0, cursor="hand2",
                       font=("Segoe UI", 10, "bold"),
                       padx=14, pady=9, width=width)
        return b

    def card(self, parent, title, value, status=GREEN, detail=""):
        f = tk.Frame(parent, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        f.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(f, text=title, bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 3))
        tk.Label(f, text=value, bg=PANEL2, fg=status,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14)
        if detail:
            tk.Label(f, text=detail, bg=PANEL2, fg=MUTED,
                     font=("Consolas", 8)).pack(anchor="w", padx=14, pady=(3, 12))
        else:
            tk.Frame(f, bg=PANEL2, height=12).pack()
        return f

    def section(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(12, 6))

    def build(self):
        header = tk.Frame(self.root, bg=BG, height=68)
        header.pack(fill="x", padx=22, pady=(12, 6))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="LIVE POOKALAM", bg=BG, fg=TEXT,
                 font=("Segoe UI", 23, "bold")).pack(side="left")
        tk.Label(brand, text="  Interactive Projection Experience", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left", pady=(8, 0))
        tk.Label(header, text="DEVELOPED BY bnsh.eb", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=28, pady=(8, 0))

        self.dev_var = tk.BooleanVar(value=self.dev_mode)
        tk.Checkbutton(header, text="DEV MODE", variable=self.dev_var,
                       command=self.toggle_dev, bg=BG, fg=TEXT,
                       selectcolor=PANEL3, activebackground=BG,
                       activeforeground=TEXT, font=("Segoe UI", 9, "bold")).pack(side="right", padx=8)
        self.button(header, "⟳  UPDATE & RESTART", self.update_restart).pack(side="right", padx=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=(4, 0))

        self.sidebar = tk.Frame(body, bg=PANEL, width=238,
                                highlightthickness=1, highlightbackground=BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 14))
        self.sidebar.pack_propagate(False)
        brandbox = tk.Frame(self.sidebar, bg=PANEL)
        brandbox.pack(fill="x", padx=16, pady=18)
        tk.Label(brandbox, text="✿", bg=PANEL, fg=GOLD,
                 font=("Segoe UI Symbol", 34)).pack(side="left")
        tk.Frame(brandbox, bg=PANEL).pack(side="left", padx=7)
        tk.Label(brandbox, text="LIVE\nPOOKALAM", bg=PANEL, fg=TEXT,
                 justify="left", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(self.sidebar, text="Interactive Projection Experience",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=18)
        tk.Label(self.sidebar, text="developed by bnsh.eb", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=18, pady=(2, 12))
        self.nav_buttons = {}
        for icon, label, key in self.NAV:
            b = tk.Button(self.sidebar, text=f"  {icon}   {label}",
                          command=lambda k=key: self.show_page(k),
                          bg=PANEL, fg=TEXT, activebackground=PURPLE2,
                          activeforeground="white", relief="flat", bd=0,
                          anchor="w", font=("Segoe UI", 10, "bold"), pady=10)
            b.pack(fill="x", padx=9, pady=2)
            self.nav_buttons[key] = b
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=14, pady=12)
        tk.Label(self.sidebar, text="FIELD SERVICE", bg=PANEL, fg=PURPLE,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(0, 6))
        for label, cmd in [("⟳  UPDATE & RESTART", self.update_restart),
                           ("⚙  SETTINGS", lambda: self.show_page("settings")),
                           ("🔧  DIAGNOSTICS", lambda: self.show_page("diagnostics")),
                           ("?  HELP", lambda: self.show_page("help")),
                           ("⏻  EXIT", self.close)]:
            tk.Button(self.sidebar, text=label, command=cmd, bg=PANEL, fg=TEXT,
                      activebackground=PANEL3, activeforeground=TEXT, relief="flat",
                      anchor="w", font=("Segoe UI", 9), pady=7).pack(fill="x", padx=12)
        self.sys = tk.StringVar(value="●  System Ready")
        tk.Label(self.sidebar, textvariable=self.sys, bg=PANEL, fg=GREEN,
                 font=("Segoe UI", 8, "bold")).pack(side="bottom", anchor="w", padx=18, pady=16)

        self.main = tk.Frame(body, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.show_page("home")

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def page_title(self, title, subtitle):
        tk.Label(self.main, text=title, bg=BG, fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(self.main, text=subtitle, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

    def show_page(self, key):
        self.page = key
        self.clear()
        for k, b in self.nav_buttons.items():
            b.configure(bg=PURPLE if k == key else PANEL,
                        fg="white" if k == key else TEXT)
        method = getattr(self, f"page_{key}", self.page_home)
        method()

    # ---------- pages ----------
    def page_home(self):
        self.page_title("Dashboard", "Monitor the installation, calibration and live experience from one screen.")
        row = tk.Frame(self.main, bg=BG); row.pack(fill="x")
        self.card(row, "▣  PROJECTOR", "CONNECTED" if self.proj else "READY", GREEN,
                  "Display 2  •  1920 × 1080")
        self.card(row, "●  WEBCAM", "CONNECTED" if self.cap.isOpened() else "OFFLINE",
                  GREEN if self.cap.isOpened() else RED, "1280 × 720  •  Live feed")
        self.card(row, "◎  CALIBRATION", "VALID" if self.H is not None else "NOT SET",
                  GREEN if self.H is not None else GOLD,
                  "Saved mapping" if self.H is not None else "Calibration required")
        self.card(row, "▣  SYSTEM", "OK", GREEN, f"Developer Mode: {'ON' if self.dev_mode else 'OFF'}")

        grid = tk.Frame(self.main, bg=BG); grid.pack(fill="both", expand=True, pady=(10, 0))
        left = tk.Frame(grid, bg=BG); left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        right = tk.Frame(grid, bg=BG, width=250); right.pack(side="right", fill="y", padx=(5, 0)); right.pack_propagate(False)

        self.preview_panel(left, "WEBCAM PREVIEW", self.frame, "DEV OVERLAY")
        self.section(right, "QUICK ACTIONS")
        self.button(right, "◎  CALIBRATE", lambda: self.show_page("calibrate"), True).pack(fill="x", pady=4)
        self.button(right, "◉  DETECT POOKALAM", lambda: self.show_page("detect")).pack(fill="x", pady=4)
        self.button(right, "⌁  SHOW EDGE (DEV)", self.show_edge).pack(fill="x", pady=4)
        self.button(right, "▦  TEST PATTERN", self.projector_grid).pack(fill="x", pady=4)
        self.button(right, "■  BLACK SCREEN", self.projector_black).pack(fill="x", pady=4)
        self.section(right, "SHOW CONTROL")
        self.button(right, "▶  RUN SHOW", self.run_show, True).pack(fill="x", pady=4)
        self.button(right, "■  STOP", self.stop_show).pack(fill="x", pady=4)

    def preview_panel(self, parent, title, frame, badge):
        f = tk.Frame(parent, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        f.pack(fill="both", expand=True)
        top = tk.Frame(f, bg=PANEL2); top.pack(fill="x", padx=12, pady=8)
        tk.Label(top, text=title, bg=PANEL2, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(top, text=badge, bg=PANEL3, fg=PURPLE,
                 font=("Segoe UI", 8, "bold"), padx=7, pady=3).pack(side="right")
        self.preview = tk.Label(f, bg="#020204"); self.preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        if frame is not None:
            self.set_preview(frame)

    def page_source(self):
        self.page_title("Source", "Choose what becomes the Pookalam canvas.")
        row = tk.Frame(self.main, bg=BG); row.pack(fill="x", pady=10)
        choices = [("DIGITAL", "Uploaded Pookalam image", "digital"),
                   ("PHYSICAL", "Real flower Pookalam via webcam", "physical"),
                   ("HYBRID", "Real flowers + projected effects", "hybrid"),
                   ("GENERATED", "Development test pattern", "generated")]
        for title, desc, key in choices:
            f = tk.Frame(row, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
            f.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(f, text=title, bg=PANEL2, fg=PURPLE,
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(18, 4))
            tk.Label(f, text=desc, bg=PANEL2, fg=MUTED, wraplength=180,
                     font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 15))
            self.button(f, "SELECT", lambda k=key: self.set_source(k), key == self.state.get("source")).pack(anchor="w", padx=16, pady=(0, 16))
        self.section(self.main, "DIGITAL SOURCE")
        self.button(self.main, "＋  CHOOSE POOKALAM IMAGE", self.choose_image).pack(anchor="w")
        self.source_label = tk.Label(self.main, text=self.state.get("image") or "No image selected",
                                     bg=BG, fg=MUTED, font=("Consolas", 9)); self.source_label.pack(anchor="w", pady=10)

    def page_calibrate(self):
        self.page_title("Calibration", "Automated live sequence. Re-run whenever the projector or webcam moves.")
        top = tk.Frame(self.main, bg=BG); top.pack(fill="x")
        self.calib_status = tk.StringVar(value="READY")
        self.calib_detail = tk.StringVar(value="The old map remains active until a new valid map is accepted.")
        tk.Label(top, textvariable=self.calib_status, bg=BG, fg=GOLD,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(top, textvariable=self.calib_detail, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))
        actions = tk.Frame(self.main, bg=BG); actions.pack(fill="x", pady=(0, 8))
        self.button(actions, "◎  CALIBRATE", self.start_calibration, True).pack(side="left", padx=(0, 5))
        self.button(actions, "▦  PROJECTOR GRID", self.projector_grid).pack(side="left", padx=5)
        self.button(actions, "■  STOP CALIBRATION", self.stop_calibration).pack(side="left", padx=5)
        self.button(actions, "CLEAR MAP", self.clear_calibration).pack(side="left", padx=5)
        body = tk.Frame(self.main, bg=BG); body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); left.pack(side="left", fill="both", expand=True, padx=(0,5))
        self.calib_preview = tk.Label(left, bg="#020204"); self.calib_preview.pack(fill="both", expand=True, padx=8, pady=8)
        right = tk.Frame(body, bg=PANEL2, width=280, highlightthickness=1, highlightbackground=BORDER); right.pack(side="right", fill="y", padx=(5,0)); right.pack_propagate(False)
        tk.Label(right, text="AUTOMATED SEQUENCE", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=14)
        self.calib_labels = []
        names = ["MAGENTA", "CYAN", "YELLOW", "GREEN"]
        for i, name in enumerate(names):
            var = tk.StringVar(value=f"{i+1}   {name}   WAITING")
            lab = tk.Label(right, textvariable=var, bg=PANEL2, fg=MUTED, font=("Consolas", 10, "bold")); lab.pack(anchor="w", padx=16, pady=8); self.calib_labels.append((var, lab))
        self.calib_progress = tk.StringVar(value="0 / 4")
        tk.Label(right, textvariable=self.calib_progress, bg=PANEL2, fg=PURPLE, font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=16, pady=8)
        self.calib_error = tk.StringVar(value="Reprojection error: —")
        tk.Label(right, textvariable=self.calib_error, bg=PANEL2, fg=MUTED, font=("Consolas", 9)).pack(anchor="w", padx=16)

    def page_detect(self):
        self.page_title("Detect Pookalam", "See what the webcam actually understands before choosing interaction behaviour.")
        row = tk.Frame(self.main, bg=BG); row.pack(fill="x")
        self.card(row, "BOUNDARY", "LOCKED" if self.contour is not None else "SEARCHING", GREEN if self.contour is not None else GOLD)
        self.card(row, "CONFIDENCE", f"{self.confidence*100:.0f}%", GREEN if self.confidence > .7 else GOLD)
        self.card(row, "DEV OVERLAY", "ON" if self.dev_mode else "OFF", PURPLE)
        f = tk.Frame(self.main, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); f.pack(fill="both", expand=True, pady=10)
        self.detect_preview = tk.Label(f, bg="#020204"); self.detect_preview.pack(fill="both", expand=True, padx=8, pady=8)

    def page_experience(self):
        self.page_title("Experience", "Build the Living Pookalam effect stack. Interaction behaviour remains configurable.")
        body = tk.Frame(self.main, bg=BG); body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=PANEL2, width=270, highlightthickness=1, highlightbackground=BORDER); left.pack(side="left", fill="y", padx=(0,5)); left.pack_propagate(False)
        tk.Label(left, text="EFFECT LAYERS", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=14)
        for name in ["Breathing Glow", "Radial Wave", "Petal Flow", "Fireflies", "Lotus Bloom", "Interaction Ripple", "Interaction Sparks", "Spiral", "Colour Pulse"]:
            var = tk.BooleanVar(value=True)
            tk.Checkbutton(left, text=name, variable=var, bg=PANEL2, fg=TEXT,
                           selectcolor=PANEL3, activebackground=PANEL2,
                           activeforeground=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=4)
        right = tk.Frame(body, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); right.pack(side="left", fill="both", expand=True, padx=(5,0))
        tk.Label(right, text="EFFECT PREVIEW", bg=PANEL2, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=12)
        self.effect_canvas = tk.Canvas(right, bg="#020204", highlightthickness=0); self.effect_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        for label, value in [("Intensity", 75), ("Speed", 50), ("Size", 60), ("Opacity", 80)]:
            row = tk.Frame(right, bg=PANEL2); row.pack(fill="x", padx=14, pady=3); tk.Label(row, text=label, bg=PANEL2, fg=MUTED, width=10, anchor="w").pack(side="left"); tk.Scale(row, from_=0, to=100, orient="horizontal", bg=PANEL2, fg=TEXT, troughcolor=PANEL3, highlightthickness=0, showvalue=True, value=value).pack(side="left", fill="x", expand=True)

    def page_run(self):
        self.page_title("Run Show", "Final operator surface. Start, pause and stop the projection safely.")
        f = tk.Frame(self.main, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER); f.pack(fill="both", expand=True)
        tk.Label(f, text="LIVE OUTPUT", bg=PANEL2, fg=GREEN if self.showing else MUTED, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=14)
        self.run_preview = tk.Label(f, bg="#020204"); self.run_preview.pack(fill="both", expand=True, padx=10, pady=10)
        bar = tk.Frame(self.main, bg=BG); bar.pack(fill="x", pady=10)
        self.button(bar, "▶  RUN SHOW", self.run_show, True).pack(side="left", padx=4)
        self.button(bar, "Ⅱ  PAUSE", self.pause_show).pack(side="left", padx=4)
        self.button(bar, "■  STOP", self.stop_show).pack(side="left", padx=4)

    def page_settings(self):
        self.page_title("Settings", "Installation profile and field hardware configuration.")
        for label, key in [("Showroom", "showroom"), ("Camera index", "camera_index"), ("Projector monitor", "projector_monitor")]:
            row = tk.Frame(self.main, bg=PANEL2); row.pack(fill="x", pady=4); tk.Label(row, text=label, bg=PANEL2, fg=MUTED, width=22, anchor="w").pack(side="left", padx=12, pady=10); e=tk.Entry(row, bg="#0c0a12", fg=TEXT, insertbackground=TEXT, relief="flat"); e.insert(0,str(self.state.get(key,""))); e.pack(side="left", fill="x", expand=True, padx=12, pady=8); setattr(self, "setting_"+key, e)
        self.button(self.main, "SAVE SETTINGS", self.save_settings, True).pack(anchor="w", pady=10)

    def page_diagnostics(self):
        self.page_title("Diagnostics", "Field diagnostics for camera, projector, calibration and detection.")
        text = tk.Text(self.main, bg="#05040a", fg=TEXT, insertbackground=TEXT, relief="flat", font=("Consolas", 9))
        text.pack(fill="both", expand=True)
        lines = [f"Live Pookalam diagnostics", f"Python: {sys.version.split()[0]}", f"OpenCV: {cv2.__version__}", f"Webcam: {'CONNECTED' if self.cap.isOpened() else 'OFFLINE'}", f"Projector window: {'OPEN' if self.proj else 'CLOSED'}", f"Calibration: {'VALID' if self.H is not None else 'NOT SET'}", f"Developer mode: {self.dev_mode}"]
        text.insert("1.0", "\n".join(lines)); text.configure(state="disabled")

    def page_help(self):
        self.page_title("Help", "Field workflow for Live Pookalam.")
        tk.Label(self.main, text="SOURCE → CALIBRATE → DETECT → EXPERIENCE → RUN SHOW\n\nMove either camera or projector? Press CALIBRATE and let the automated four-target sequence complete.\n\nDeveloper Mode projects the real camera segmentation edge for verification.\n\nESC stops the show. F11 toggles fullscreen.", bg=BG, fg=TEXT, justify="left", font=("Segoe UI", 11)).pack(anchor="nw", pady=20)

    # ---------- hardware / actions ----------
    def set_source(self, key):
        self.state["source"] = key; save_state(self.state); self.show_page("source")

    def choose_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")])
        if path:
            self.state["image"] = path; self.state["source"] = "digital"; save_state(self.state); self.show_page("source")

    def open_projector(self):
        if self.proj is None or not self.proj.win.winfo_exists():
            self.proj = ProjectionWindow(self)
        self.proj.place()

    def projector_grid(self): self.open_projector(); self.proj.grid()
    def projector_black(self): self.open_projector(); self.proj.black()

    def start_calibration(self):
        self.open_projector(); self.stop_show(); self.open_projector()
        self.calib_index = 0; self.calib_history = []; self.calib_started = time.perf_counter()
        self.proj.target(0)
        self.calib_status.set("CALIBRATING • TARGET 1 / 4")
        self.calib_detail.set("Point the webcam at the projected target. Acquisition is automatic.")
        for i,(var,lab) in enumerate(self.calib_labels): var.set(f"{i+1}   {ProjectionWindow.TARGETS[i][0]}   {'ACTIVE' if i==0 else 'WAITING'}"); lab.configure(fg=PURPLE if i==0 else MUTED)
        self.calib_progress.set("0 / 4")

    def stop_calibration(self):
        self.calib_index = -1
        if self.proj: self.proj.black()
        if hasattr(self, "calib_status"): self.calib_status.set("CALIBRATION STOPPED")

    def detect_target(self, frame, index):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ranges = [(145,175), (85,110), (20,40), (45,85)]
        lo,hi = ranges[index]
        mask = cv2.inRange(hsv, (lo,90,80), (hi,255,255))
        contours,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates=[c for c in contours if 0.00005*frame.shape[0]*frame.shape[1] < cv2.contourArea(c) < 0.05*frame.shape[0]*frame.shape[1]]
        if not candidates:return None
        c=max(candidates,key=cv2.contourArea); m=cv2.moments(c)
        if not m["m00"]:return None
        return (m["m10"]/m["m00"],m["m01"]/m["m00"])

    def calibration_tick(self):
        if self.calib_index < 0 or self.frame is None:return
        p=self.detect_target(self.frame,self.calib_index)
        if p is None:
            self.calib_history=[]
            self.calib_detail.set("Searching for the active projected target…")
            return
        self.calib_history.append(p)
        if len(self.calib_history) > 8:self.calib_history.pop(0)
        if len(self.calib_history) < 8:
            self.calib_detail.set(f"Target {self.calib_index+1}: stable frames {len(self.calib_history)}/8")
            return
        arr=np.array(self.calib_history,np.float32); mean=arr.mean(0); spread=float(np.max(np.linalg.norm(arr-mean,axis=1)))
        self.calib_detail.set(f"Target {self.calib_index+1}: stable • jitter {spread:.1f}px")
        if spread > 12:return
        self.calib_points.append(tuple(mean)) if hasattr(self,'calib_points') else setattr(self,'calib_points',[tuple(mean)])
        idx=self.calib_index; self.calib_labels[idx][0].set(f"{idx+1}   {ProjectionWindow.TARGETS[idx][0]}   LOCKED"); self.calib_labels[idx][1].configure(fg=GREEN)
        self.calib_progress.set(f"{idx+1} / 4"); self.calib_history=[]
        if idx < 3:
            self.calib_index += 1; self.proj.target(self.calib_index); self.calib_labels[self.calib_index][0].set(f"{self.calib_index+1}   {ProjectionWindow.TARGETS[self.calib_index][0]}   ACTIVE"); self.calib_labels[self.calib_index][1].configure(fg=PURPLE); return
        cam=np.float32(self.calib_points); margin=.12; dst=np.float32([(self.proj.w*margin,self.proj.h*margin),(self.proj.w*(1-margin),self.proj.h*margin),(self.proj.w*(1-margin),self.proj.h*(1-margin)),(self.proj.w*margin,self.proj.h*(1-margin))]); H,_=cv2.findHomography(cam,dst,cv2.RANSAC); 
        if H is None:self.stop_calibration(); self.calib_status.set("CALIBRATION FAILED"); return
        self.H=H; self.state["homography"]=H.tolist(); self.state["projector_width"]=self.proj.w; self.state["projector_height"]=self.proj.h; save_state(self.state); self.calib_error.set("Reprojection error: VALID"); self.calib_status.set("CALIBRATION COMPLETE"); self.calib_detail.set("New map accepted. The previous map was retained until this point."); self.calib_index=-1; self.proj.black()

    def clear_calibration(self):
        self.H=None; self.state["homography"]=None; save_state(self.state); self.calib_status.set("MAP CLEARED") if hasattr(self,'calib_status') else None

    def show_edge(self):
        self.open_projector();
        if self.contour is not None:self.proj.render(self.interaction,self.contour)

    def run_show(self):
        self.open_projector(); self.showing=True; self.page="run"; self.show_page("run")

    def pause_show(self): self.showing=False
    def stop_show(self):
        self.showing=False
        if self.proj:self.proj.black()

    def toggle_dev(self):
        self.dev_mode=bool(self.dev_var.get()); self.state["dev_mode"]=self.dev_mode; save_state(self.state)

    def save_settings(self):
        for key in ("showroom","camera_index","projector_monitor"):
            try:self.state[key]=int(getattr(self,"setting_"+key).get()) if key != "showroom" else getattr(self,"setting_"+key).get()
            except ValueError:pass
        save_state(self.state); messagebox.showinfo("Live Pookalam","Settings saved.")

    def update_restart(self):
        if not messagebox.askyesno("Update & Restart", "Download the latest Live Pookalam build and restart now?"):return
        try:
            subprocess.run(["git","pull","--ff-only"],cwd=ROOT,check=True,capture_output=True,text=True)
            subprocess.run([sys.executable,"-m","pip","install","-r","requirements.txt"],cwd=ROOT,check=True,capture_output=True,text=True)
            subprocess.Popen([sys.executable,"-m","app.ui"],cwd=ROOT)
            self.close(restart=True)
        except Exception as exc:
            messagebox.showerror("Update failed", str(exc))

    def set_preview(self, frame):
        if not hasattr(self,"preview") or self.preview.winfo_exists() is False:return
        img=cv2.cvtColor(cv2.resize(frame,(900,506)),cv2.COLOR_BGR2RGB); self.preview_photo=ImageTk.PhotoImage(Image.fromarray(img)); self.preview.configure(image=self.preview_photo)

    def tick(self):
        ok,frame=self.cap.read()
        if ok:
            self.frame=frame
            _,self.contour,self.confidence=segment_pookalam(frame)
            if self.page=="home":self.set_preview(frame)
            elif self.page=="detect" and hasattr(self,"detect_preview"):
                debug=frame.copy()
                if self.contour is not None:cv2.drawContours(debug,[self.contour],-1,(190,134,255),4)
                img=cv2.cvtColor(cv2.resize(debug,(900,506)),cv2.COLOR_BGR2RGB);self.detect_photo=ImageTk.PhotoImage(Image.fromarray(img));self.detect_preview.configure(image=self.detect_photo)
            elif self.page=="calibrate" and hasattr(self,"calib_preview"):
                debug=frame.copy();
                if self.calib_index>=0:
                    p=self.detect_target(frame,self.calib_index)
                    if p:cv2.circle(debug,(int(p[0]),int(p[1])),24,(0,255,0),3)
                img=cv2.cvtColor(cv2.resize(debug,(900,506)),cv2.COLOR_BGR2RGB);self.calib_photo=ImageTk.PhotoImage(Image.fromarray(img));self.calib_preview.configure(image=self.calib_photo)
            if self.calib_index>=0:self.calibration_tick()
            if self.showing and self.proj:self.proj.render(self.interaction,self.contour)
        self.root.after(33,self.tick)

    def toggle_fullscreen(self): self.root.attributes("-fullscreen", not bool(self.root.attributes("-fullscreen")))

    def close(self, restart=False):
        try:self.cap.release()
        except Exception:pass
        if self.proj:
            try:self.proj.win.destroy()
            except Exception:pass
        if not restart:self.root.destroy()


def launch():
    root=tk.Tk(); FieldConsole(root); root.mainloop()


if __name__ == "__main__":
    launch()

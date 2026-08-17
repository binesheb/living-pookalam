"""Windows 11 operator dashboard for Living Pookalam.

The dashboard is intentionally thin: hardware/vision/rendering stay in the core
services while this UI gives an operator a single place to control them.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox


BG = "#08080d"
PANEL = "#111118"
BORDER = "#2b2b35"
TEXT = "#eeeeee"
MUTED = "#a9a9b5"
GOLD = "#ffd45a"
GREEN = "#7dff9a"
RED = "#ff7d7d"


class OperatorDashboard:
    def __init__(self, root: tk.Tk, service=None) -> None:
        self.root = root
        self.service = service
        self.root.title("Living Pookalam — Operator")
        self.root.geometry("1180x720")
        self.root.minsize(980, 620)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.status = tk.StringVar(value="READY")
        self.source = tk.StringVar(value="Not selected")
        self.profile = tk.StringVar(value="template")
        self.cards: dict[str, tk.Label] = {}
        self.build()

    def build(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 14))
        tk.Label(header, text="LIVING POOKALAM", bg=BG, fg=GOLD,
                 font=("Segoe UI", 28, "bold")).pack(anchor="w")
        tk.Label(header, text="ONAM 2026  •  WINDOWS 11  •  OPERATOR MODE",
                 bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=8)

        nav = tk.Frame(body, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER, width=300)
        nav.pack(side="left", fill="y", padx=(0, 18))
        nav.pack_propagate(False)

        self.button(nav, "DIGITAL POOKALAM", self.choose_digital)
        self.button(nav, "PHYSICAL POOKALAM", lambda: self.set_source("Physical Pookalam"))
        self.button(nav, "HYBRID", lambda: self.set_source("Hybrid"))
        self.separator(nav)
        self.button(nav, "CALIBRATE", self.calibrate)
        self.button(nav, "DETECT POOKALAM", self.detect)
        self.button(nav, "INTERACTION TEST", self.interaction_test)
        self.separator(nav)
        self.button(nav, "▶  RUN SHOW", self.run_show, accent=True)
        self.button(nav, "■  STOP SHOW", self.stop_show)

        content = tk.Frame(body, bg=BG)
        content.pack(side="left", fill="both", expand=True)

        status_panel = tk.Frame(content, bg=PANEL, highlightthickness=1,
                                highlightbackground=BORDER)
        status_panel.pack(fill="x")
        tk.Label(status_panel, text="SYSTEM STATUS", bg=PANEL, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(status_panel, textvariable=self.status, bg=PANEL, fg=GREEN,
                 font=("Consolas", 19, "bold")).pack(anchor="w", padx=18, pady=(0, 14))

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill="x", pady=14)
        for name in ("WEBCAM", "PROJECTOR", "CALIBRATION", "POOKALAM", "INTERACTION"):
            self.card(cards, name)

        preview = tk.Frame(content, bg="#05050a", highlightthickness=1,
                           highlightbackground=BORDER)
        preview.pack(fill="both", expand=True)
        tk.Label(preview, text="LIVE PREVIEW", bg="#05050a", fg=MUTED,
                 font=("Segoe UI", 10, "bold")).pack(anchor="nw", padx=14, pady=10)
        tk.Label(preview, text="Camera / projector preview will appear here",
                 bg="#05050a", fg="#555562", font=("Segoe UI", 17)).pack(expand=True)

        footer = tk.Frame(content, bg=BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, text="Source:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(footer, textvariable=self.source, bg=BG, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(5, 25))
        tk.Label(footer, text="Profile:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(footer, textvariable=self.profile, bg=BG, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

        self.root.bind("<Escape>", lambda _e: self.close())
        self.root.bind("<c>", lambda _e: self.calibrate())
        self.root.bind("<d>", lambda _e: self.choose_digital())
        self.root.bind("<p>", lambda _e: self.set_source("Physical Pookalam"))
        self.root.bind("<h>", lambda _e: self.set_source("Hybrid"))
        self.root.bind("<r>", lambda _e: self.run_show())
        self.root.bind("<s>", lambda _e: self.stop_show())

    def button(self, parent, label, command, accent=False):
        tk.Button(parent, text=label, command=command, relief="flat",
                  bg="#3b3018" if accent else "#191920",
                  fg=GOLD if accent else TEXT,
                  activebackground="#5a471e", activeforeground="white",
                  font=("Segoe UI", 10, "bold"), cursor="hand2",
                  height=2).pack(fill="x", padx=16, pady=5)

    def separator(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16, pady=10)

    def card(self, parent, name):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        f.pack(side="left", fill="x", expand=True, padx=3)
        tk.Label(f, text=name, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(pady=(9, 2))
        v = tk.Label(f, text="READY", bg=PANEL, fg="#777784",
                     font=("Consolas", 10, "bold"))
        v.pack(pady=(0, 9))
        self.cards[name] = v

    def set_card(self, name, value, good=None):
        color = "#777784" if good is None else (GREEN if good else RED)
        if name in self.cards:
            self.cards[name].configure(text=value, fg=color)

    def set_source(self, value):
        self.source.set(value)
        self.status.set(f"SOURCE: {value.upper()}")
        self.set_card("POOKALAM", "SELECTED", True)

    def choose_digital(self):
        path = filedialog.askopenfilename(
            title="Choose Pookalam image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All files", "*.*")],
        )
        if path:
            self.set_source(f"Digital • {path.split('/')[-1].split('\\\\')[-1]}")

    def calibrate(self):
        self.status.set("CALIBRATION READY")
        self.set_card("CALIBRATION", "READY", True)
        messagebox.showinfo("Calibration", "Calibration workspace is ready. The next calibration stage will guide you through the floor and projector targets.")

    def detect(self):
        self.status.set("POOKALAM DETECTION READY")
        self.set_card("POOKALAM", "DETECTION", None)

    def interaction_test(self):
        self.status.set("INTERACTION TEST")
        self.set_card("INTERACTION", "TESTING", None)

    def run_show(self):
        self.status.set("SHOW RUNNING")
        self.set_card("PROJECTOR", "OUTPUT", True)
        self.set_card("INTERACTION", "ACTIVE", True)

    def stop_show(self):
        self.status.set("STOPPED")
        self.set_card("INTERACTION", "READY", None)

    def close(self):
        self.root.destroy()


def launch(service=None):
    root = tk.Tk()
    OperatorDashboard(root, service=service)
    root.mainloop()


if __name__ == "__main__":
    launch()

"""Polished Windows field UI shell for Live Pookalam.

The shell keeps the existing production page implementations and calibration
state machine, but presents them through a cleaner control-room workflow.
"""
from __future__ import annotations

import tkinter as tk

from app.ui.field_product import ProductFieldConsole
from app.ui.field_ui import BG, BORDER, PANEL, PANEL2, PANEL3, TEXT, MUTED, PURPLE, PURPLE2, GREEN, RED, CYAN, GOLD


class PremiumProductFieldConsole(ProductFieldConsole):
    """Production console with a responsive, operator-first visual shell."""

    NAV = [
        ("01", "HOME", "home", "Overview"),
        ("02", "SOURCE", "source", "Pookalam source"),
        ("03", "CALIBRATE", "calibrate", "Camera + projector"),
        ("04", "ANALYSE", "analyze", "Pattern intelligence"),
        ("05", "DETECT", "detect", "Live boundary"),
        ("06", "EFFECTS", "experience", "Living effects"),
        ("07", "RUN SHOW", "run", "Final output"),
    ]

    def build(self):
        self.root.configure(bg="#07080d")
        self.root.title("LIVE POOKALAM  •  Control Room")
        self.root.geometry("1500x920")
        self.root.minsize(1180, 760)

        top = tk.Frame(self.root, bg="#07080d")
        top.pack(fill="x", padx=24, pady=(18, 10))

        brand = tk.Frame(top, bg="#07080d")
        brand.pack(side="left")
        mark = tk.Canvas(brand, width=42, height=42, bg="#07080d", highlightthickness=0)
        mark.pack(side="left", padx=(0, 12))
        mark.create_oval(4, 4, 38, 38, outline=GOLD, width=2)
        mark.create_oval(12, 12, 30, 30, outline=PURPLE, width=2)
        mark.create_oval(19, 19, 23, 23, fill=GOLD, outline="")
        title = tk.Frame(brand, bg="#07080d")
        title.pack(side="left")
        tk.Label(title, text="LIVE POOKALAM", bg="#07080d", fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(title, text="INTERACTIVE PROJECTION EXPERIENCE  •  ONAM 2026",
                 bg="#07080d", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")

        tk.Label(top, text="developed by bnsh.eb", bg="#07080d", fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left", padx=28, pady=(8, 0))

        right = tk.Frame(top, bg="#07080d")
        right.pack(side="right")
        self.header_status = tk.StringVar(value="● SYSTEM READY")
        tk.Label(right, textvariable=self.header_status, bg="#07080d", fg=GREEN,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=14)
        self.dev_var = tk.BooleanVar(value=self.dev_mode)
        tk.Checkbutton(right, text="DEV MODE", variable=self.dev_var,
                       command=self.toggle_dev, bg="#07080d", fg=PURPLE,
                       selectcolor=PANEL3, activebackground="#07080d",
                       activeforeground=PURPLE, font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)
        self.button(right, "UPDATE & RESTART", self.update_restart).pack(side="left", padx=6)

        body = tk.Frame(self.root, bg="#07080d")
        body.pack(fill="both", expand=True, padx=24, pady=(2, 18))

        self.sidebar = tk.Frame(body, bg=PANEL, width=258,
                                highlightthickness=1, highlightbackground=BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="SHOW WORKFLOW", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(18, 10))
        self.nav_buttons = {}
        for number, label, key, desc in self.NAV:
            holder = tk.Frame(self.sidebar, bg=PANEL)
            holder.pack(fill="x", padx=9, pady=2)
            b = tk.Button(holder, text=f"{number}   {label}",
                          command=lambda k=key: self.show_page(k),
                          bg=PANEL, fg=TEXT, activebackground=PURPLE2,
                          activeforeground="white", relief="flat", bd=0,
                          anchor="w", cursor="hand2",
                          font=("Segoe UI", 10, "bold"), pady=8)
            b.pack(fill="x")
            tk.Label(holder, text=desc, bg=PANEL, fg="#6f687d",
                     font=("Segoe UI", 7)).pack(anchor="w", padx=37, pady=(0, 4))
            self.nav_buttons[key] = b

        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=12)
        tk.Label(self.sidebar, text="FIELD TOOLS", bg=PANEL, fg=PURPLE,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(0, 6))
        for label, cmd in [
            ("⚙  SETTINGS", lambda: self.show_page("settings")),
            ("⌁  DIAGNOSTICS", lambda: self.show_page("diagnostics")),
            ("?  HELP", lambda: self.show_page("help")),
        ]:
            tk.Button(self.sidebar, text=label, command=cmd, bg=PANEL, fg=TEXT,
                      activebackground=PANEL3, activeforeground=TEXT, relief="flat",
                      anchor="w", cursor="hand2", font=("Segoe UI", 9), pady=7).pack(fill="x", padx=12)

        bottom = tk.Frame(self.sidebar, bg="#0c0d13", highlightthickness=1, highlightbackground=BORDER)
        bottom.pack(side="bottom", fill="x", padx=12, pady=12)
        tk.Label(bottom, text="INSTALLATION", bg="#0c0d13", fg=MUTED,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(bottom, textvariable=self._installation_status(), bg="#0c0d13", fg=GREEN,
                 font=("Consolas", 8, "bold")).pack(anchor="w", padx=10, pady=(0, 9))

        self.main = tk.Frame(body, bg="#07080d")
        self.main.pack(side="left", fill="both", expand=True)
        self.show_page("home")

    def _installation_status(self):
        self.installation_var = tk.StringVar()
        self._refresh_installation_status()
        return self.installation_var

    def _refresh_installation_status(self):
        if not hasattr(self, "installation_var"):
            return
        camera = "CAMERA OK" if self.cap.isOpened() else "CAMERA OFFLINE"
        calibration = "MAP VALID" if self.H is not None else "MAP REQUIRED"
        self.installation_var.set(f"{camera}  •  {calibration}")

    def show_page(self, key):
        super().show_page(key)
        if hasattr(self, "header_status"):
            if key == "run":
                self.header_status.set("● LIVE SHOW" if self.showing else "● SHOW STANDBY")
            elif key == "calibrate":
                self.header_status.set("● CALIBRATION READY")
            else:
                self.header_status.set("● SYSTEM READY")
        self._refresh_installation_status()

    def page_home(self):
        self.page_title("Good evening. The floor is ready.",
                        "A single control room for the real Pookalam, projection mapping, colour calibration and Living Effects.")

        hero = tk.Frame(self.main, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        hero.pack(fill="x", pady=(0, 10))
        left = tk.Frame(hero, bg=PANEL2)
        left.pack(side="left", fill="both", expand=True, padx=18, pady=16)
        tk.Label(left, text="INSTALLATION STATUS", bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        status = "READY FOR CALIBRATION" if self.H is None else "READY FOR EXPERIENCE"
        colour = GOLD if self.H is None else GREEN
        tk.Label(left, text=status, bg=PANEL2, fg=colour,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(5, 2))
        tk.Label(left, text="Camera → geometry → colour → pattern → mask → effects",
                 bg=PANEL2, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        actions = tk.Frame(hero, bg=PANEL2)
        actions.pack(side="right", padx=18, pady=16)
        self.button(actions, "CALIBRATE", lambda: self.show_page("calibrate"), True).pack(side="left", padx=4)
        self.button(actions, "RUN SHOW", self.run_show).pack(side="left", padx=4)
        self.button(actions, "BLACK", self.projector_black).pack(side="left", padx=4)

        cards = tk.Frame(self.main, bg="#07080d")
        cards.pack(fill="x", pady=(0, 10))
        self.card(cards, "PROJECTOR", "READY", GREEN, "Windows display  •  native output")
        self.card(cards, "WEBCAM", "CONNECTED" if self.cap.isOpened() else "OFFLINE",
                  GREEN if self.cap.isOpened() else RED, "Live floor feed")
        self.card(cards, "CALIBRATION", "VALID" if self.H is not None else "REQUIRED",
                  GREEN if self.H is not None else GOLD, "Camera ↔ projector map")
        self.card(cards, "DEVELOPER", "ON" if self.dev_mode else "OFF",
                  PURPLE if self.dev_mode else MUTED, "Real edge overlay")

        lower = tk.Frame(self.main, bg="#07080d")
        lower.pack(fill="both", expand=True)
        preview = tk.Frame(lower, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        preview.pack(side="left", fill="both", expand=True, padx=(0, 6))
        topbar = tk.Frame(preview, bg=PANEL2); topbar.pack(fill="x", padx=14, pady=10)
        tk.Label(topbar, text="LIVE CAMERA / FLOOR", bg=PANEL2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(topbar, text="REAL-TIME", bg="#0e1e18", fg=GREEN,
                 font=("Segoe UI", 7, "bold"), padx=8, pady=3).pack(side="right")
        self.preview = tk.Label(preview, bg="#020204")
        self.preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        if self.frame is not None:
            self.set_preview(self.frame)

        quick = tk.Frame(lower, bg=PANEL2, width=250, highlightthickness=1, highlightbackground=BORDER)
        quick.pack(side="right", fill="y", padx=(6, 0)); quick.pack_propagate(False)
        tk.Label(quick, text="QUICK ACTIONS", bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        for text, cmd, primary in [
            ("CALIBRATE", lambda: self.show_page("calibrate"), True),
            ("ANALYSE POOKALAM", lambda: self.show_page("analyze"), False),
            ("SHOW REAL EDGE", self.show_edge, False),
            ("TEST PATTERN", self.projector_grid, False),
            ("BLACK SCREEN", self.projector_black, False),
        ]:
            self.button(quick, text, cmd, primary).pack(fill="x", padx=10, pady=4)
        tk.Frame(quick, bg=BORDER, height=1).pack(fill="x", padx=12, pady=12)
        tk.Label(quick, text="SHOW CONTROL", bg=PANEL2, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(0, 5))
        self.button(quick, "RUN SHOW", self.run_show, True).pack(fill="x", padx=10, pady=4)
        self.button(quick, "STOP SHOW", self.stop_show).pack(fill="x", padx=10, pady=4)


__all__ = ["PremiumProductFieldConsole"]

"""Field launcher wrapper for Live Pookalam.

Adds field-operator actions without coupling update behavior into the rendering engine.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from app.update_manager import update_and_restart
from app.ui import calibration_realtime
from app.ui.live_pookalam_app import LivePookalamApp


def _run_update(self: LivePookalamApp) -> None:
    button = getattr(self, "_update_button", None)
    if button is not None:
        button.configure(state="disabled", text="UPDATING…")

    def worker() -> None:
        result = update_and_restart()
        def finish() -> None:
            if result.ok:
                # The updater launches the fresh process; close this UI immediately.
                self.running = False
                try:
                    self.close()
                except Exception:
                    self.root.destroy()
            else:
                if button is not None:
                    button.configure(state="normal", text="UPDATE & RESTART")
                messagebox.showerror("Update failed", result.message, parent=self.root)
        self.root.after(0, finish)

    threading.Thread(target=worker, daemon=True).start()


def _page_home(self: LivePookalamApp) -> None:
    # Keep the existing home workflow and add a field-service control row.
    self._original_page_home()
    frame = tk.Frame(self.main, bg="#11141a")
    frame.pack(fill="x", pady=(0, 10))
    tk.Label(
        frame,
        text="FIELD SERVICE",
        bg="#11141a",
        fg="#98a2ae",
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left", padx=14, pady=10)
    self._update_button = tk.Button(
        frame,
        text="UPDATE & RESTART",
        command=lambda: _run_update(self),
        bg="#4a3a18",
        fg="#ffd45a",
        activebackground="#624d20",
        activeforeground="white",
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        height=2,
        padx=16,
    )
    self._update_button.pack(side="right", padx=10, pady=6)
    tk.Label(
        frame,
        text="Pull latest main branch + update dependencies + restart",
        bg="#11141a",
        fg="#98a2ae",
        font=("Segoe UI", 9),
    ).pack(side="right", padx=10)


def install() -> None:
    if getattr(LivePookalamApp, "_field_launcher_installed", False):
        return
    calibration_realtime.install()
    LivePookalamApp._original_page_home = LivePookalamApp.page_home
    LivePookalamApp.page_home = _page_home
    LivePookalamApp._field_launcher_installed = True


def launch() -> None:
    install()
    root = tk.Tk()
    LivePookalamApp(root)
    root.mainloop()


__all__ = ["install", "launch"]

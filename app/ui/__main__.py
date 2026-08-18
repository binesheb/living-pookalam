"""Windows field console entry point for Live Pookalam.

Paint a native Tk splash before importing the heavy vision/effects stack so a
slow Python/OpenCV import or camera backend can never make Windows appear to
have a hung application.
"""
from __future__ import annotations

import threading
import traceback
import tkinter as tk

from app.ui.camera_bootstrap import install_nonblocking_camera

install_nonblocking_camera()


def launch() -> None:
    root = tk.Tk()
    root.title("LIVE POOKALAM")
    root.geometry("760x430")
    root.minsize(620, 360)
    root.configure(bg="#090711")

    tk.Label(root, text="LIVE POOKALAM", bg="#090711", fg="#f4f1fa",
             font=("Segoe UI", 30, "bold")).pack(pady=(85, 8))
    tk.Label(root, text="Interactive Projection Experience", bg="#090711",
             fg="#9c95aa", font=("Segoe UI", 12)).pack()
    status = tk.StringVar(value="Starting control room…")
    tk.Label(root, textvariable=status, bg="#090711", fg="#8b35ff",
             font=("Segoe UI", 11, "bold")).pack(pady=34)
    tk.Label(root, text="developed by bnsh.eb", bg="#090711", fg="#6f687d",
             font=("Segoe UI", 9)).pack()

    result: dict[str, object] = {}

    def load_application() -> None:
        try:
            result["console"] = __import__("app.ui.field_product", fromlist=["ProductFieldConsole"]).ProductFieldConsole
        except Exception:
            result["error"] = traceback.format_exc()

    def poll() -> None:
        if "error" in result:
            status.set("STARTUP ERROR — see terminal")
            print(result["error"])
            return
        console = result.get("console")
        if console is None:
            root.after(50, poll)
            return
        for widget in root.winfo_children():
            widget.destroy()
        try:
            console(root)
        except Exception:
            print(traceback.format_exc())
            status.set("STARTUP ERROR — see terminal")

    root.after(50, poll)
    threading.Thread(target=load_application, name="live-pookalam-import", daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    launch()

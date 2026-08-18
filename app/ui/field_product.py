"""Production launcher for the Live Pookalam field console."""
from __future__ import annotations

import tkinter as tk

from app.ui.field_experience_console import FieldExperienceConsole
from app.ui.masked_projection import MaskedProjectionWindow


class ProductFieldConsole(FieldExperienceConsole):
    """Approved UI plus production projection masking."""

    def open_projector(self):
        if self.proj is None or not self.proj.win.winfo_exists():
            self.proj = MaskedProjectionWindow(self)
        self.proj.place()


def launch():
    root = tk.Tk()
    ProductFieldConsole(root)
    root.mainloop()

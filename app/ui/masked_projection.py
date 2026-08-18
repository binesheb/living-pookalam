"""Production projector surface with Pookalam-only output masking."""
from __future__ import annotations

import os
from dataclasses import replace

import cv2
import numpy as np
from PIL import ImageTk

from app.rendering.compositor import build_projection_mask, map_contour_to_projector, prepare_digital_layer
from app.ui.field_ui import ProjectionWindow, DrawAdapter
from app.visuals.masking import MaskedDrawAdapter


class MaskedProjectionWindow(ProjectionWindow):
    """Project only the Pookalam layer and masked effects; never a raw rectangle."""

    def render(self, interaction=None, contour=None, pattern=None, image=None):
        self.clear()
        source = self.app.state.get("source", "generated")
        if pattern is None and contour is None:
            return

        if pattern is not None and getattr(pattern, "contour", None) is not None:
            source_shape = (pattern.height, pattern.width, 3)
            H = self.app.H if source in ("physical", "hybrid") else None
            mapped = map_contour_to_projector(pattern.contour, source_shape, (self.w, self.h), H)
        else:
            raw = np.asarray(contour, dtype=np.float32)
            source_shape = self.app.frame.shape if self.app.frame is not None else (720, 1280, 3)
            H = self.app.H if source in ("physical", "hybrid") else None
            mapped = map_contour_to_projector(raw, source_shape, (self.w, self.h), H)

        mask = build_projection_mask(mapped, (self.w, self.h), edge_margin=8)
        if mask is None:
            return

        projected_pattern = None
        if pattern is not None:
            center = np.asarray(pattern.centre, dtype=np.float32).reshape(1, 1, 2)
            if H is not None:
                center = cv2.perspectiveTransform(center, np.asarray(H, dtype=np.float32)).reshape(2)
            else:
                center = np.mean(mapped, axis=0)
            radius = float(np.max(np.linalg.norm(mapped - center.reshape(1, 2), axis=1)))
            projected_pattern = replace(pattern, width=self.w, height=self.h,
                                        centre=(float(center[0]), float(center[1])),
                                        radius=radius, contour=mapped)

        # Physical/hybrid: never synthesize a second Pookalam over the flowers.
        # Digital: display only the detected Pookalam pixels using alpha masking.
        if source == "digital":
            digital = image
            if digital is None:
                path = self.app.state.get("image", "")
                if path and os.path.exists(path):
                    digital = cv2.imread(path)
            if digital is None or pattern is None or pattern.contour is None:
                return
            prepared = prepare_digital_layer(digital, pattern.contour, (self.w, self.h))
            if prepared is not None:
                layer, centre = prepared
                self.base_photo = ImageTk.PhotoImage(layer)
                self.canvas.create_image(centre[0], centre[1], image=self.base_photo)

        old_base = self.app.engine.effects.get("base", False)
        self.app.engine.effects["base"] = source == "generated"
        try:
            self.app.engine.render(MaskedDrawAdapter(DrawAdapter(self.canvas), mask), self.w, self.h,
                                   interaction=interaction, pattern=projected_pattern)
        finally:
            self.app.engine.effects["base"] = old_base

        if self.app.dev_mode and mapped is not None:
            pts = [(float(x), float(y)) for x, y in mapped.reshape(-1, 2)]
            if len(pts) >= 2:
                self.canvas.create_line(*[v for p in pts for v in p], fill="#8b35ff", width=4, smooth=True)
            self.canvas.create_text(36, 32, text="DEV • MASKED POOKALAM OUTPUT",
                                    anchor="nw", fill="#8b35ff", font=("Segoe UI", 18, "bold"))

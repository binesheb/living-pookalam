"""Projection surface with Pookalam-only output masking."""
from __future__ import annotations

from types import SimpleNamespace
import cv2
import numpy as np

from app.ui.field_ui import ProjectionWindow, DrawAdapter
from app.visuals.masking import ProjectionMask, MaskedDrawAdapter


class MaskedProjectionWindow(ProjectionWindow):
    """Project only effect pixels that belong to the Pookalam footprint."""

    def _project_pattern(self, pattern):
        if pattern is None or getattr(pattern, "contour", None) is None:
            return None, None
        contour = np.asarray(pattern.contour, dtype=np.float32).reshape(-1, 1, 2)
        src_w, src_h = float(max(1, pattern.width)), float(max(1, pattern.height))
        if self.app.H is not None:
            mapped = cv2.perspectiveTransform(contour, self.app.H).reshape(-1, 2)
        else:
            mapped = contour.reshape(-1, 2).copy()
            mapped[:, 0] = mapped[:, 0] / src_w * self.w
            mapped[:, 1] = mapped[:, 1] / src_h * self.h
        mapped[:, 0] = mapped[:, 0] * self.w / max(1, self.app.state.get("projector_width", self.w))
        mapped[:, 1] = mapped[:, 1] * self.h / max(1, self.app.state.get("projector_height", self.h))
        mapped_contour = mapped.astype(np.float32).reshape(-1, 1, 2)
        center = np.asarray([pattern.centre], dtype=np.float32).reshape(-1, 1, 2)
        if self.app.H is not None:
            center = cv2.perspectiveTransform(center, self.app.H).reshape(2)
            center[0] *= self.w / max(1, self.app.state.get("projector_width", self.w))
            center[1] *= self.h / max(1, self.app.state.get("projector_height", self.h))
        else:
            center = center.reshape(2)
            center[0] = center[0] / src_w * self.w
            center[1] = center[1] / src_h * self.h
        radius = float(max(np.linalg.norm(mapped - center.reshape(1, 2), axis=1)))
        original_radius = max(1.0, float(getattr(pattern, "radius", 1.0)))
        rings = tuple(float(r) / original_radius * radius for r in getattr(pattern, "rings", ()))
        projected = SimpleNamespace(
            width=self.w,
            height=self.h,
            centre=(float(center[0]), float(center[1])),
            radius=radius,
            contour=mapped_contour,
            rings=rings,
        )
        return projected, mapped_contour

    def render(self, interaction=None, contour=None, pattern=None, image=None):
        self.clear()
        projected_pattern, mapped_contour = self._project_pattern(pattern)
        if mapped_contour is None and contour is not None:
            raw = np.asarray(contour, dtype=np.float32).reshape(-1, 1, 2)
            if self.app.H is not None:
                mapped_contour = cv2.perspectiveTransform(raw, self.app.H)
            else:
                mapped_contour = raw.copy()
                if self.app.frame is not None:
                    h, w = self.app.frame.shape[:2]
                    mapped_contour[:, 0, 0] = mapped_contour[:, 0, 0] / max(1, w) * self.w
                    mapped_contour[:, 0, 1] = mapped_contour[:, 0, 1] / max(1, h) * self.h
            projected_pattern = SimpleNamespace(
                width=self.w, height=self.h,
                centre=(self.w / 2, self.h / 2),
                radius=min(self.w, self.h) * .38,
                contour=mapped_contour,
                rings=(),
            )
        mask = ProjectionMask(mapped_contour, self.w, self.h, edge_margin=12) if mapped_contour is not None else None
        draw = DrawAdapter(self.canvas)
        safe_draw = MaskedDrawAdapter(draw, mask) if mask is not None else draw
        self.app.engine.render(safe_draw, self.w, self.h,
                               interaction=interaction, pattern=projected_pattern, mask=mask)
        if self.app.dev_mode and mapped_contour is not None:
            pts = mapped_contour.reshape(-1, 2)
            self.canvas.create_line(*[v for p in [(float(x), float(y)) for x, y in pts] for v in p],
                                    fill="#8b35ff", width=4, smooth=True)
            self.canvas.create_text(36, 32, text="DEV • MASKED POOKALAM OUTPUT",
                                    anchor="nw", fill="#8b35ff",
                                    font=("Segoe UI", 18, "bold"))

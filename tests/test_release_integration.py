import inspect

from app.ui.masked_projection import MaskedProjectionWindow
from app.visuals.masking import ProjectionMask


def test_production_projection_signature_matches_visual_engine():
    params = inspect.signature(MaskedProjectionWindow.render).parameters
    assert "mask" not in params
    assert "pattern" in params
    assert "interaction" in params


def test_mask_rejects_outside_and_allows_narrow_edge_band():
    import numpy as np

    contour = np.array([[[10, 10]], [[90, 10]], [[90, 90]], [[10, 90]]], dtype=np.float32)
    mask = ProjectionMask(contour, 100, 100, edge_margin=8)
    assert not mask.inside(5, 50)
    assert mask.inside(50, 50)
    assert mask.inside(10, 50, edge=True)
    assert not mask.inside(50, 50, radius=45)

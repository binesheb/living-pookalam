import numpy as np

from app.visuals.masking import ProjectionMask


def square():
    return np.array([[[10, 10]], [[90, 10]], [[90, 90]], [[10, 90]]], dtype=np.float32)


def test_projection_mask_rejects_outside_points():
    mask = ProjectionMask(square(), 100, 100)
    assert mask.inside(50, 50)
    assert not mask.inside(2, 50)


def test_projection_mask_keeps_large_effects_inside_only():
    mask = ProjectionMask(square(), 100, 100)
    assert mask.inside(50, 50, radius=20)
    assert not mask.inside(15, 50, radius=20)


def test_projection_mask_allows_narrow_edge_band():
    mask = ProjectionMask(square(), 100, 100, edge_margin=10)
    assert mask.inside(7, 50, edge=True)
    assert not mask.inside(-5, 50, edge=True)

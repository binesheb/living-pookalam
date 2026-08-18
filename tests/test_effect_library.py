from app.visuals.effect_library import CATEGORIES, EFFECTS, PRESETS, EFFECT_INDEX, effects_by_category
from app.visuals.engine import VisualEngine


def test_effect_catalog_is_categorized_and_unique():
    ids = [e.id for e in EFFECTS]
    assert len(ids) == len(set(ids))
    assert set(CATEGORIES) == set(e.category for e in EFFECTS)
    assert set(EFFECT_INDEX) == set(ids)


def test_presets_reference_known_effects():
    for effects in PRESETS.values():
        assert effects
        assert all(effect_id in EFFECT_INDEX for effect_id in effects)


def test_engine_supports_pattern_effects():
    engine = VisualEngine()
    engine.apply_preset(PRESETS["MAGIC_TOUCH"])
    assert engine.effects["edge_pulse"]
    assert engine.effects["touch_burst"]
    assert engine.effects["touch_trail"]

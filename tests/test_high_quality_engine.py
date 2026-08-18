from app.visuals.engine import VisualEngine, Interaction
from app.visuals.effect_library import EFFECTS, PRESETS


def test_1080p_engine_has_bounded_effect_catalog():
    engine = VisualEngine()
    assert len(engine.EFFECTS) >= 40
    assert engine.max_particles <= 1000


def test_catalog_effects_exist_in_engine():
    engine = VisualEngine()
    for spec in EFFECTS:
        assert spec.id in engine.effects, spec.id


def test_all_presets_reference_existing_effects():
    engine = VisualEngine()
    for preset in PRESETS.values():
        for effect_id in preset:
            assert effect_id in engine.effects, effect_id


def test_engine_renders_without_interaction():
    class Draw:
        def circle(self,*a,**k): pass
        def line(self,*a,**k): pass
        def polygon(self,*a,**k): pass
    VisualEngine().render(Draw(), 1920, 1080, interaction=Interaction())

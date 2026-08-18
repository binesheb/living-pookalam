"""Effect catalog for the Live Pookalam compositor.

The catalog is data-first so the UI can expose effects like a modern video
editor without hard-coding the operator workflow into the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EffectSpec:
    id: str
    name: str
    category: str
    description: str
    parameters: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ("always", "approach", "touch", "move")


CATEGORIES = (
    "EDGE FX", "RADIAL", "FLOWER", "PARTICLES", "LIGHT", "LIQUID",
    "ENERGY", "ONAM", "INTERACTION", "TRANSITIONS"
)


def _spec(id: str, name: str, category: str, description: str, parameters=("intensity", "speed", "size")) -> EffectSpec:
    return EffectSpec(id, name, category, description, tuple(parameters))


EFFECTS: tuple[EffectSpec, ...] = (
    _spec("edge_glow", "Neon Edge", "EDGE FX", "Soft luminous contour around the detected Pookalam."),
    _spec("edge_trace", "Moving Edge Trace", "EDGE FX", "A travelling highlight follows the real contour."),
    _spec("edge_electric", "Electric Edge", "EDGE FX", "Animated broken electrical energy along the contour."),
    _spec("edge_particles", "Edge Particles", "EDGE FX", "Particles travel along detected edges."),
    _spec("edge_draw", "Edge Draw", "EDGE FX", "Progressively reveals the detected contour."),
    _spec("edge_pulse", "Edge Pulse", "EDGE FX", "A pulse chases around the Pookalam boundary."),
    _spec("radial_wave", "Radial Wave", "RADIAL", "Concentric wave travelling from the Pookalam centre."),
    _spec("ring_pulse", "Ring Pulse", "RADIAL", "Individual detected rings pulse independently."),
    _spec("spiral", "Spiral", "RADIAL", "Rotating spiral light through the pattern."),
    _spec("radial_rays", "Light Rays", "RADIAL", "Soft rays expand from the centre."),
    _spec("flower_bloom", "Flower Bloom", "FLOWER", "Flower regions appear to bloom outward."),
    _spec("petal_drift", "Petal Drift", "FLOWER", "Petal-like particles drift from the pattern."),
    _spec("petal_shimmer", "Petal Shimmer", "FLOWER", "Moving highlights sweep across flower regions."),
    _spec("fireflies", "Fireflies", "PARTICLES", "Warm particles orbit the Pookalam."),
    _spec("gold_dust", "Golden Dust", "PARTICLES", "Fine gold particles rise and scatter."),
    _spec("sparkle", "Sparkle", "PARTICLES", "Short-lived star-like highlights."),
    _spec("bloom", "Soft Glow", "LIGHT", "Ambient bloom around the detected geometry."),
    _spec("light_sweep", "Light Sweep", "LIGHT", "A moving band of light crosses the pattern."),
    _spec("golden_shimmer", "Golden Shimmer", "ONAM", "Warm festival shimmer constrained to the Pookalam."),
    _spec("deepam", "Deepam Glow", "ONAM", "Lamp-like warm halo and breathing light."),
    _spec("flower_shower", "Flower Shower", "ONAM", "Gentle falling floral particles."),
    _spec("water_ripple", "Water Ripple", "LIQUID", "Soft ripple rings from an interaction point."),
    _spec("liquid_edge", "Liquid Edge", "LIQUID", "Flowing highlight follows the contour."),
    _spec("energy_ring", "Energy Ring", "ENERGY", "Bright energy ring around an interaction point."),
    _spec("shockwave", "Shockwave", "ENERGY", "Fast expanding interaction wave."),
    _spec("touch_burst", "Touch Burst", "INTERACTION", "Burst exactly where a hand approaches the Pookalam."),
    _spec("touch_trail", "Touch Trail", "INTERACTION", "Leaves a fading light trail behind movement."),
    _spec("region_react", "Region React", "INTERACTION", "Triggers the detected region nearest the user."),
    _spec("reveal", "Pattern Reveal", "TRANSITIONS", "Reveals the Pookalam from centre or edge."),
    _spec("dissolve", "Particle Dissolve", "TRANSITIONS", "Dissolves the pattern into particles."),
)

EFFECT_INDEX = {e.id: e for e in EFFECTS}

PRESETS = {
    "ONAM_GOLD": ("golden_shimmer", "edge_glow", "radial_wave", "fireflies", "deepam"),
    "LIVING_FLOWER": ("flower_bloom", "petal_drift", "edge_trace", "sparkle"),
    "MAGIC_TOUCH": ("edge_pulse", "touch_burst", "water_ripple", "touch_trail", "energy_ring"),
    "REVEAL": ("reveal", "edge_draw", "gold_dust", "radial_rays"),
}


def effects_by_category() -> dict[str, tuple[EffectSpec, ...]]:
    return {category: tuple(e for e in EFFECTS if e.category == category) for category in CATEGORIES}


def preset(name: str) -> tuple[str, ...]:
    return PRESETS.get(name, ())

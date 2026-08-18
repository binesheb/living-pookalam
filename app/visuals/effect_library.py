"""Production effect catalog for Live Pookalam 1080p projection."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EffectSpec:
    id: str
    name: str
    category: str
    description: str
    parameters: tuple[str, ...] = ("intensity", "speed", "size")
    triggers: tuple[str, ...] = ("always", "approach", "touch", "move")

def _spec(id, name, category, description, parameters=("intensity", "speed", "size"), triggers=("always", "approach", "touch", "move")):
    return EffectSpec(id, name, category, description, tuple(parameters), tuple(triggers))

CATEGORIES = ("EDGE FX", "RADIAL", "FLOWER", "PARTICLES", "LIGHT", "LIQUID", "ENERGY", "ONAM", "INTERACTION", "TRANSITIONS")
EFFECTS = (
    _spec("edge_glow","Neon Edge","EDGE FX","Soft luminous contour around the real Pookalam."),
    _spec("edge_trace","Moving Edge Trace","EDGE FX","Travelling highlight follows the detected boundary."),
    _spec("edge_electric","Electric Edge","EDGE FX","Animated electrical energy follows the contour."),
    _spec("edge_particles","Edge Particles","EDGE FX","Particles travel around the boundary."),
    _spec("edge_draw","Edge Draw","EDGE FX","Progressively draws the Pookalam boundary."),
    _spec("edge_pulse","Edge Pulse","EDGE FX","Repeating pulse travels around the edge."),
    _spec("edge_spark","Edge Spark","EDGE FX","Fine sparks flash at moving edge points."),
    _spec("liquid_edge","Liquid Edge","LIQUID","Flowing blue highlight around the contour."),
    _spec("radial_wave","Radial Wave","RADIAL","Concentric waves expand from the centre."),
    _spec("ring_pulse","Ring Pulse","RADIAL","Detected rings pulse independently."),
    _spec("spiral","Spiral","RADIAL","Rotating golden spiral through the geometry."),
    _spec("radial_rays","Light Rays","RADIAL","Soft festival rays radiate from the centre."),
    _spec("mandala_spin","Mandala Spin","RADIAL","Slow rotating mandala-style light geometry."),
    _spec("color_wave","Colour Wave","RADIAL","Warm colour pulse travels through concentric rings."),
    _spec("flower_bloom","Flower Bloom","FLOWER","Layered flower petals bloom from the centre."),
    _spec("lotus_bloom","Lotus Bloom","FLOWER","Central lotus opens and breathes."),
    _spec("petal_drift","Petal Drift","FLOWER","Petal particles drift gently across the pattern."),
    _spec("petal_flow","Petal Flow","FLOWER","Continuous controlled petal movement."),
    _spec("petal_shimmer","Petal Shimmer","FLOWER","Soft moving highlights on floral regions."),
    _spec("petal_burst","Petal Burst","FLOWER","Petals burst outward from interaction."),
    _spec("fireflies","Fireflies","PARTICLES","Warm floating points orbit the Pookalam."),
    _spec("gold_dust","Golden Dust","PARTICLES","Fine golden particles rise through the pattern."),
    _spec("sparkle","Sparkle","PARTICLES","Small star-like festival highlights."),
    _spec("starfield","Starfield","PARTICLES","Dense but bounded micro-stars create depth."),
    _spec("golden_rain","Golden Rain","PARTICLES","Elegant falling gold particles."),
    _spec("bloom","Soft Glow","LIGHT","Ambient luminous bloom."),
    _spec("breathing_glow","Breathing Glow","LIGHT","Slow breathing illumination."),
    _spec("light_sweep","Light Sweep","LIGHT","Moving festival light sweeps across the form."),
    _spec("golden_shimmer","Golden Shimmer","ONAM","Warm Kerala-festival shimmer."),
    _spec("deepam","Deepam Glow","ONAM","Deepam-inspired warm centre glow."),
    _spec("flower_shower","Flower Shower","ONAM","Gentle falling flower-like particles."),
    _spec("aurora","Onam Aurora","ONAM","Subtle cyan-gold atmospheric light."),
    _spec("heartbeat","Heartbeat","ENERGY","Slow breathing pulse around the Pookalam."),
    _spec("center_beacon","Centre Beacon","ENERGY","Bright controlled centre focus."),
    _spec("magic_ring","Magic Ring","ENERGY","Elegant rotating energy ring."),
    _spec("energy_ring","Energy Ring","ENERGY","Bright ring around an interaction point."),
    _spec("shockwave","Shockwave","ENERGY","Fast expanding interaction wave."),
    _spec("water_ripple","Water Ripple","LIQUID","Soft water-like interaction ripples."),
    _spec("touch_burst","Touch Burst","INTERACTION","Burst appears at the detected user point."),
    _spec("touch_trail","Touch Trail","INTERACTION","Fading trail follows movement."),
    _spec("interaction_ripple","Interaction Ripple","INTERACTION","Ripple responds to proximity/touch."),
    _spec("interaction_spark","Interaction Sparks","INTERACTION","Fine sparks respond to interaction."),
    _spec("region_react","Region React","INTERACTION","Nearest detected region becomes active."),
    _spec("reveal","Pattern Reveal","TRANSITIONS","Reveals the visual experience progressively."),
    _spec("dissolve","Particle Dissolve","TRANSITIONS","Dissolves the pattern into particles."),
)
EFFECT_INDEX={e.id:e for e in EFFECTS}
PRESETS={
    "ONAM_GOLD": ("base","golden_shimmer","edge_glow","radial_wave","fireflies","deepam","gold_dust"),
    "LIVING_FLOWER": ("base","flower_bloom","lotus_bloom","petal_drift","petal_shimmer","edge_trace","sparkle"),
    "MAGIC_TOUCH": ("base","edge_pulse","touch_burst","water_ripple","touch_trail","energy_ring","center_beacon"),
    "REVEAL": ("base","reveal","edge_draw","gold_dust","radial_rays","flower_bloom"),
    "MAHABALI_GLOW": ("base","golden_shimmer","deepam","aurora","heartbeat","edge_glow"),
    "TEMPLE_LIGHT": ("base","radial_rays","ring_pulse","deepam","center_beacon","golden_shimmer"),
    "FLOWER_SHOWER": ("base","flower_shower","petal_flow","gold_dust","edge_glow"),
    "MAGIC_MANDALA": ("base","mandala_spin","radial_wave","ring_pulse","sparkle","edge_trace"),
    "WATER_MAGIC": ("base","water_ripple","liquid_edge","radial_wave","aurora","touch_trail"),
}
def effects_by_category(): return {category:tuple(e for e in EFFECTS if e.category==category) for category in CATEGORIES}
def preset(name): return PRESETS.get(name,())

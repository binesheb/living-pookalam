# LIVE POOKALAM

**Interactive Projection Experience for Onam**  
**developed by bnsh.eb**

Live Pookalam is a reusable Windows 11 platform that turns a physical Pookalam, a digital Pookalam, or both into an interactive projection canvas. It is designed to be installed repeatedly across showrooms without changing the application core.

## Operator workflow

```text
HOME
  ↓
SOURCE
  ↓
CALIBRATE
  ↓
ANALYSE
  ↓
DETECT
  ↓
EFFECTS
  ↓
RUN SHOW
```

**Developer Mode** exposes the real camera segmentation/edge geometry on the projector. Calibration can be rerun at any time when the camera or projector moves.

## Windows 11

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.ui
```

Or launch `run_windows.bat`.

## Sources

### Digital
Upload a Pookalam image. The pattern analyzer extracts a usable boundary, centre, radial rings, dominant colours, edges and symmetry so effects can be previewed without a physical installation.

### Physical
The webcam observes the real flower Pookalam. The deterministic vision layer derives a contour/mask and geometry from the live feed.

### Hybrid
The physical flowers remain visible while the projector adds effects over the real geometry.

## Calibration

Calibration is an automated, repeatable camera → projector mapping sequence. Only the currently projected, uniquely coloured target is valid, reducing false locks from wallpaper or room content. A new mapping is accepted only after stable observations and validation; the previous mapping remains available until a valid replacement exists.

Move the projector or webcam? Press **CALIBRATE** and run the sequence again. No application restart is required.

## Pattern analysis

The `Analyse` stage produces a deterministic `PatternAnalysis` model containing:

- boundary/contour
- edge map
- centre
- radius
- concentric ring geometry
- dominant colours
- approximate radial symmetry order
- confidence

The analyzer intentionally does not require semantic AI recognition of every flower. Geometry remains reliable even when flower-level classification is uncertain.

## Living Effects

The effect engine is data-driven and pattern-aware. It is designed around the interaction model of modern editors such as VN/CapCut while remaining specific to Pookalam projection.

### Edge FX

- Neon Edge
- Moving Edge Trace
- Electric Edge
- Edge Particles
- Edge Draw
- Edge Pulse
- Liquid Edge

### Radial

- Radial Wave
- Ring Pulse
- Spiral
- Light Rays

### Flower / Particles

- Flower Bloom
- Petal Drift
- Petal Shimmer
- Fireflies
- Golden Dust
- Sparkle

### Light / Festival

- Soft Glow
- Light Sweep
- Golden Shimmer
- Deepam Glow
- Flower Shower

### Liquid / Energy

- Water Ripple
- Energy Ring
- Shockwave

### Interaction

- Touch Burst
- Touch Trail
- Region React

### Transitions

- Pattern Reveal
- Particle Dissolve

Presets currently include **ONAM GOLD**, **LIVING FLOWER**, **MAGIC TOUCH** and **REVEAL**.

Every effect is a layer. Parameters such as intensity and speed can be changed without changing the underlying calibration or vision model.

## Developer Mode

Developer Mode is intended for installation and experimentation. It can show:

- live camera feed
- detected Pookalam contour
- centre/geometry
- calibration diagnostics
- projected real edge
- effect previews

The interaction behavior is intentionally not hard-coded to a single gesture. This allows the final Onam interaction design to be decided after real-world tracking tests.

## Showroom replication

One application core is shared across all installations. Hardware and content belong in installation profiles:

```text
app/                       shared application logic
profiles/template/         reference installation
profiles/showrooms/<id>/  showroom-specific calibration/content
```

A showroom should not require a code fork.

## Production roadmap

- robust marker calibration and lens correction
- floor-plane rectification
- editable Pookalam region masks
- flower/motif semantic recognition
- GPU compositor for high-resolution projection
- hand/gesture tracking
- multiple-person interaction
- scene/timeline editor
- audio-reactive effects
- Onam/Mahabali scene library
- packaged Windows EXE
- watchdog and recovery
- showroom profile editor
- remote update/deployment

## Project identity

**LIVE POOKALAM**  
Interactive Projection Experience  
**developed by bnsh.eb**

## License

MIT. See `LICENSE`.

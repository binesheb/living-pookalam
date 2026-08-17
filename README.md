# LIVE POOKALAM

**Interactive Projection Experience for Onam**

**developed by bnsh.eb**

Living Pookalam is a reusable Windows 11 platform that turns a physical Pookalam, a digital Pookalam, or both into an interactive projection experience. It is designed to be installed repeatedly across showrooms without changing the application core.

## Design philosophy

The operator should not need to understand computer vision, homography, rendering or Python.

The application therefore follows a guided workflow:

```text
HOME
  ↓
SOURCE
  ↓
CALIBRATE (when installation is ready)
  ↓
DETECT / LOCK POOKALAM
  ↓
EXPERIENCE
  ↓
RUN SHOW
```

Calibration is deliberately optional during development. The visual experience can be tested on a projector before the physical installation is ready.

## Windows 11 test

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.ui
```

Or use `run_windows.bat`.

## Modes

### Digital
Upload a Pookalam image and use it as the base visual surface. This is the fastest way to develop and test effects without a physical flower arrangement.

### Physical
The webcam observes the real floor Pookalam. The vision layer detects its usable contour and derives geometry for interaction and effects.

### Hybrid
The real flower Pookalam remains visible while projected light, particles, glows, waves and other effects are layered over it.

## Calibration model

The first hardware implementation uses a planar camera → projector homography.

1. Extend Windows to the projector.
2. Start Live Pookalam.
3. Open **CALIBRATE**.
4. The projector displays four targets.
5. The webcam detects their camera coordinates.
6. The application computes the homography.
7. The installation mapping is saved locally.

Because both devices observe the same floor plane, the camera can be mounted at an angle. Future production calibration will add stronger marker detection, lens correction, confidence/error reporting and manual adjustment.

## Pookalam perception

The Pookalam is represented as a contour/mask rather than assuming a perfect circle. This is important when the webcam is placed to the side and the Pookalam appears as an ellipse or perspective-distorted shape.

Planned perception layers include:

- floor rectification
- colour/chroma segmentation
- boundary and contour locking
- centre/radial geometry
- ring/region analysis
- symmetry analysis
- feature/motif detection
- person tracking
- multiple-person interaction
- optional AI semantic recognition

## Experience engine

The renderer is built from independent effect layers so an operator can compose an experience without changing code.

Current layers include:

- base Pookalam
- breathing glow
- radial waves
- petal flow
- fireflies
- lotus bloom
- interaction ripple
- interaction sparks
- spiral light
- colour pulse

The architecture is intentionally open for future Onam scenes, Mahabali sequences, butterflies, lamps, flower motion, water/light waves, audio-reactive effects, timelines and scripted scenes.

## Operator workflow

### HOME
Hardware health, showroom profile, calibration state and quick-start actions.

### SOURCE
Choose Digital, Physical or Hybrid.

### CALIBRATE
Projector/camera mapping. Can be skipped during early development.

### DETECT
Find and lock the actual Pookalam. Detection is assisted; the contour is the primary geometry.

### EXPERIENCE
Enable/disable individual effect layers.

### RUN SHOW
Safe show control. `ESC` stops the experience.

## Showroom replication

One core application is deployed everywhere.

```text
app/                       shared application logic
profiles/template/         reference installation
profiles/showrooms/<id>/  showroom-specific hardware/calibration/content
```

A new showroom should never require a code fork. Camera index, projector display, physical dimensions, calibration, zones and local content belong in the showroom profile.

## Production roadmap

- robust ArUco calibration
- camera lens correction
- floor-plane rectification
- editable Pookalam mask
- Pookalam feature/region map
- GPU renderer
- multi-person tracking
- hand/gesture tracking
- scene/timeline editor
- audio-reactive experience
- Onam/Mahabali scene library
- packaged Windows EXE
- automatic startup/recovery
- watchdog and failsafe
- showroom profile editor
- installation diagnostics
- remote deployment/update support

## Project identity

**LIVE POOKALAM**  
Interactive Projection Experience  
**developed by bnsh.eb**

## License

MIT. See `LICENSE`.

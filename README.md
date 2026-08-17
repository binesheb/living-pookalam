# Living Pookalam

A reusable, showroom-deployable interactive Pookalam platform for **Windows 11**.

Living Pookalam turns a physical floral/visual installation into an interactive projection experience using a webcam, projector, local computer and configurable content. The same software core is deployed to multiple showrooms through independent profiles.

## Current Windows hardware-test build

The repository now contains a functional desktop operator application.

```text
Windows 11 PC
    |
    +-- USB webcam
    |
    +-- HDMI / DisplayPort projector
    |
    +-- Living Pookalam Operator
             |
             +-- 4-point projector calibration
             +-- digital Pookalam image
             +-- physical Pookalam detection
             +-- hybrid mode
             +-- interaction test
             +-- live projector output
```

### Start the Windows application

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.ui
```

Or double-click `run_windows.bat`.

## Calibration model

The first hardware build uses a **direct camera-to-projector homography** for the planar floor.

1. Extend Windows display to the projector.
2. Open Living Pookalam.
3. Press **PROJECTOR TEST** to verify output.
4. Press **4-POINT CALIBRATE**.
5. The projector displays four numbered targets.
6. The webcam detects the four targets.
7. The software calculates the camera -> projector homography.
8. The mapping is saved to `installation_profile.json`.

This works even when the webcam is mounted at an angle because both camera and projector are observing the same approximately planar floor.

## Physical Pookalam

The detector does not assume the camera sees a perfect circle. The camera image is segmented by colour/chroma and the largest plausible compact region is used as the initial Pookalam contour. The contour is the primary geometry; centre/radius are derived values.

The detection is intentionally **assisted** for this first physical test. The production vision layer will add stronger floor rectification, confidence scoring, manual contour correction and AI person/object tracking.

## Interaction

After calibration, **INTERACTION TEST** enables webcam motion detection. A detected person/body region is mapped through the camera-to-projector homography and used to drive a visible ring/particle effect.

This is the first end-to-end hardware proof: **camera -> mapping -> interaction -> projector**.

## Digital / physical / hybrid

- **Digital:** upload a Pookalam image and use it as the projected base.
- **Physical:** use the actual flower Pookalam as the physical surface.
- **Hybrid:** combine a real Pookalam with uploaded digital artwork/effects.

## Core principle

**One application. Many showroom profiles.**

A showroom must never require a code fork. Physical dimensions, camera calibration, projector mapping, zones, content and local hardware settings belong in `profiles/`, while application logic stays in `app/`.

## Repository layout

```text
app/
  api/             Local control and health API
  core/            Configuration and application lifecycle
  experience/      Scenes, zones and experience state
  hardware/        Hardware adapters
  interaction/     Input-to-action rules
  perception/      Camera/sensor processing
  rendering/       Output abstraction
  ui/              Windows operator application
profiles/
  template/        Copy this for a new showroom
  showrooms/       Deployment-specific profiles
tests/             Automated tests
tools/             Calibration and diagnostics
docs/              Architecture and deployment docs
run_windows.bat    Windows one-click launcher
```

## Replicating a showroom

1. Copy `profiles/template` to `profiles/showrooms/<id>`.
2. Enter physical dimensions and hardware identifiers.
3. Run projector/camera calibration at that showroom.
4. Store calibration output in the showroom profile.
5. Deploy the same application release.
6. Validate health, camera input, rendering and interaction.

## Development status

The project is being built in layers. The current build is suitable for **initial Windows 11 hardware testing**, not yet the final Onam production release.

Next production layers include:

- robust floor-plane calibration
- projector lens/distortion compensation
- Pookalam contour/mask locking
- manual contour correction
- GPU visual renderer
- richer particle/flower effects
- person tracking and multiple-person interaction
- scene/timeline engine
- audio synchronization
- packaged Windows executable
- showroom profile editor
- installation diagnostics
- recovery/failsafe handling

## License

MIT. See `LICENSE`.

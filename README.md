# Living Pookalam

Living Pookalam projects a reference Pookalam image onto a calibrated floor and uses a live camera to understand activity inside the projection.

## Version 2.1

- Upload a high-quality reference image
- Manual crop before projection
- The reference image is retained as the source for future pattern and effect generation
- Projector output is restricted to the Windows extended display
- Two-stage calibration: projector field, then designated floor area
- Perspective correction and warped floor projection
- Motion detection across the full projected area
- Rectified detailed analysis inside the designated floor area
- Normalized object coordinates for the interactive effect engine
- Live camera debug windows automatically appear while projection is active
- Manual Update from GitHub
- Startup performs one controlled `git pull --ff-only`

## Controls

- **Select & Crop** — load the reference Pookalam image.
- **Calibrate** — mark projector field and physical floor area.
- **Start Projection** — projects to the extended display and opens live camera debug windows on the main display.
- **Stop Projection** — stops projector output and camera analysis.
- **Close App** — terminates the application and closes OpenCV windows.
- **Update from GitHub** — manually pulls the latest changes.

## Start

```bat
run_windows.bat
```

Requirements: Python 3, Git, camera, and projector configured in Windows **Extend** mode.

## Data model

The designated floor is normalized to `(0,0)` through `(1,1)`. Interactive effects should use this coordinate system rather than raw camera pixels.

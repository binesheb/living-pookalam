# Living Pookalam

Living Pookalam projects artwork onto a calibrated floor area and provides the foundation for interactive camera-driven effects.

## Version 2 foundation

- Image upload and manual crop
- Projector always uses the Windows extended display
- Two-stage calibration:
  1. mark the full projector field in the camera image
  2. mark the designated physical floor area inside it
- Perspective correction from the camera-observed quadrilateral to normalized floor coordinates
- Warped projector output
- Motion detection across the complete projector field
- Detailed rectified analysis inside the designated floor area
- Contour position and normalized interaction coordinates
- Vision Debug windows for validating camera understanding
- Manual `Update from GitHub` button
- Startup performs one `git pull --ff-only`; the application itself never pulls or restarts recursively

## Start

On Windows:

```bat
run_windows.bat
```

Requirements: Python 3, Git, a camera, and a projector configured in **Windows Extend** mode.

## Workflow

1. Select and crop an image.
2. Calibrate the projector field and floor boundary.
3. Use **Vision Debug** to verify global motion and rectified floor analysis.
4. Use **Project** to send the warped image only to the extended projector display.

Press `Esc` or `Q` to close OpenCV projection or debug windows.

## Interaction data

The floor is normalized to coordinates from `(0,0)` to `(1,1)`. Future interactive effects should consume this normalized coordinate space rather than raw camera pixels.

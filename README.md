# Living Pookalam

Windows desktop application for perspective-correct image projection onto a calibrated floor area.

## Start

Run `run_windows.bat`.

The launcher performs exactly one `git pull --ff-only` before starting the application, then creates/uses `.venv`, installs dependencies, and launches `main.py`. The running application never performs `git pull` and never restarts itself for updates.

## Workflow

1. Select and crop an image.
2. Calibrate using the webcam.
3. Mark the four corners of the projector field.
4. Mark the four corners of the physical floor boundary inside that field.
5. Project the warped image to the Windows extended display.

The main display is used for the GUI and camera calibration. Projector output is intended for the extended display.

## Version

Current release: 1.0.2

# Live Pookalam — Field Readiness

## Approved scope

The product must support reliable floor projection from a side-mounted camera/projector on Windows 11, with 1920x1080 as the baseline and resolution-independent rendering for future projectors.

## Installation sequence

1. Detect camera and projector.
2. Lock camera exposure, white balance and focus where the driver permits.
3. Run automated four-target geometric calibration.
4. Run colour reference calibration.
5. Detect/confirm the physical or digital Pookalam.
6. Build the projector-space mask with safety margin and feathering.
7. Validate reprojection error, coverage, colour confidence, FPS and output resolution.
8. Save a versioned installation profile without deleting the previous known-good profile.
9. Lock installation.
10. Run the show.

## Recalibration rules

- **Recalibrate**: camera/projector position changed.
- **Re-detect**: Pookalam geometry changed but the camera/projector relationship did not.
- A failed calibration must never replace a known-good profile.
- A new profile becomes active only after validation passes.

## Projection safety

- The normal compositor outputs black/transparent outside the Pookalam mask.
- Edge effects use a controlled edge band.
- Developer diagnostics may intentionally draw outside the production mask.
- Emergency Black must be available from every operator screen.

## Reliability

The show must remain offline-capable after installation. Camera/projector reconnects should recover without restarting the whole application. If a critical subsystem cannot recover, fail safely to black output.

## Performance

Baseline: 1920x1080 @ 60 FPS. Decorative quality must degrade before the base Pookalam projection is compromised.

## Final-day operator workflow

`POWER ON → START → HARDWARE CHECK → LOAD VALID PROFILE → READY → RUN SHOW`

If equipment was moved: `CALIBRATE → VALIDATE → RUN SHOW`.

## Certification gate

The software is not considered field-certified until the actual Windows 11 machine, projector, webcam, floor surface and Pookalam pass the complete hardware checklist.

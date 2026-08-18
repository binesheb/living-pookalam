# LIVE POOKALAM 1.0.0-rc1

## Release status

**Field Release Candidate 1** — Windows 11.

This release consolidates the current calibration, pattern analysis, Pookalam-only projection masking, Living Effects and operator workflow.

## Release gates

### Software

- [x] Automated four-target calibration
- [x] Stable-frame target locking
- [x] Reprojection-error validation
- [x] Previous calibration retained on failed recalibration
- [x] Digital Pookalam source is alpha-masked to detected geometry
- [x] Physical effects are rendered only through the projector-space mask
- [x] Developer edge overlay is available
- [x] Pattern analysis and effect library are integrated
- [x] Automated regression tests for calibration, segmentation, pattern analysis, effects and compositor
- [x] Python compile/import gate in CI
- [x] Windows launcher/update workflow retained

### Hardware acceptance still required

The RC is not declared a final production release until it passes on the actual Windows 11 installation PC with the real projector and webcam.

Required field tests:

1. Projector and webcam placed on the same side of the Pookalam.
2. Automated calibration completed from start to finish.
3. Projector moved, calibration rerun, and mapping verified.
4. Physical Pookalam detected without the wallpaper/background becoming the contour.
5. Developer Mode edge overlay lands on the real flower boundary.
6. Effects remain inside the Pookalam and do not expose a rectangular projection area.
7. Digital Pookalam image projects only inside its detected mask.
8. Run Show starts/stops cleanly.
9. Camera disconnect/reconnect does not crash the operator UI.
10. Projector disconnect/reconnect does not corrupt the saved calibration.

## Operator release procedure

```powershell
git pull
.\.venv\Scripts\python.exe -m app.ui
```

Or use the application's **UPDATE & RESTART** action when available.

## Rollback

If a new build fails hardware acceptance, use the last known-good Git commit. Never delete the saved installation profile while troubleshooting; the previous calibration is intentionally preserved across failed recalibration attempts.

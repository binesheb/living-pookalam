# LIVE POOKALAM 1.0.0-rc3

## Release status

**Field Release Candidate 3** — Windows 11.

This release consolidates automated calibration, pattern analysis, Pookalam-only projection masking, Living Effects and the approved operator workflow. RC3 additionally makes the **actual production launcher** use the robust four-target calibration state machine; the demo/legacy calibration path is no longer the release path.

## Release gates

### Software

- [x] Automated four-target calibration
- [x] One active colour target at a time
- [x] Stable-frame target locking
- [x] Reprojection-error validation
- [x] Failed recalibration leaves the previous valid map untouched
- [x] Calibration can be rerun after projector/webcam movement
- [x] Digital Pookalam source is alpha-masked to detected geometry
- [x] Physical/hybrid effects are rendered only through the projector-space mask
- [x] Projector-resolution scaling after calibration
- [x] Developer edge overlay is available
- [x] Pattern analysis and effect library are integrated
- [x] Regression tests for calibration, segmentation, pattern analysis, effects and compositor
- [x] Production UI import gate in CI
- [x] Python compile gate in CI
- [x] Windows launcher/update workflow retained
- [x] Production projector path reviewed separately from preview/demo path

### Hardware acceptance still required

The RC is **not** declared a final production release until it passes on the actual Windows 11 installation PC with the real projector and webcam.

Required field tests:

1. Projector and webcam placed on the same side of the Pookalam.
2. Automated calibration completes without manual point selection.
3. Projector moved, calibration rerun, and mapping verified.
4. Physical Pookalam detected without wallpaper/background becoming the contour.
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

# LIVE POOKALAM — Approved Architecture

## Release direction

Windows 11, 1920×1080 projector, side-mounted projector/webcam, automated repeatable calibration, projector-space masking, pattern-aware effects, interactive effects, simulation and final-day safe mode.

## Pipeline

Camera → perception → PookalamModel → calibration/homography → projector-space mask → effect graph → compositor → 1920×1080 projector.

## Product workflow

HOME → SOURCE → CALIBRATE → ANALYSE → DETECT → EFFECTS → INTERACTION → SHOW.

Developer Mode exposes camera frames, detected contours, masks, calibration diagnostics and performance counters. Normal Show Mode hides development controls.

## Calibration

Calibration is an automated four-target sequence. Each target is uniquely identified, must remain stable across multiple frames, and is accepted only after geometric validation. A failed rerun never replaces the last known-good calibration.

## Rendering rules

- Never intentionally project a visible rectangular content area onto the floor.
- Effects are clipped by the Pookalam projection mask.
- Edge effects may use a small controlled edge band.
- Base physical Pookalam remains visible in Physical/Hybrid mode.
- 1080p is the canonical output resolution.
- Adaptive quality reduces decorative complexity before compromising mapping or base output.

## Effect architecture

Effects are data-driven and target geometry: boundary, edges, centre, rings, regions, colors and interaction zones. Effects are composable and can be arranged into scenes and timelines.

## Field reliability

Camera/projector disconnects, calibration failure, invalid pattern detection and rendering overload must enter a safe state instead of crashing the show. Final Day mode must require a healthy pipeline before starting.

## Testing gate

Unit tests → production import checks → calibration tests → mask tests → renderer/effect tests → Windows hardware test → long-duration soak → release.

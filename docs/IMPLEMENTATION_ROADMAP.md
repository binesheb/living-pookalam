# Live Pookalam — Approved Implementation Roadmap

## Release principle

Build a dependable field installation first. Decorative complexity must never compromise calibration, masking, projection stability, or safe recovery.

## Phase A — Foundation
- Production pipeline contracts
- 1920x1080 output contract
- Runtime quality governor
- Final-day safe-start / safe-stop controller
- Pookalam model shared by vision and effects

## Phase B — Vision
- Automated four-target calibration
- Calibration quality score
- Live camera feed
- Stable target locking
- Recalibration without restarting
- Physical Pookalam contour
- Ring/centre/region analysis
- Colour-aware region extraction

## Phase C — Projection
- Camera-to-projector homography
- Projector-space mask
- Safe edge band
- Feathered mask
- Resolution-aware mapping
- Black outside projection region
- Display reconnect handling

## Phase D — Effects
- Edge FX
- Radial/mandala FX
- Flower FX
- Particle FX
- Light FX
- Liquid FX
- Energy FX
- Onam FX
- Interaction FX
- Transitions
- Effect graph and parameter system

## Phase E — Show Director
- Timeline/scenes
- Presets
- Auto-generated experience
- Welcome / calm / festival / interactive / finale scenes
- Looping
- Crossfades and geometry-aware transitions

## Phase F — Interaction
- Person detection
- Hand/gesture detection
- Approach / hover / touch-confidence states
- Region-aware reactions
- Multi-person interaction
- Interaction cooldown and decay

## Phase G — Simulation
- Virtual camera angle
- Virtual projector geometry
- Pookalam image import
- Effect preview without physical floor
- Repeatable regression scenes

## Phase H — Field Reliability
- Camera disconnect recovery
- Projector disconnect recovery
- Watchdog
- Safe black output
- Crash restart
- Previous calibration preservation
- Update & Restart
- Installation profiles per showroom

## Phase I — Certification
Hardware acceptance is mandatory before final release:

1. Same-side projector + webcam setup.
2. Full automated calibration.
3. Recalibration after movement.
4. Real Pookalam detection under showroom lighting.
5. Edge overlay follows real flowers.
6. No visible rectangular projection field.
7. 1080p output remains stable for an extended show.
8. Camera/projector reconnect tests.
9. Full show start/stop/restart tests.
10. Final-day operator workflow test.

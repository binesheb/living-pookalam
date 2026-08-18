# LIVE POOKALAM 1.1.0-rc1

## High Quality 1080p Effects Release

**Target:** Windows 11 + 1920x1080 projector.

This release makes the new high-quality visual engine the production renderer and expands the effect system for a polished Onam showroom experience.

## New visual capabilities

### Edge FX
- Neon Edge
- Moving Edge Trace
- Electric Edge
- Edge Particles
- Edge Draw
- Edge Pulse
- Edge Spark
- Liquid Edge

### Radial / Mandala
- Radial Wave
- Ring Pulse
- Spiral
- Light Rays
- Mandala Spin
- Colour Wave

### Flower
- Flower Bloom
- Lotus Bloom
- Petal Drift
- Petal Flow
- Petal Shimmer
- Petal Burst

### Particles
- Fireflies
- Golden Dust
- Sparkle
- Starfield
- Golden Rain

### Festival / Onam
- Golden Shimmer
- Deepam Glow
- Flower Shower
- Onam Aurora
- Heartbeat
- Centre Beacon

### Interaction
- Touch Burst
- Touch Trail
- Interaction Ripple
- Interaction Sparks
- Water Ripple
- Energy Ring
- Shockwave

### Presets
- ONAM GOLD
- LIVING FLOWER
- MAGIC TOUCH
- REVEAL
- MAHABALI GLOW
- TEMPLE LIGHT
- FLOWER SHOWER
- MAGIC MANDALA
- WATER MAGIC

## 1080p rendering policy

The production target is **1920x1080**. Effects are deliberately bounded in object count so the Tk projector surface remains responsive on normal Windows installation hardware.

The visual engine remains independent of Tkinter and is consumed through the existing draw adapter. This keeps the compositor replaceable later with a GPU renderer without changing calibration or pattern-analysis APIs.

## Safety / projection rules

- Pookalam-only projection masking remains mandatory.
- Effects outside the approved contour are rejected by the projection mask.
- Failed calibration never overwrites the previous valid calibration.
- Developer edge overlays remain disabled when Developer Mode is disabled.
- A black projector surface is used whenever a valid projection geometry is unavailable.

## Hardware acceptance

Final production certification still requires the actual Windows 11 PC, webcam and 1920x1080 projector.

Required tests:

1. Four-target calibration.
2. Side-mounted camera/projector geometry.
3. Recalibration after hardware movement.
4. Physical flower detection.
5. Digital Pookalam masking.
6. Every preset at 1080p.
7. Edge effects at 1080p.
8. Interaction effects.
9. 30-minute continuous Run Show stability test.
10. Camera/projector disconnect recovery.

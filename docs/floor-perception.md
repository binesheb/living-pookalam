# Floor Perception and Pookalam Auto-Fit

## Why the camera does not need to be overhead

The installation may place the webcam at the side of the Pookalam. A circular Pookalam therefore appears as an ellipse or another perspective-distorted shape in the raw camera image.

Living Pookalam does **not** perform shape detection directly on that distorted image.

The pipeline is:

```text
Side-mounted webcam
        |
        v
Four known floor reference points
        |
        v
Camera -> floor homography
        |
        v
Rectified top-down floor image
        |
        v
Pookalam segmentation
        |
        v
Contour + mask + centre + confidence
        |
        v
Normalized Pookalam coordinate space
        |
        v
Interaction + effects + projection renderer
```

## Two different calibration concepts

### 1. Camera/floor calibration

The operator establishes four points on the floor plane. These can be detected using ArUco markers or another robust calibration target. They define the projective transform that converts the angled camera view into a virtual top-down floor view.

### 2. Pookalam detection

After rectification, the software finds the actual Pookalam region. The primary result is a **mask/contour**, not a circle.

Centre, area, bounding box and other measurements are derived from that contour.

This allows the same system to support:

- circular Pookalams
- oval Pookalams
- slightly irregular handmade Pookalams
- asymmetric designs
- different diameters
- different layouts

## Operator workflow

1. Mount the webcam and projector.
2. Run projector/webcam/floor calibration.
3. Point the camera at the physical Pookalam.
4. Run **Detect Pookalam**.
5. Review the detected contour/mask.
6. Press **Accept & Lock**.
7. Run the interaction test.
8. Run the show.

The system should never silently assume a perfect circle.

## Digital and hybrid sources

A digital Pookalam image can use its own alpha/shape mask as the base geometry.

Hybrid mode can use:

- physical Pookalam for floor geometry
- uploaded digital artwork for visual content
- the same normalized coordinate system for effects

## Production requirement

Automatic segmentation is an assisted feature. Camera exposure, floor reflections, shadows, people and flower colours can reduce confidence. The operator UI must show the confidence and allow manual correction before locking the geometry.

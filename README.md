# Interactive Pookalam

Interactive Pookalam uses a calibrated projector and camera to create two independent interaction spaces from one live camera view.

## Two-zone interaction model

### 1. Projector Field Zone
The complete quadrilateral illuminated by the projector.

- Motion is detected anywhere inside this zone.
- Camera coordinates are mapped into projector pixel coordinates.
- Field activity can create large-scale effects across the whole projection: ripples, wake-up pulses, trails, or ambient reactions.

### 2. Floor Interaction Zone
The designated physical floor area inside the projector field.

- The quadrilateral is perspective-rectified into a normalized square.
- Detailed contour and occupancy analysis happens only here.
- Positions are reported as normalized `(u,v)` coordinates from `(0,0)` to `(1,1)`.
- These data drive precise Pookalam interactions and future pattern-aware effects.

The two zones are intentionally separate. A movement in the outer projector field can trigger a global animation without being interpreted as detailed floor interaction.

## Current interactive build

- Upload and crop a high-quality Pookalam reference image.
- Calibrate projector field and floor interaction area separately.
- Keep the Pookalam image as the base projection.
- Detect global motion across the projector field.
- Convert global motion into projector-space pulse effects.
- Rectify the floor area for detailed interaction analysis.
- Show live camera and floor debug windows while interaction is running.
- Project only on the Windows extended display.
- Stop and terminate controls in the GUI.
- Manual GitHub update plus one controlled startup update check.

## Controls

- **Select & Crop**
- **Calibrate Zones**
- **Start Interactive**
- **Stop**
- **Close App**
- **Update from GitHub**

## Start

```bat
run_windows.bat
```

Press **Stop** to end projection and camera processing. The application also closes all camera/projection windows when **Close App** is used.

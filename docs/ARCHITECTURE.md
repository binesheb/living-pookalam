# Architecture

## Runtime layers

### 1. Core
Owns lifecycle, configuration, logging and health.

### 2. Perception
Normalizes camera/sensor input into application events. Hardware-specific code must stay behind an adapter interface.

### 3. Interaction
Converts normalized events into semantic actions such as `ZONE_ENTER`, `GESTURE`, `TOUCH`, `IDLE_TIMEOUT` and `SCENE_REQUEST`.

### 4. Experience
Owns Pookalam scenes, zones, effects and state transitions. It must not know whether output is a projector, monitor or LED wall.

### 5. Rendering
Converts experience state into frames for a configured output backend. Projector mapping is a profile concern.

### 6. Operator API/UI
Provides local controls, health, diagnostics, scene selection and calibration status.

## Multi-showroom model

```text
                  GitHub release
                        |
          +-------------+-------------+
          |             |             |
       Showroom A    Showroom B    Showroom C
       profile       profile       profile
          |             |             |
       machine       machine       machine
```

The release is identical. Only profile data and hardware calibration differ.

## Hardware abstraction

Camera, GPIO, projector and display implementations must be adapters. The rest of the application consumes stable interfaces. This allows development on Windows and deployment on Linux/Raspberry Pi without rewriting the experience layer.

## Offline-first

The core experience must continue working when internet connectivity is unavailable. Network/cloud integrations are optional extensions, never a runtime dependency for the basic installation.

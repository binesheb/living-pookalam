# Living Pookalam

A reusable, showroom-deployable interactive Pookalam platform.

Living Pookalam turns a physical floral/visual installation into an interactive digital experience using a camera, projector/display, local computer and configurable content. The same software core is deployed to multiple showrooms through independent profiles.

## Core principle

**One application. Many showroom profiles.**

A showroom must never require a code fork. Physical dimensions, camera calibration, projector mapping, zones, content and local hardware settings belong in `profiles/`, while application logic stays in `app/`.

```text
Camera / Sensors
       |
       v
+-------------------+
| Perception Layer  |
+-------------------+
       |
       v
+-------------------+
| Interaction Engine|
+-------------------+
       |
       v
+-------------------+
| Experience Engine |
+-------------------+
       |
       v
+-------------------+
| Renderer / Output |
+-------------------+
       |
       v
Projector / Display
```

## Repository layout

```text
app/
  api/             Local control and health API
  core/            Configuration and application lifecycle
  experience/      Scenes, zones and experience state
  hardware/        Hardware adapters
  interaction/     Input-to-action rules
  perception/      Camera/sensor processing
  rendering/       Output abstraction
  ui/              Operator dashboard
profiles/
  template/        Copy this for a new showroom
  showrooms/       Deployment-specific profiles
scripts/           Installation and maintenance helpers
tests/             Automated tests
tools/             Calibration and diagnostics
docs/              Architecture and deployment docs
```

## Quick start

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m app
```

Docker:

```bash
docker compose up --build
```

## Configuration

Set `LIVING_POOKALAM_PROFILE` to a showroom profile. Development defaults to `profiles/template`.

Do not commit secrets, API keys, passwords, certificates or machine-specific credentials.

## Replicating a showroom

1. Copy `profiles/template` to `profiles/showrooms/<id>`.
2. Enter physical dimensions and hardware identifiers.
3. Run calibration tools.
4. Store calibration output in the showroom profile.
5. Deploy the same application release.
6. Validate health, camera input, rendering and interaction.

The deployment should be reproducible on Windows during development and Linux/Raspberry Pi where hardware permits.

## Roadmap

- Core configuration/profile system
- Local operator API and health monitoring
- Camera abstraction and calibration
- Pookalam geometry and interaction zones
- Real-time renderer
- Operator dashboard
- Docker and Raspberry Pi deployment
- Content/effect plugin system
- Multi-showroom fleet management

## Contribution

Ideas, bugs and improvements belong in GitHub Issues. Prefer small pull requests. New showroom support should normally be configuration, not duplicated code.

## License

MIT. See `LICENSE`.

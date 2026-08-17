# Showroom Deployment

## New showroom

1. Install the supported OS and Python/Docker runtime.
2. Clone the repository at the required release tag.
3. Copy `profiles/template` to `profiles/showrooms/<id>`.
4. Configure the display/projector and camera.
5. Run calibration tools.
6. Set `LIVING_POOKALAM_PROFILE=<id>`.
7. Start with Docker Compose.
8. Open the local operator endpoint on port 8080.
9. Verify camera, rendering, interaction and recovery after restart.

## Machine independence

A machine should contain only deployment-specific data and runtime state. Application source comes from a known GitHub release. This makes replacement machines and additional showrooms repeatable.

## Operational rule

Do not edit application code directly on a showroom machine. Fix the code in GitHub, release it, and deploy the release. Profile-only changes can be made through the showroom deployment process.

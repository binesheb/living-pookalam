# Showroom Profile Template

Copy this directory to `profiles/showrooms/<showroom-id>/`.

Do not put secrets here.

## Calibration files

- `camera-calibration.json` — camera intrinsics/extrinsics and capture settings.
- `projector-mapping.json` — output geometry and projector mapping.

These files are intentionally separate from the application so a replacement computer or projector can be calibrated without changing source code.

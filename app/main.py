"""Living Pookalam application entry point."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conlist

from app import __version__
from app.calibration.manual_corners import calibrate_manual_corners
from app.core.config import load_profile
from app.core.runtime import RuntimeState

app = FastAPI(title="Living Pookalam", version=__version__)
state = RuntimeState()
manual_calibration = None


class Point(BaseModel):
    x: float
    y: float


class ManualCornerRequest(BaseModel):
    points: list[Point] = Field(min_length=4, max_length=4)
    physical_width_mm: float = Field(gt=0)
    physical_height_mm: float = Field(gt=0)


@app.on_event("startup")
def startup() -> None:
    state.start()


@app.get("/health")
def health() -> dict:
    profile = load_profile()
    return {"status": "ok", "running": state.running, "version": __version__, "profile": profile.get("id", "unknown")}


@app.get("/api/v1/state")
def runtime_state() -> dict:
    return {"running": state.running, "active_scene": state.active_scene, "last_event": state.last_event, "started_at": state.started_at.isoformat() if state.started_at else None}


@app.get("/api/v1/calibration/manual")
def get_manual_calibration() -> dict:
    return {"calibration": manual_calibration.as_dict() if manual_calibration else None,
            "corner_order": ["top_left", "top_right", "bottom_right", "bottom_left"]}


@app.post("/api/v1/calibration/manual")
def save_manual_calibration(request: ManualCornerRequest) -> dict:
    global manual_calibration
    try:
        manual_calibration = calibrate_manual_corners(
            [[p.x, p.y] for p in request.points], request.physical_width_mm, request.physical_height_mm
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "calibration": manual_calibration.as_dict()}


def run() -> None:
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()

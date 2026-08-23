"""Living Pookalam application entry point."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import __version__
from app.core.config import load_profile, load_runtime_config, save_runtime_config
from app.core.runtime import RuntimeState
from app.perception.camera import discover_cameras, test_camera

app = FastAPI(title="Living Pookalam", version=__version__)
state = RuntimeState()


class CameraSelection(BaseModel):
    index: int = Field(ge=0, le=99)


@app.on_event("startup")
def startup() -> None:
    state.start()


@app.get("/health")
def health() -> dict:
    profile = load_profile()
    return {
        "status": "ok",
        "running": state.running,
        "version": __version__,
        "profile": profile.get("id", "unknown"),
    }


@app.get("/api/v1/state")
def runtime_state() -> dict:
    return {
        "running": state.running,
        "active_scene": state.active_scene,
        "last_event": state.last_event,
        "started_at": state.started_at.isoformat() if state.started_at else None,
    }


@app.get("/api/v1/cameras")
def cameras(max_index: int = 10) -> dict:
    max_index = min(max(max_index, 1), 50)
    return {"selected_index": load_runtime_config()["camera_index"],
            "cameras": discover_cameras(max_index)}


@app.post("/api/v1/cameras/test")
def camera_test(selection: CameraSelection) -> dict:
    return test_camera(selection.index)


@app.post("/api/v1/cameras/select")
def select_camera(selection: CameraSelection) -> dict:
    result = test_camera(selection.index)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Camera test failed"))
    config = load_runtime_config()
    config["camera_index"] = selection.index
    save_runtime_config(config)
    return {"ok": True, "selected_index": selection.index, "camera": result}


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()

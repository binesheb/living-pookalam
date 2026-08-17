"""Living Pookalam application entry point."""

from fastapi import FastAPI

from app import __version__
from app.core.config import load_profile
from app.core.runtime import RuntimeState

app = FastAPI(title="Living Pookalam", version=__version__)
state = RuntimeState()


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


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["profile"] == "template"


def test_state() -> None:
    response = client.get("/api/v1/state")
    assert response.status_code == 200
    assert "active_scene" in response.json()

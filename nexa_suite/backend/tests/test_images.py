from fastapi.testclient import TestClient

from app.main import app


def test_image_generation_requires_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.images.is_permission_enabled", lambda _key: False)
    response = TestClient(app).post(
        "/api/images/generate",
        json={"prompt": "a neon city", "user_confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_generated_image_rejects_invalid_id() -> None:
    response = TestClient(app).get("/api/images/not-a-safe-id")
    assert response.status_code == 404

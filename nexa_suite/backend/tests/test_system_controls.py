from fastapi.testclient import TestClient

from app.main import app


def test_system_control_requires_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.system_controls.is_permission_enabled", lambda _key: False)
    response = TestClient(app).post(
        "/api/system-controls/execute",
        json={"action": "volume_up", "user_confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_system_control_requires_confirmation(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.system_controls.is_permission_enabled", lambda _key: True)
    response = TestClient(app).post(
        "/api/system-controls/execute",
        json={"action": "close_app", "target": "notepad", "user_confirmed": False},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmation_required"

from fastapi.testclient import TestClient

from app.main import app
from app.voice import assemblyai


def test_assemblyai_status_requires_key(monkeypatch):
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    result = assemblyai.status()
    assert result["configured"] is False
    assert result["ready"] is False


def test_assemblyai_token_route_does_not_expose_key(monkeypatch):
    monkeypatch.setattr("app.api.routes.voice.is_permission_enabled", lambda _key: True)

    async def fake_token():
        return "short-lived-token"

    monkeypatch.setattr(assemblyai, "create_streaming_token", fake_token)
    result = TestClient(app).get("/api/voice/stt/assemblyai/token")
    assert result.status_code == 200
    assert result.json()["token"] == "short-lived-token"
    assert result.json()["provider"] == "assemblyai"

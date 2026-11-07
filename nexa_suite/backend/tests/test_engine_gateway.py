"""The web facade must preserve the native engine's private control boundary."""
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


def test_cross_origin_page_cannot_control_engine():
    with patch("app.api.routes.engine.forward", new_callable=AsyncMock) as forward:
        with TestClient(app) as client:
            response = client.post("/api/engine/command", json={"action": "text", "text": "Hello"},
                                   headers={"Origin": "https://example.com"})
        assert response.status_code == 403
        forward.assert_not_awaited()


def test_local_nexa_command_uses_fixed_private_route():
    with patch("app.api.routes.engine.forward", new_callable=AsyncMock, return_value={"accepted": True}) as forward:
        with TestClient(app) as client:
            response = client.post("/api/engine/command", json={"action": "text", "text": "আমার নাম কী?"},
                                   headers={"Origin": "http://127.0.0.1:8766"})
        assert response.status_code == 200
        args = forward.await_args.args
        assert args[0] == "/command"
        assert args[1]["text"] == "আমার নাম কী?"


def test_event_cursor_is_forwarded_without_arbitrary_url():
    with patch("app.api.routes.engine.forward", new_callable=AsyncMock, return_value={"events": [], "cursor": 7}) as forward:
        with TestClient(app) as client:
            assert client.get("/api/engine/events?after=7").status_code == 200
        forward.assert_awaited_once_with("/state?after=7")

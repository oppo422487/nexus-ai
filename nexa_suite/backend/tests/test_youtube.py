from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.youtube.controller import parse_youtube_command
from app.chat import service as chat_service


def test_youtube_command_parser_supports_media_controls() -> None:
    cases = {
        "pause youtube": ("pause", None),
        "resume the video": ("resume", None),
        "skip forward 15 seconds": ("skip", 15),
        "skip back 8 seconds": ("skip", -8),
        "youtube volume 70": ("set_volume", 70),
        "set speed 1.5": ("set_speed", 1.5),
        "sleep timer 30": ("sleep_timer", 30),
        "close youtube": ("close", None),
        "ইউটিউব বন্ধ করো": ("close", None),
    }
    for text, (action, value) in cases.items():
        parsed = parse_youtube_command(text)
        assert parsed.action == action
        assert parsed.value == value


def test_youtube_search_parser_keeps_query() -> None:
    parsed = parse_youtube_command("youtube e lofi music search koro")
    assert parsed.action == "search"
    assert parsed.query == "lofi music"


def test_youtube_search_parser_supports_bangla_and_short_yt_forms() -> None:
    cases = {
        "yt te python tutorial search dao": "python tutorial",
        "ইউটিউবে বাংলা গান চালাও": "বাংলা গান",
        "ইউটিউব এ রবীন্দ্র সংগীত খুঁজে দাও": "রবীন্দ্র সংগীত",
    }
    for text, expected_query in cases.items():
        parsed = parse_youtube_command(text)
        assert parsed.action == "search"
        assert parsed.query == expected_query


def test_youtube_skill_is_registered() -> None:
    from app.productivity.registry import skill_registry

    skill = next(item for item in skill_registry() if item["id"] == "advanced_youtube")
    assert skill["name"] == "YouTube Skill"
    assert skill["status"] == "ready"


def test_youtube_command_requires_confirmation(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.youtube.is_permission_enabled", lambda _key: True)
    response = TestClient(app).post(
        "/api/youtube/command",
        json={"action": "pause", "user_confirmed": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmation_required"
    assert body["executed"] is False


def test_youtube_status_never_requires_browser(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.youtube.is_permission_enabled", lambda _key: True)
    response = TestClient(app).get("/api/youtube/status")
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "status"
    assert body["state"]["launched"] is False


def test_chat_youtube_control_returns_confirmable_action(monkeypatch) -> None:
    monkeypatch.setattr(chat_service, "is_permission_enabled", lambda _key: True)
    response = chat_service._youtube_skill_response("pause youtube")
    assert response.intent == "youtube_control"
    assert response.requires_confirmation is True
    assert response.action is not None
    assert response.action.kind == "youtube_control"

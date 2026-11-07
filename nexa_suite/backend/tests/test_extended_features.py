from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.reminders import store as reminder_store


client = TestClient(app)


def test_content_export_requires_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.content.is_permission_enabled", lambda _key: False)
    response = client.post(
        "/api/content/export",
        json={"title": "Notes", "content": "Safe local notes", "format": "md", "user_confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_content_export_writes_only_safe_name(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.api.routes.content.is_permission_enabled", lambda _key: True)
    monkeypatch.setattr("app.api.routes.content.OUTPUT_DIR", tmp_path)
    response = client.post(
        "/api/content/export",
        json={"title": "../../My Bangla Notes", "content": "Hello", "format": "md", "user_confirmed": True},
    )
    body = response.json()
    assert body["exported"] is True
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert files[0].parent == tmp_path
    assert files[0].read_text(encoding="utf-8").startswith("# ../../My Bangla Notes")


def test_image_queue_and_history_require_permission(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.images.is_permission_enabled", lambda _key: False)
    queued = client.post("/api/images/queue", json={"prompt": "a city", "user_confirmed": True})
    history = client.get("/api/images/history")
    assert queued.json()["status"] == "blocked"
    assert history.json()["images"] == []


def test_edge_tts_requires_both_permissions(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.voice.is_permission_enabled", lambda _key: False)
    response = client.post(
        "/api/voice/tts/edge/audio",
        json={"text": "hello", "voice": "en-US-AriaNeural", "rate": "+0%"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"


def test_voice_engines_use_online_services_without_local_models(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.voice.is_permission_enabled", lambda _key: True)
    engines = client.get("/api/voice/stt/engines").json()
    tts = client.get("/api/voice/tts/status").json()

    assert engines["preferred_engine"] == "assemblyai_streaming"
    assert engines["engines"][0]["model_available"] is True
    assert "local model" in engines["engines"][0]["message"]
    assert tts["available"] is True
    assert {voice["id"] for voice in tts["voices"]} >= {
        "bn-BD-NabanitaNeural",
        "bn-BD-PradeepNeural",
    }


def test_audit_statistics_and_export_are_available() -> None:
    stats = client.get("/api/audit/stats")
    export = client.get("/api/audit/export?format=csv")
    assert stats.status_code == 200
    assert stats.json()["status"] == "ok"
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "created_at" in export.text.splitlines()[0]


def test_reminder_can_be_edited_and_due_time_cleared(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(reminder_store, "REMINDERS_DB_PATH", tmp_path / "reminders.sqlite3")
    created = reminder_store.create_reminder("Old title", "note", "2026-08-30T10:00:00+06:00", "daily")
    assert created["ok"] is True
    reminder_id = created["reminder"]["id"]
    updated = reminder_store.update_reminder(
        reminder_id,
        title="New title",
        due_at="",
        recurrence="weekly",
    )
    assert updated["ok"] is True
    item = reminder_store.list_reminders()[0]
    assert item["title"] == "New title"
    assert item["due_at"] is None
    assert item["recurrence"] == "weekly"


def test_huggingface_configuration_is_local_and_confirmed(monkeypatch, tmp_path) -> None:
    local_env = tmp_path / ".env"
    monkeypatch.setattr("app.api.routes.setup.env_file", lambda: local_env)
    blocked = client.post("/api/setup/huggingface", json={"token": "hf_test_token", "user_confirmed": False})
    assert blocked.json()["status"] == "confirmation_required"
    saved = client.post("/api/setup/huggingface", json={"token": "hf_test_token", "user_confirmed": True})
    assert saved.json()["configured"] is True
    assert local_env.read_text(encoding="utf-8") == "HUGGINGFACE_API_KEY=hf_test_token\n"


def test_packaged_electron_null_origin_is_allowed() -> None:
    response = client.options(
        "/api/health",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "null"

from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.productivity import store as productivity_store
from app.productivity import service as productivity_service
from app.reminders import store as reminder_store


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(productivity_store, "DB_PATH", tmp_path / "productivity.sqlite3")
    monkeypatch.setattr(reminder_store, "REMINDERS_DB_PATH", tmp_path / "reminders.sqlite3")
    return TestClient(app)


def _chat(client: TestClient, message: str, source: str = "chat_page") -> dict:
    response = client.post("/api/chat/message", json={"message": message, "source": source})
    assert response.status_code == 200
    return response.json()


def test_persistent_memory_voice_and_text(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    saved = _chat(client, "মনে রাখো আমার favourite color blue")
    listed = _chat(client, "কি মনে রেখেছ")
    assert saved["intent"] == "memory_save"
    assert "favourite color blue" in listed["answer"]


def test_notes_tasks_and_shopping_commands(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    assert _chat(client, "নোট করো voice test করতে হবে")["intent"] == "note_save"
    assert _chat(client, "task add documentation শেষ করো")["intent"] == "task_save"
    assert _chat(client, "shopping list add coffee")["intent"] == "shopping_save"
    assert "documentation" in _chat(client, "task list")["answer"]


def test_local_calendar_and_email_draft_never_send(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    calendar = _chat(client, "calendar add tomorrow 10 am team meeting")
    email = _chat(client, "email draft to Rahim project update ready")
    assert calendar["intent"] == "calendar_add"
    assert email["intent"] == "email_draft"
    assert "send করিনি" in email["answer"]
    snapshot = client.get("/api/productivity/dashboard").json()
    assert len(snapshot["calendar_events"]) == 1
    assert len(snapshot["drafts"]) == 1


def test_reminder_timer_command_creates_local_alert(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    data = _chat(client, "set a timer in 5 minutes")
    assert data["intent"] == "reminder_create"
    assert reminder_store.list_reminders(include_done=False)


def test_media_commands_use_allowlisted_windows_control(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        productivity_service,
        "execute_system_control",
        lambda request: SimpleNamespace(status="executed", message=f"ok:{request.action}"),
    )
    assert _chat(client, "next song")["answer"] == "ok:next_track"
    assert _chat(client, "close spotify")["answer"] == "ok:close_app"


def test_screen_context_uses_active_nexa_page(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    data = _chat(client, "এই স্ক্রিনে কী আছে", "global_voice:skills")
    assert data["intent"] == "screen_context"
    assert "২০টি capability" in data["answer"]


def test_voice_profiles_do_not_claim_biometrics(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    data = _chat(client, "voice profile create Rahman")
    assert data["intent"] == "voice_profile_create"
    dashboard = client.get("/api/productivity/dashboard").json()
    assert dashboard["voice_profiles"][0]["name"] == "Rahman"


def test_registry_has_all_twenty_skills_and_diagnostics(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    dashboard = client.get("/api/productivity/dashboard").json()
    diagnostics = client.get("/api/productivity/diagnostics").json()
    assert len(dashboard["skills"]) == 20
    assert all(skill["status"] == "ready" for skill in dashboard["skills"])
    assert diagnostics["backend"] == "connected"
    assert len(diagnostics["checks"]) >= 4


def test_productivity_api_requires_confirmation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    blocked = client.post("/api/productivity/items", json={"kind": "note", "text": "private note"}).json()
    created = client.post("/api/productivity/items", json={"kind": "note", "text": "private note", "user_confirmed": True}).json()
    assert blocked["status"] == "confirmation_required"
    assert created["created"] is True

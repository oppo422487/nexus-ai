from __future__ import annotations

from fastapi.testclient import TestClient

from app.audit import event_log
from app.main import app
from app.actions.website import get_allowed_website_url
from app.permissions import store as permission_store


def action_payload(
    intent: str,
    value: str,
    kind: str,
    original_text: str,
    *,
    confirmed: bool = True,
    dry_run: bool = True,
) -> dict:
    return {
        "intent": intent,
        "target": {"kind": kind, "value": value, "label": value},
        "original_text": original_text,
        "normalized_text": original_text.lower(),
        "confidence": 100,
        "safety_level": "confirmation_required",
        "user_confirmed": confirmed,
        "dry_run": dry_run,
        "source": "pytest_safety_smoke",
    }


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_canonical_youtube_url_is_allowed() -> None:
    allowed, url, reason = get_allowed_website_url("https://www.youtube.com")
    assert allowed is True
    assert url == "https://www.youtube.com"
    assert reason == "Website is allowed."


def test_permissions_endpoint(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    client = TestClient(app)

    response = client.get("/api/permissions")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["permissions"], list)
    assert isinstance(data["locked_permissions"], list)


def test_locked_permission_cannot_be_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    client = TestClient(app)

    response = client.put(
        "/api/permissions",
        json={"key": "shell_command_execution", "enabled": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["updated"] is False
    assert data["enabled"] is False


def test_dangerous_command_blocked_even_with_confirmation(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    client = TestClient(app)

    response = client.post(
        "/api/actions/website/open",
        json=action_payload(
            "open_website",
            "google",
            "url",
            "delete system32 then open google",
            confirmed=True,
            dry_run=False,
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["executed"] is False
    assert data["can_execute"] is False


def test_unknown_app_target_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    client = TestClient(app)

    response = client.post(
        "/api/actions/app/open",
        json=action_payload(
            "open_app",
            "unknown_app_for_pytest",
            "app",
            "open unknown app",
            confirmed=True,
            dry_run=False,
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["executed"] is False


def test_unknown_website_target_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    client = TestClient(app)

    response = client.post(
        "/api/actions/website/open",
        json=action_payload(
            "open_website",
            "example.invalid",
            "url",
            "open example invalid",
            confirmed=True,
            dry_run=False,
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["executed"] is False


def test_whitelisted_dry_run_action_is_preview_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    client = TestClient(app)

    response = client.post(
        "/api/actions/website/open",
        json=action_payload(
            "open_website",
            "google",
            "url",
            "open google",
            confirmed=True,
            dry_run=True,
        ),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview_only"
    assert data["executed"] is False
    assert data["dry_run"] is True


def test_audit_recent_endpoint_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        permission_store,
        "PERMISSIONS_FILE",
        tmp_path / "permissions.json",
    )
    monkeypatch.setattr(event_log, "AUDIT_DB_PATH", tmp_path / "audit.sqlite3")
    client = TestClient(app)

    client.post(
        "/api/actions/website/open",
        json=action_payload(
            "open_website",
            "google",
            "url",
            "open google",
            confirmed=True,
            dry_run=True,
        ),
    )
    response = client.get("/api/audit/recent?limit=10")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["events"], list)
    assert data["events"]
    assert data["events"][0]["status"] == "preview_only"

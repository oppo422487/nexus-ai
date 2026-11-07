from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_email_status_never_exposes_password(monkeypatch):
    monkeypatch.setenv("NEXA_EMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("NEXA_EMAIL_APP_PASSWORD", "private-app-password")
    response = client.get("/api/email/status")
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert "password" not in response.text.lower()
    assert "private-app-password" not in response.text


def test_email_send_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setenv("NEXA_EMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("NEXA_EMAIL_APP_PASSWORD", "private-app-password")
    response = client.post("/api/email/send", json={"recipient": "person@example.com", "subject": "Update", "body": "Hello", "user_confirmed": False})
    assert response.status_code == 200
    assert response.json()["sent"] is False
    assert response.json()["status"] == "confirmation_required"


def test_email_preview_never_sends(monkeypatch):
    monkeypatch.setenv("NEXA_EMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("NEXA_EMAIL_APP_PASSWORD", "private-app-password")
    response = client.post("/api/email/preview", json={"recipient": "person@example.com", "subject": "Update", "body": "Hello"})
    assert response.status_code == 200
    assert response.json()["sent"] is False
    assert response.json()["confirmation_required"] is True

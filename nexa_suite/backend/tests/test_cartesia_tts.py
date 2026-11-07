from fastapi.testclient import TestClient

from app.main import app
from app.voice import cartesia


def test_cartesia_key_is_encrypted_and_never_returned(tmp_path, monkeypatch):
    monkeypatch.setattr(cartesia, "KEY_FILE", tmp_path / "cartesia-key.dpapi")
    monkeypatch.setattr(cartesia, "SETTINGS_FILE", tmp_path / "cartesia-settings.json")
    client = TestClient(app)
    key = "sk_car_testing123456789"

    saved = client.put("/api/voice/tts/cartesia/key", json={"api_key": key}).json()
    assert saved["ok"] is True
    assert saved["configured"] is True
    assert key.encode() not in cartesia.KEY_FILE.read_bytes()
    assert key not in str(saved)
    assert key not in client.get("/api/voice/tts/cartesia/status").text
    assert cartesia.get_key() == key

    removed = client.delete("/api/voice/tts/cartesia/key").json()
    assert removed["configured"] is False
    assert not cartesia.KEY_FILE.exists()


def test_cartesia_is_primary_and_does_not_call_edge(tmp_path, monkeypatch):
    monkeypatch.setattr(cartesia, "KEY_FILE", tmp_path / "cartesia-key.dpapi")
    monkeypatch.setattr(cartesia, "SETTINGS_FILE", tmp_path / "cartesia-settings.json")
    cartesia.save_key("sk_car_testing123456789")
    called = []
    monkeypatch.setattr(cartesia, "generate_audio", lambda text, language: called.append((text, language)) or b"mp3data")
    response = TestClient(app).post("/api/voice/tts/audio", json={"text": "হ্যালো", "language": "bn"})
    assert response.status_code == 200
    assert response.content == b"mp3data"
    assert response.headers["X-TTS-Provider"] == "cartesia"
    assert called == [("হ্যালো", "bn")]


def test_invalid_key_does_not_replace_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(cartesia, "KEY_FILE", tmp_path / "cartesia-key.dpapi")
    monkeypatch.setattr(cartesia, "SETTINGS_FILE", tmp_path / "cartesia-settings.json")
    cartesia.save_key("sk_car_testing123456789")
    result = TestClient(app).put("/api/voice/tts/cartesia/key", json={"api_key": "invalid-key-value"}).json()
    assert result["ok"] is False
    assert cartesia.get_key() == "sk_car_testing123456789"


def test_cartesia_audio_uses_current_key_and_selected_voice(tmp_path, monkeypatch):
    monkeypatch.setattr(cartesia, "KEY_FILE", tmp_path / "cartesia-key.dpapi")
    monkeypatch.setattr(cartesia, "SETTINGS_FILE", tmp_path / "cartesia-settings.json")
    cartesia.save_key("sk_car_testing123456789")
    cartesia.set_voice("bn", "test-bangla-voice")
    requests = []

    class Response:
        content = b"mp3-data"
        def raise_for_status(self):
            return None

    def fake_post(url, *, headers, json, timeout):
        requests.append((url, headers, json, timeout))
        return Response()

    monkeypatch.setattr(cartesia.httpx, "post", fake_post)
    assert cartesia.generate_audio("হ্যালো", "bn") == b"mp3-data"
    assert requests[0][1]["Authorization"] == "Bearer sk_car_testing123456789"
    assert requests[0][2]["model_id"] == "sonic-3.6"
    assert requests[0][2]["voice"] == "test-bangla-voice"
    assert requests[0][2]["language"] == "bn"

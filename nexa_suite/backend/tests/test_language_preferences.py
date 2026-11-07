from fastapi.testclient import TestClient

from app.main import app
from app.chat import service
from app.llm.schemas import LLMResponse


def test_bangla_preference_controls_english_input(monkeypatch):
    monkeypatch.setattr(service, "complete_llm", lambda *args, **kwargs: None)
    response = TestClient(app).post("/api/chat/message", json={"message": "hello", "preferred_language": "Bangla"}).json()
    assert response["intent"] == "greeting"
    assert "কীভাবে সাহায্য" in response["answer"]


def test_english_preference_controls_bangla_input(monkeypatch):
    monkeypatch.setattr(service, "complete_llm", lambda *args, **kwargs: None)
    response = TestClient(app).post("/api/chat/message", json={"message": "ধন্যবাদ", "preferred_language": "English"}).json()
    assert "You are welcome" in response["answer"]


def test_explicit_language_request_overrides_setting(monkeypatch):
    monkeypatch.setattr(service, "complete_llm", lambda *args, **kwargs: None)
    response = TestClient(app).post("/api/chat/message", json={"message": "hello, reply in English", "preferred_language": "Bangla"}).json()
    assert "Hello" in response["answer"]


def test_language_postprocessing_translates_wrong_language(monkeypatch):
    monkeypatch.setattr(service, "complete_llm", lambda *args, **kwargs: LLMResponse(answer="বাংলা উত্তর।", provider="test"))
    token = service.set_preferred_reply_language("hello", "Bangla")
    try:
        from app.schemas.chat import ChatMessageResponse
        response = ChatMessageResponse(status="completed", intent="test", message="hello", answer="This is an English response.")
        result = service.enforce_reply_language(response, "hello", None)
        assert result.answer == "বাংলা উত্তর।"
    finally:
        service.reset_preferred_reply_language(token)

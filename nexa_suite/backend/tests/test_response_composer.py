from __future__ import annotations

from types import SimpleNamespace

from app.assistant.response_composer import compose, compose_intent
from app.chat import service


def test_boss_style_always_uses_boss() -> None:
    assert compose("Hello, how can I help?", "Boss", "english").startswith("Boss,")
    assert compose_intent("llm_setup_missing", address_style="Boss", language_style="mixed").startswith("Boss,")


def test_sir_style_always_uses_sir() -> None:
    answer = compose_intent("youtube_open_done", address_style="Sir", language_style="mixed")
    assert answer.startswith("Sir,")
    assert "Boss" not in answer


def test_vai_style_uses_vai() -> None:
    answer = compose_intent("calculator_open_done", address_style="Vai", language_style="mixed")
    assert answer.startswith("Vai,")
    assert "Boss" not in answer
    assert "Sir" not in answer


def test_neutral_omits_title() -> None:
    answer = compose_intent("clarification", address_style="Neutral", language_style="english")
    assert not answer.startswith(("Boss,", "Sir,", "Vai,"))


def test_whatsapp_reply_says_send_was_not_clicked() -> None:
    answer = compose_intent("whatsapp_draft_done", address_style="Boss", language_style="mixed")
    assert "Boss" in answer
    assert "Send" in answer
    assert "click" in answer


def test_youtube_reply_is_natural() -> None:
    open_answer = compose_intent("youtube_open_done", address_style="Boss", language_style="mixed")
    search_answer = compose_intent("youtube_search_done", address_style="Boss", language_style="mixed", query="python tutorial")
    assert "YouTube open" in open_answer
    assert "python tutorial" in search_answer
    assert "search" in search_answer


def test_bangla_youtube_reply_is_natural() -> None:
    answer = compose_intent("youtube_open_done", address_style="Sir", language_style="bangla")
    assert answer.startswith("স্যার,")
    assert "আপনার জন্য YouTube" in answer
    assert "আর কিছু" in answer


def test_no_generic_vague_fallback_for_known_composer_cases() -> None:
    answer = compose_intent("llm_setup_missing", address_style="Boss", language_style="mixed")
    assert "I am not fully sure what you want yet" not in answer
    assert "key" in answer


def test_repeated_casual_chat_varies() -> None:
    first = service.conversational_answer("how are you", "casual_chat", "Boss", [])
    history = [SimpleNamespace(role="assistant", content=first.answer)]
    second = service.conversational_answer("how are you", "casual_chat", "Boss", history)
    assert first.answer != second.answer


def test_calculator_action_reply_is_natural(monkeypatch) -> None:
    monkeypatch.setattr(service, "get_allowed_app", lambda message: (True, {"label": "Calculator", "command": "calc.exe"}, "ok"))
    monkeypatch.setattr(service, "normalize_app_key", lambda message: "calculator")
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: True)
    monkeypatch.setattr(
        service,
        "execute_open_app",
        lambda request: SimpleNamespace(status="executed", executed=True, error=None, message="executed"),
    )
    response = service._app_action_response("calculator open koro", "Boss")
    assert response.status == "executed"
    assert response.auto_execute_safe is True
    assert response.answer.startswith("Boss,")
    assert "Calculator open" in response.answer


def test_youtube_trusted_open_reply_is_natural(monkeypatch) -> None:
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: True)
    monkeypatch.setattr(
        service,
        "execute_open_website",
        lambda request: SimpleNamespace(status="executed", executed=True, error=None, message="opened"),
    )
    response = service._youtube_skill_response("youtube open koro", "Boss")
    assert response.status == "executed"
    assert response.answer.startswith("Boss,")
    assert "YouTube open" in response.answer


def test_bangla_youtube_trusted_open_reply_is_natural(monkeypatch) -> None:
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: True)
    monkeypatch.setattr(
        service,
        "execute_open_website",
        lambda request: SimpleNamespace(status="executed", executed=True, error=None, message="opened"),
    )
    response = service._youtube_skill_response("ইউটিউব ওপেন কর", "Sir")
    assert response.status == "executed"
    assert response.answer.startswith("স্যার,")
    assert "আপনার জন্য YouTube" in response.answer


def test_whatsapp_trusted_reply_says_no_send_click(monkeypatch) -> None:
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: True)
    monkeypatch.setattr(
        service,
        "execute_open_website",
        lambda request: SimpleNamespace(status="executed", executed=True, error=None, message="opened"),
    )
    response = service._execute_trusted_website_open(
        url="whatsapp://send?phone=8801922869012&text=hi",
        label="WhatsApp draft to Rahim",
        original_text="whatsapp e Rahim ke bolo hi",
        intent="whatsapp_draft",
        success_answer="unused",
        action_kind="whatsapp_draft",
        recipient="Rahim",
        draft_text="hi",
        address_style="Boss",
    )
    assert response.status == "executed"
    assert response.answer.startswith("Boss,")
    assert "Send" in response.answer
    assert "click" in response.answer

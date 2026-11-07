from __future__ import annotations

from pathlib import Path

import pytest

from app.chat import service
from app.memory.pending_tasks import PendingTask, clear_pending_task, get_pending_task, set_pending_task, whatsapp_message_task
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse


@pytest.fixture(autouse=True)
def isolated_pending_and_contacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.contacts import store as contact_store

    monkeypatch.setattr(contact_store, "CONTACTS_FILE", tmp_path / "contacts.json")
    clear_pending_task()
    yield
    clear_pending_task()


def _request(message: str, history: list | None = None) -> ChatMessageRequest:
    return ChatMessageRequest(message=message, history=history or [], address_style="Boss")


def _fake_open_response(**kwargs) -> ChatMessageResponse:
    return ChatMessageResponse(
        status="executed",
        intent=kwargs.get("intent", "whatsapp_draft"),
        message=kwargs.get("original_text", ""),
        answer=kwargs.get("success_answer", "Done Boss. WhatsApp draft opened. Please review and press Send manually."),
        execution_enabled=True,
        auto_execute_safe=True,
        chips=["WhatsApp draft"],
        action=service.ChatActionStatus(
            kind=kwargs.get("action_kind", "whatsapp_draft"),
            target=kwargs.get("url", "whatsapp://send?phone=8801922869012&text=hi"),
            label=kwargs.get("label", "WhatsApp draft"),
            executed=True,
            requires_confirmation=False,
            message=kwargs.get("success_answer", "Done"),
            recipient=kwargs.get("recipient"),
            draft_text=kwargs.get("draft_text"),
        ),
    )


def test_whatsapp_pending_number_continuation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: key == "trusted_whatsapp_draft_auto_open")
    monkeypatch.setattr(service, "_execute_trusted_website_open", lambda **kwargs: _fake_open_response(**kwargs))

    first = service.handle_chat_message(_request("whatsapp e Rahim ke bolo ami pore call korbo"))
    assert first.status == "needs_more_info"
    assert first.pending_task is not None
    assert first.pending_task.kind == "whatsapp_contact_number"
    assert "Rahim" in first.pending_task.status_label

    second = service.handle_chat_message(_request("rahim number 01922869012"))
    assert second.status == "executed"
    assert second.auto_execute_safe is True
    assert second.action is not None
    assert second.action.executed is True
    assert "Send" in second.answer
    assert get_pending_task() is None


def test_whatsapp_pending_message_continuation(monkeypatch: pytest.MonkeyPatch) -> None:
    service.save_contact("Rahim", "01922869012")
    monkeypatch.setattr(service, "is_permission_enabled", lambda key: key == "trusted_whatsapp_draft_auto_open")
    monkeypatch.setattr(service, "_execute_trusted_website_open", lambda **kwargs: _fake_open_response(**kwargs))

    first = service.handle_chat_message(_request("WhatsApp Rahim draft"))
    assert first.status == "needs_more_info"
    assert first.pending_task is not None
    assert first.pending_task.kind == "whatsapp_message_text"

    second = service.handle_chat_message(_request("ami pore call korbo"))
    assert second.status == "executed"
    assert second.action is not None
    assert second.action.draft_text
    assert "Send" in second.answer
    assert get_pending_task() is None


def test_app_planning_continuation_completes_pending_task() -> None:
    first = service.handle_chat_message(_request("ami ekta app banate cai"))
    assert first.status == "needs_more_info"
    assert first.pending_task is not None
    assert first.pending_task.kind == "app_planning_details"

    second = service.handle_chat_message(_request("android app, medicine reminder"))
    assert second.status == "completed"
    assert second.intent == "app_planning_continue"
    assert "medicine reminder" in second.answer
    assert get_pending_task() is None


def test_login_page_details_continuation_uses_generation_pending_task() -> None:
    first = service.handle_chat_message(_request("ekta login page banabo"))
    assert first.status == "needs_configuration"
    assert first.pending_task is not None
    assert first.pending_task.kind == "llm_generation_details"

    second = service.handle_chat_message(_request("html css diye"))
    assert second.intent == "llm_generation_continue"
    assert second.status in {"needs_configuration", "completed"}
    assert get_pending_task() is None


def test_cancel_pending_task() -> None:
    set_pending_task(whatsapp_message_task("Rahim", "WhatsApp Rahim draft"))
    response = service.handle_chat_message(_request("cancel"))
    assert response.status == "cancelled"
    assert response.intent == "pending_task_cancel"
    assert get_pending_task() is None


def test_dangerous_command_during_pending_task_is_blocked() -> None:
    set_pending_task(whatsapp_message_task("Rahim", "WhatsApp Rahim draft"))
    response = service.handle_chat_message(_request("delete system32"))
    assert response.status == "blocked"
    assert response.intent == "blocked_dangerous"
    assert get_pending_task() is not None


def test_location_pending_status_is_returned() -> None:
    response = service.handle_chat_message(_request("my location"))
    assert response.status == "needs_permission"
    assert response.pending_task is not None
    assert response.pending_task.kind == "location_permission"


def test_pending_task_expires_and_clears() -> None:
    set_pending_task(
        PendingTask(
            kind="whatsapp_message_text",
            prompt="Need message",
            status_label="Waiting for message text",
            recipient="Rahim",
            expires_at="2000-01-01T00:00:00+00:00",
        )
    )
    assert get_pending_task() is None

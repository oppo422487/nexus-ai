"""Pending task state machine for local assistant continuations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import os
from threading import Lock
from typing import Any

DEFAULT_SESSION_ID = "local"
DEFAULT_TTL_MINUTES = int(os.getenv("NEXA_PENDING_TASK_TTL_MINUTES", "30"))
CANCEL_WORDS = {"cancel", "stop", "bad dao", "baad dao", "বাদ দাও", "থামো"}
CONFIRM_WORDS = {
    "confirm",
    "yes",
    "ok",
    "okay",
    "proceed",
    "do it",
    "হ্যাঁ",
    "হ্যাঁ করো",
    "হ্যাঁ করুন",
    "ঠিক আছে",
    "অনুমতি দিলাম",
    "করো",
    "করুন",
}


@dataclass
class PendingTask:
    kind: str
    prompt: str
    status_label: str
    recipient: str | None = None
    message: str | None = None
    topic: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(
        default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_TTL_MINUTES)).isoformat()
    )

    def expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current >= datetime.fromisoformat(self.expires_at)


_TASKS: dict[str, PendingTask] = {}
_LOCK = Lock()


def set_pending_task(task: PendingTask, session_id: str = DEFAULT_SESSION_ID) -> PendingTask:
    with _LOCK:
        _TASKS[session_id] = task
        return task


def get_pending_task(session_id: str = DEFAULT_SESSION_ID) -> PendingTask | None:
    with _LOCK:
        task = _TASKS.get(session_id)
        if task and task.expired():
            _TASKS.pop(session_id, None)
            return None
        return task


def clear_pending_task(session_id: str = DEFAULT_SESSION_ID) -> None:
    with _LOCK:
        _TASKS.pop(session_id, None)


def is_cancel_message(message: str) -> bool:
    normalized = " ".join((message or "").strip().lower().split())
    return normalized in CANCEL_WORDS


def is_confirm_message(message: str) -> bool:
    normalized = " ".join((message or "").strip().lower().split())
    return normalized in CONFIRM_WORDS


def pending_snapshot(session_id: str = DEFAULT_SESSION_ID) -> dict[str, Any] | None:
    task = get_pending_task(session_id)
    return asdict(task) if task else None


def whatsapp_number_task(recipient: str, message: str, original_text: str) -> PendingTask:
    return PendingTask(
        kind="whatsapp_contact_number",
        prompt=f"Need phone number for {recipient}",
        status_label=f"Waiting for {recipient}'s phone number",
        recipient=recipient,
        message=message,
        data={"original_text": original_text},
    )


def whatsapp_message_task(recipient: str, original_text: str) -> PendingTask:
    return PendingTask(
        kind="whatsapp_message_text",
        prompt=f"Need WhatsApp message for {recipient}",
        status_label="Waiting for message text",
        recipient=recipient,
        data={"original_text": original_text},
    )


def app_planning_task(original_text: str) -> PendingTask:
    return PendingTask(
        kind="app_planning_details",
        prompt="Need platform and main features",
        status_label="Waiting for app/project details",
        topic="app_planning",
        data={"original_text": original_text},
    )


def llm_generation_task(original_text: str) -> PendingTask:
    return PendingTask(
        kind="llm_generation_details",
        prompt="Need technology/style details",
        status_label="Waiting for generation details",
        topic="llm_generation",
        data={"original_text": original_text},
    )


def file_summary_task(original_text: str) -> PendingTask:
    return PendingTask(
        kind="file_summary_file",
        prompt="Need PDF upload or file selection",
        status_label="Waiting for PDF upload/selection",
        topic="file_summary",
        data={"original_text": original_text},
    )


def youtube_query_task(original_text: str) -> PendingTask:
    return PendingTask(
        kind="youtube_search_query",
        prompt="Need YouTube search query",
        status_label="Waiting for YouTube search query",
        topic="youtube",
        data={"original_text": original_text},
    )


def location_permission_task(original_text: str) -> PendingTask:
    return PendingTask(
        kind="location_permission",
        prompt="Need browser/device location permission",
        status_label="Waiting for location permission",
        topic="location",
        data={"original_text": original_text},
    )


def action_confirmation_task(
    *,
    action_kind: str,
    target: str,
    label: str,
    original_text: str,
) -> PendingTask:
    return PendingTask(
        kind="action_confirmation",
        prompt=f"Confirm opening {label}",
        status_label=f"Waiting for confirmation: {label}",
        topic="safe_action",
        data={
            "action_kind": action_kind,
            "target": target,
            "label": label,
            "original_text": original_text,
        },
    )


def email_confirmation_task(*, recipient: str, contact_name: str, subject: str, body: str) -> PendingTask:
    return PendingTask(
        kind="email_send_confirmation",
        prompt="Confirm sending the displayed email draft",
        status_label=f"Waiting for email confirmation: {contact_name}",
        recipient=recipient,
        message=body,
        topic="email",
        data={"contact_name": contact_name, "subject": subject, "body": body},
    )

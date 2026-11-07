"""Assistant request state helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.assistant.types import AssistantContext
from app.memory.context_store import ConversationContext, get_context
from app.memory.pending_tasks import PendingTask, get_pending_task
from app.nlu.normalizer import detect_language_style, normalize_text


@dataclass
class AssistantState:
    context: ConversationContext
    pending_task: PendingTask | None = None


def build_context(message: str, *, address_style: str | None = None, history: list | None = None) -> AssistantContext:
    normalized = normalize_text(message)
    language_style = detect_language_style(message, normalized)
    return AssistantContext(
        message=message,
        normalized=normalized,
        address_style=address_style,
        language_style=language_style,
        history=list(history or []),
    )


def load_state(session_id: str = "local") -> AssistantState:
    return AssistantState(context=get_context(session_id), pending_task=get_pending_task(session_id))

"""Local short-term conversation memory for Nexa AI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

MAX_MESSAGES = 10
DEFAULT_SESSION_ID = "local"


@dataclass
class ConversationTurn:
    role: str
    content: str
    intent: str | None = None
    route: str | None = None
    topic: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConversationContext:
    messages: list[ConversationTurn] = field(default_factory=list)
    last_intent: str | None = None
    last_route: str | None = None
    last_topic: str | None = None
    last_assistant_question: str | None = None
    language_style: str | None = None
    address_style: str | None = None


_STORE: dict[str, ConversationContext] = {}
_LOCK = Lock()


def get_context(session_id: str = DEFAULT_SESSION_ID) -> ConversationContext:
    with _LOCK:
        return _STORE.setdefault(session_id, ConversationContext())


def clear_context(session_id: str = DEFAULT_SESSION_ID) -> None:
    with _LOCK:
        _STORE.pop(session_id, None)


def remember_turn(
    role: str,
    content: str,
    *,
    intent: str | None = None,
    route: str | None = None,
    topic: str | None = None,
    assistant_question: str | None = None,
    language_style: str | None = None,
    address_style: str | None = None,
    session_id: str = DEFAULT_SESSION_ID,
) -> ConversationContext:
    with _LOCK:
        context = _STORE.setdefault(session_id, ConversationContext())
        context.messages.append(ConversationTurn(role=role, content=content, intent=intent, route=route, topic=topic))
        context.messages = context.messages[-MAX_MESSAGES:]
        if intent:
            context.last_intent = intent
        if route:
            context.last_route = route
        if topic:
            context.last_topic = topic
        if assistant_question:
            context.last_assistant_question = assistant_question
        if language_style:
            context.language_style = language_style
        if address_style:
            context.address_style = address_style
        return context


def last_user_messages(history: list, limit: int = 4) -> list[str]:
    result: list[str] = []
    for item in reversed(history[-limit:]):
        if getattr(item, "role", "") == "user":
            result.append(getattr(item, "content", "") or "")
    return list(reversed(result))


def context_snapshot(session_id: str = DEFAULT_SESSION_ID) -> dict[str, Any]:
    context = get_context(session_id)
    data = asdict(context)
    data["messages"] = [asdict(item) for item in context.messages]
    return data

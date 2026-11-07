"""Human-facing response composition helpers.

All final user-facing assistant text should pass through this module so address
style, language style, and action wording stay consistent across tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.assistant.persona import address_label, prepend_address
from app.assistant.templates import pick_template
from app.assistant.tone import resolve_language_style


@dataclass
class ComposerInput:
    intent: str
    route: str = "local"
    action_status: str | None = None
    address_style: str | None = None
    language_style: str | None = None
    user_message: str = ""
    tool_result: Any | None = None
    llm_result: Any | None = None
    search_result: Any | None = None
    error: str | None = None
    clarification_type: str | None = None
    values: dict[str, Any] = field(default_factory=dict)
    history_count: int = 0


def compose_from_input(data: ComposerInput) -> str:
    language_style = resolve_language_style(data.user_message, data.language_style)
    if data.error:
        return prepend_address(data.error, data.address_style, language_style)
    text = pick_template(data.intent, language_style, data.history_count, **data.values)
    return prepend_address(text, data.address_style, language_style)


def compose_intent(
    intent: str,
    *,
    address_style: str | None = None,
    language_style: str | None = None,
    user_message: str = "",
    history_count: int = 0,
    **values: Any,
) -> str:
    return compose_from_input(
        ComposerInput(
            intent=intent,
            address_style=address_style,
            language_style=language_style,
            user_message=user_message,
            values=values,
            history_count=history_count,
        )
    )


def compose(text: str, address_style: str | None = None, language_style: str = "mixed") -> str:
    return prepend_address(text, address_style, language_style)


__all__ = [
    "ComposerInput",
    "address_label",
    "compose",
    "compose_from_input",
    "compose_intent",
]

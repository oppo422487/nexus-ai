"""Safety router facade."""

from __future__ import annotations

from app.actions.safety import contains_dangerous_keyword


def is_dangerous(message: str) -> bool:
    return contains_dangerous_keyword(message)


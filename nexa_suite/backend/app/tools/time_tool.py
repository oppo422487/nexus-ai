"""Current-time tool facade."""

from __future__ import annotations


def answer_current_time(message: str) -> tuple[str, str]:
    from app.chat.service import current_time_answer

    return current_time_answer(message)


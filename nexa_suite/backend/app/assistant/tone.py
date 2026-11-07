"""Language-style and tone helpers for human response composition."""

from __future__ import annotations

from app.nlu.normalizer import detect_language_style, normalize_text


def resolve_language_style(user_message: str | None, language_style: str | None = None) -> str:
    if language_style in {"bangla", "banglish", "english", "mixed"}:
        return language_style
    return detect_language_style(user_message or "", normalize_text(user_message or ""))


def is_banglish_like(language_style: str) -> bool:
    return language_style in {"bangla", "banglish", "mixed"}

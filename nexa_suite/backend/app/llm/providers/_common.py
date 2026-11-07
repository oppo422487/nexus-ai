"""Common helpers for hosted LLM providers."""

from __future__ import annotations

import os

import httpx

from app.llm.schemas import LLMRequest


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def timeout_seconds() -> float:
    raw = env("NEXA_LLM_TIMEOUT_SECONDS", "20")
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 20.0


def user_prompt(request: LLMRequest) -> str:
    if request.context:
        return f"Source/context:\n{request.context}\n\nUser request:\n{request.message}"
    return request.message


def post_json(url: str, *, headers: dict[str, str], payload: dict) -> dict | None:
    response = httpx.post(url, headers=headers, json=payload, timeout=timeout_seconds())
    if response.status_code >= 400:
        return None
    data = response.json()
    return data if isinstance(data, dict) else None


def first_choice_text(data: dict) -> str | None:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    text = first.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def openai_messages(request: LLMRequest) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": request.system_prompt},
        {"role": "user", "content": user_prompt(request)},
    ]

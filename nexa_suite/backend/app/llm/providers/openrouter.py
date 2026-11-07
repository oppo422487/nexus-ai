"""OpenRouter hosted LLM provider."""

from __future__ import annotations

from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.providers._common import env, first_choice_text, openai_messages, post_json


def complete(request: LLMRequest) -> LLMResponse | None:
    key = env("OPENROUTER_API_KEY")
    if not key:
        return None
    model = env("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    data = post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        payload={"model": model, "messages": openai_messages(request), "max_tokens": request.max_tokens},
    )
    text = first_choice_text(data or {})
    return LLMResponse(answer=text, provider="OpenRouter", model=model) if text else None

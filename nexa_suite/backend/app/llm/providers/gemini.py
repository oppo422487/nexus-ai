"""Gemini hosted LLM provider."""

from __future__ import annotations

from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.providers._common import env, post_json, user_prompt


def complete(request: LLMRequest) -> LLMResponse | None:
    key = env("GEMINI_API_KEY")
    if not key:
        return None
    model = env("GEMINI_MODEL", "gemini-3.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "systemInstruction": {"parts": [{"text": request.system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt(request)}]}],
        "generationConfig": {"maxOutputTokens": request.max_tokens},
    }
    data = post_json(url, headers={"Content-Type": "application/json"}, payload=payload)
    candidates = (data or {}).get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    return LLMResponse(answer=text, provider="Gemini", model=model) if text else None

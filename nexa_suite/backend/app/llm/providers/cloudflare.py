"""Cloudflare Workers AI hosted provider."""

from __future__ import annotations

from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.providers._common import env, openai_messages, post_json


def complete(request: LLMRequest) -> LLMResponse | None:
    account_id = env("CLOUDFLARE_ACCOUNT_ID")
    token = env("CLOUDFLARE_API_TOKEN")
    if not account_id or not token:
        return None
    model = env("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    data = post_json(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        payload={"messages": openai_messages(request), "max_tokens": request.max_tokens},
    )
    result = (data or {}).get("result")
    text = result.get("response") if isinstance(result, dict) else None
    return LLMResponse(answer=text.strip(), provider="Cloudflare Workers AI", model=model) if isinstance(text, str) and text.strip() else None

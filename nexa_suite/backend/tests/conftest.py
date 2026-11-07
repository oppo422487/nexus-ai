from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_external_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep backend tests deterministic when the developer has real API keys."""

    for key in (
        "NEXA_LLM_ROUTER_ENABLED",
        "NEXA_LLM_PRIMARY",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_MODEL",
        "MISTRAL_API_KEY",
        "MISTRAL_MODEL",
        "CEREBRAS_API_KEY",
        "CEREBRAS_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

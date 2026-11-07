"""Hosted LLM provider router for Nexa AI.

The router is opt-in and never receives credentials directly from source code.
Providers are tried in a fixed safe order and return only the provider name used,
not API keys or request headers.
"""

from __future__ import annotations

import os

from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.providers import cerebras, cloudflare, gemini, groq, mistral, openrouter

PROVIDER_ORDER = ("gemini", "groq", "openrouter", "cloudflare", "mistral", "cerebras")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def router_enabled() -> bool:
    return _env_bool("NEXA_LLM_ROUTER_ENABLED", False)


def build_system_prompt(address_style: str | None = None, language_style: str = "english") -> str:
    address = (address_style or "Boss").strip() or "Neutral"
    language_rule = {
        "bangla": "Reply entirely in natural Bengali script unless the user explicitly requests another language.",
        "english": "Reply entirely in English unless the user explicitly requests another language.",
    }.get(language_style, "Answer in the user's language style: Bangla, Banglish, or English.")
    return (
        "You are Nexa AI, a respectful personal desktop assistant. "
        f"{language_rule} "
        f"Use this address style naturally when appropriate: {address}. "
        "Do not claim live/current data unless source context is provided. "
        "Do not execute actions, open apps, send WhatsApp messages, bypass login, scrape credentials, "
        "or weaken safety rules. For WhatsApp, compose draft text only; the user must send manually. "
        "If source context is provided, summarize it without inventing missing values."
    )


def _ordered_provider_names() -> list[str]:
    primary = (os.getenv("NEXA_LLM_PRIMARY") or "gemini").strip().lower()
    names = [primary] if primary in PROVIDER_ORDER else ["gemini"]
    names.extend(name for name in PROVIDER_ORDER if name not in names)
    return names


def _call_provider(name: str, request: LLMRequest) -> LLMResponse | None:
    if name == "gemini":
        return gemini.complete(request)
    if name == "groq":
        return groq.complete(request)
    if name == "openrouter":
        return openrouter.complete(request)
    if name == "cloudflare":
        return cloudflare.complete(request)
    if name == "mistral":
        return mistral.complete(request)
    if name == "cerebras":
        return cerebras.complete(request)
    return None


def complete(message: str, *, address_style: str | None = None, language_style: str = "english", context: str | None = None) -> LLMResponse | None:
    if not router_enabled():
        return None
    request = LLMRequest(
        message=message,
        system_prompt=build_system_prompt(address_style, language_style),
        address_style=address_style,
        language_style=language_style,
        context=context,
    )
    for index, provider_name in enumerate(_ordered_provider_names()):
        try:
            result = _call_provider(provider_name, request)
        except Exception:
            result = None
        if result and result.answer.strip():
            result.fallback_used = index > 0
            return result
    return None

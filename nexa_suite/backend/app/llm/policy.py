"""Policy for deciding when Nexa should use hosted LLMs."""

from __future__ import annotations

import re


LOCAL_ONLY_INTENTS = {
    "greeting",
    "thanks",
    "capabilities",
    "user_frustration",
    "casual_chat",
    "normal_chat",
    "weather",
    "current_time",
    "youtube_skill",
    "youtube_open",
    "youtube_search",
    "whatsapp_open",
    "app_open_request",
    "contact_command",
    "blocked_dangerous",
}

LIVE_MARKERS = {
    "latest",
    "today",
    "current",
    "news",
    "gold price",
    "silver price",
    "dollar rate",
    "exchange rate",
    "stock price",
    "bitcoin price",
    "fuel price",
    "weather",
}

LLM_MARKERS = {
    "write code",
    "code",
    "debug",
    "bug fix",
    "explain",
    "why",
    "how to",
    "generate",
    "homepage",
    "landing page",
    "page design",
    "math",
    "solve",
    "rewrite",
    "formal",
    "friendly",
    "compose",
    "email",
    "paragraph",
    "essay",
    "summary",
    "summarize",
    "complex",
}

SIMPLE_ARITHMETIC_RE = re.compile(r"^\s*\d+(\s*[-+*/]\s*\d+)+\s*$")


def normalize_policy_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def should_use_llm(message: str, intent: str, confidence: str | None = None) -> str:
    """Return use_local, use_search, use_tool, use_llm, or use_llm_after_search."""
    text = normalize_policy_text(message)
    if intent == "blocked_dangerous":
        return "use_tool"
    if intent in {"weather", "current_time", "youtube_skill", "youtube_open", "youtube_search", "whatsapp_open", "app_open_request", "contact_command"}:
        return "use_tool"
    if intent in {"greeting", "thanks", "capabilities", "user_frustration", "casual_chat", "normal_chat"}:
        return "use_local"
    if intent in {"web_search", "market_search"}:
        return "use_llm_after_search" if any(marker in text for marker in LIVE_MARKERS) else "use_search"
    if intent == "translation" and len(text) < 180:
        return "use_local"
    if SIMPLE_ARITHMETIC_RE.match(text):
        return "use_local"
    if any(marker in text for marker in LIVE_MARKERS):
        return "use_llm_after_search"
    if any(marker in text for marker in LLM_MARKERS):
        return "use_llm"
    if confidence == "low":
        return "use_llm"
    return "use_local"


def whatsapp_draft_needs_llm(message: str) -> bool:
    text = normalize_policy_text(message)
    return any(marker in text for marker in ("formal", "friendly", "professional", "shundor kore", "valo kore"))

"""Shared schemas for hosted LLM routing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LLMRequest:
    message: str
    system_prompt: str
    address_style: str | None = None
    language_style: str = "english"
    context: str | None = None
    max_tokens: int = 700


@dataclass
class LLMResponse:
    answer: str
    provider: str
    model: str | None = None
    fallback_used: bool = False


@dataclass
class LLMRoutingDecision:
    mode: str
    reason: str
    llm_allowed: bool = False
    needs_search_first: bool = False
    labels: list[str] = field(default_factory=list)

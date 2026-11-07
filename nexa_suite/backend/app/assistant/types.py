"""Shared assistant pipeline types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssistantRoute:
    intent: str
    confidence: str
    route: str
    reason: str
    needs_action: bool = False
    needs_llm: bool = False
    needs_search: bool = False
    needs_confirmation: bool = False


@dataclass
class AssistantContext:
    message: str
    normalized: str
    address_style: str | None = None
    language_style: str = "english"
    history: list[Any] = field(default_factory=list)


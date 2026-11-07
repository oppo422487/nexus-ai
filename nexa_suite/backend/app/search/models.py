"""Shared search provider result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SearchProviderResult:
    title: str
    snippet: str
    source_url: str | None
    provider: str
    confidence: str = "medium"


@dataclass
class SearchAnswer:
    answer: str
    provider: str
    source_url: str | None = None
    results: list[SearchProviderResult] = field(default_factory=list)
    exact: bool = False
    confidence: str = "medium"
    live_data: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None

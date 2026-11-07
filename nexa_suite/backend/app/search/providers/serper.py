"""Serper.dev provider for Google-like search results.

The API key is read only from SERPER_API_KEY. It must never be hard-coded.
"""

from __future__ import annotations

import os

import httpx

from app.search.models import SearchAnswer, SearchProviderResult

SERPER_ENDPOINT = "https://google.serper.dev/search"
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_RESULTS = 6


def _api_key() -> str:
    return (os.getenv("SERPER_API_KEY") or "").strip()


def _text(value: object) -> str:
    return str(value or "").strip()


def _result(title: object, snippet: object, link: object, confidence: str = "medium") -> SearchProviderResult | None:
    clean_title = _text(title)
    if not clean_title:
        return None
    return SearchProviderResult(
        title=clean_title,
        snippet=_text(snippet)[:600],
        source_url=_text(link) or None,
        provider="Serper.dev",
        confidence=confidence,
    )


def _append_result(results: list[SearchProviderResult], item: SearchProviderResult | None) -> None:
    if item is None or len(results) >= MAX_RESULTS:
        return
    if item.source_url and any(existing.source_url == item.source_url for existing in results):
        return
    results.append(item)


def _answer_from_answer_box(answer_box: dict) -> tuple[str, str | None] | None:
    title = _text(answer_box.get("title"))
    answer = _text(answer_box.get("answer") or answer_box.get("snippet") or answer_box.get("snippetHighlighted"))
    link = _text(answer_box.get("link"))
    if answer:
        prefix = f"{title}: " if title else ""
        return prefix + answer, link or None
    return None


def _answer_from_knowledge_graph(knowledge_graph: dict) -> tuple[str, str | None] | None:
    title = _text(knowledge_graph.get("title"))
    description = _text(knowledge_graph.get("description"))
    link = _text(knowledge_graph.get("website") or knowledge_graph.get("sourceUrl"))
    if title and description:
        return f"{title}: {description}", link or None
    if description:
        return description, link or None
    return None


def serper_search(query: str) -> SearchAnswer | None:
    key = _api_key()
    if not key:
        return None

    try:
        response = httpx.post(
            SERPER_ENDPOINT,
            json={"q": query, "gl": "bd", "hl": "en", "num": 10},
            headers={
                "X-API-KEY": key,
                "Content-Type": "application/json",
                "User-Agent": "NexaAI-Desktop-Assistant/1.0",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        if not isinstance(data, dict):
            return None
    except Exception:
        return None

    results: list[SearchProviderResult] = []

    answer_box = data.get("answerBox")
    if isinstance(answer_box, dict):
        boxed = _answer_from_answer_box(answer_box)
        _append_result(
            results,
            _result(
                answer_box.get("title") or "Serper answer box",
                answer_box.get("answer") or answer_box.get("snippet"),
                answer_box.get("link"),
                "high",
            ),
        )
        if boxed:
            answer, link = boxed
            return SearchAnswer(
                answer=answer,
                provider="Serper.dev",
                source_url=link,
                results=results,
                exact=True,
                confidence="high",
            )

    knowledge_graph = data.get("knowledgeGraph")
    if isinstance(knowledge_graph, dict):
        kg_answer = _answer_from_knowledge_graph(knowledge_graph)
        _append_result(
            results,
            _result(
                knowledge_graph.get("title") or "Serper knowledge graph",
                knowledge_graph.get("description"),
                knowledge_graph.get("website") or knowledge_graph.get("sourceUrl"),
                "high",
            ),
        )
        if kg_answer:
            answer, link = kg_answer
            return SearchAnswer(
                answer=answer,
                provider="Serper.dev",
                source_url=link,
                results=results,
                exact=True,
                confidence="high",
            )

    for key_name in ("organic", "topStories", "news", "places"):
        rows = data.get(key_name)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            _append_result(
                results,
                _result(
                    row.get("title") or row.get("name"),
                    row.get("snippet") or row.get("description") or row.get("address"),
                    row.get("link") or row.get("website"),
                    "medium",
                ),
            )

    if not results:
        return None

    top = results[0]
    return SearchAnswer(
        answer=f"I found related Serper.dev sources for '{query}'. Top result: {top.title}. {top.snippet}",
        provider="Serper.dev",
        source_url=top.source_url,
        results=results,
        exact=False,
        confidence="medium",
    )

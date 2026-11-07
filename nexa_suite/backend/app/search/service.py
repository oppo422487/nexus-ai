"""Safe search provider abstraction.

Default mode is free/no-key. Optional providers are only used when configured
through environment variables and never scrape Google HTML directly.
"""

from __future__ import annotations

import os
import re
import urllib.parse

import httpx

from app.schemas.chat import ChatSearchResult
from app.search.models import SearchAnswer, SearchProviderResult
from app.search.providers import serper_search

REQUEST_TIMEOUT_SECONDS = 8.0
MAX_RESULTS = 4

ALLOWED_HOSTS = {
    "api.duckduckgo.com",
    "en.wikipedia.org",
    "bn.wikipedia.org",
    "api.search.brave.com",
    "www.googleapis.com",
    "serpapi.com",
}

MARKET_KEYWORDS = {
    "gold price",
    "gold prize",
    "silver price",
    "dollar rate",
    "exchange rate",
    "stock price",
    "bitcoin price",
    "btc price",
    "fuel price",
    "oil price",
    "market price",
    "latest news",
    "news today",
}

VALUE_RE = re.compile(
    r"(?:(?:৳|bdt|tk|rs|usd|\$)\s?\d[\d,]*(?:\.\d+)?)|(?:\d[\d,]*(?:\.\d+)?\s?(?:bdt|tk|taka|usd|dollars?|per gram|gram|ভরি|vori|ounce|oz|%))",
    re.IGNORECASE,
)


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def is_market_query(query: str) -> bool:
    normalized = " ".join((query or "").lower().split())
    return any(keyword in normalized for keyword in MARKET_KEYWORDS)


def _source_label(result: SearchProviderResult) -> str:
    if result.title:
        return result.title[:80]
    if result.source_url:
        host = urllib.parse.urlparse(result.source_url).hostname or result.source_url
        return host[:80]
    return result.provider


def _extract_values(text: str) -> list[str]:
    values: list[str] = []
    for match in VALUE_RE.finditer(text or ""):
        value = match.group(0).strip()
        if value and value not in values:
            values.append(value)
        if len(values) >= 4:
            break
    return values


def _same_language_hint(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ("koto", "ajker", "bangladesh e", "ki", "koto taka")):
        return "mixed"
    return "english"


def synthesize_related_answer(query: str, result: SearchAnswer, live_data: bool) -> SearchAnswer:
    if not result.results:
        return result

    top_sources = result.results[:3]
    source_names = [_source_label(item) for item in top_sources]
    combined_snippets = " ".join(item.snippet for item in top_sources if item.snippet)
    values = _extract_values(combined_snippets)
    style = _same_language_hint(query)

    if live_data:
        if values:
            if len(set(values)) > 1:
                value_text = ", ".join(values[:4])
                if style == "mixed":
                    answer = (
                        f"Latest sources show different live values for {query}: {value_text}. "
                        f"Prices/rates source-er upor vary korte pare, so buying/selling er age official source verify korun. "
                        f"Sources checked: {', '.join(source_names)}."
                    )
                else:
                    answer = (
                        f"Latest sources show varying live values for {query}: {value_text}. "
                        f"Prices or rates may differ by source, purity, location, and update time, so verify with an official source before acting. "
                        f"Sources checked: {', '.join(source_names)}."
                    )
            else:
                value_text = values[0]
                answer = (
                    f"The latest source snippets indicate {query} is around {value_text}, but live market values can change quickly. "
                    f"Verify with the listed source before acting. Source checked: {source_names[0]}."
                )
        else:
            answer = (
                f"I found related live sources for {query}, but could not verify one exact live price. "
                f"Prices/rates may vary by source and update time. Sources checked: {', '.join(source_names)}."
            )
        result.answer = answer
        result.confidence = "medium" if values else "low"
        return result

    top = top_sources[0]
    result.answer = (
        f"Here is the best answer I found for {query}: {top.title}. "
        f"{top.snippet or 'The listed sources have more detail.'} "
        f"Sources checked: {', '.join(source_names)}."
    )
    return result


def clean_search_query(message: str) -> str:
    cleaned = " ".join((message or "").strip().split())
    lower = cleaned.lower()
    replacements = [
        r"\bgoogle theke search kore bolo\b",
        r"\bgoogle e khuje bolo\b",
        r"\bgoogle e khujte paro\b",
        r"\bsearch kore bolo\b",
        r"খুঁজে বলো",
        r"বলে দাও",
        r"\bgoogle theke\b",
        r"\bgoogle\b",
        r"\bsearch\b",
        r"\btheke\b",
        r"\bkhuje bolo\b",
        r"\bkhujte paro\b",
        r"\betar answer ki\b",
        r"\banswer ki\b",
        r"\bbolo\b",
        r"\bplease\b",
        r"\btell me\b",
    ]
    for pattern in replacements:
        lower = re.sub(pattern, " ", lower, flags=re.IGNORECASE)
    lower = re.sub(r"\bbangladesh e\b", "bangladesh", lower)
    lower = re.sub(r"\bajker\b", "today", lower)
    lower = re.sub(r"\bajke\b", "today", lower)
    lower = re.sub(r"\s+", " ", lower).strip()
    return lower or cleaned


def _safe_get_json(url: str, allowed_hosts: set[str] | None = None, headers: dict[str, str] | None = None) -> dict | None:
    host = urllib.parse.urlparse(url).hostname or ""
    if allowed_hosts is not None and host not in allowed_hosts:
        return None
    try:
        response = httpx.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "NexaAI-Desktop-Assistant/1.0", **(headers or {})},
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _chat_results(rows: list[SearchProviderResult]) -> list[ChatSearchResult]:
    return [
        ChatSearchResult(
            title=row.title,
            snippet=row.snippet,
            source_url=row.source_url,
            provider=row.provider,
            confidence=row.confidence,
        )
        for row in rows
    ]


def duckduckgo_instant(query: str) -> SearchAnswer | None:
    encoded = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
    data = _safe_get_json(url, ALLOWED_HOSTS)
    if not data:
        return None

    answer = (data.get("Answer") or "").strip()
    abstract = (data.get("AbstractText") or "").strip()
    definition = (data.get("Definition") or "").strip()
    text = answer or abstract or definition
    source_url = data.get("AbstractURL") or data.get("DefinitionURL") or "https://duckduckgo.com"

    results: list[SearchProviderResult] = []
    topics = data.get("RelatedTopics") or []
    for topic in topics:
        if len(results) >= MAX_RESULTS:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append(
                SearchProviderResult(
                    title=str(topic.get("FirstURL") or "DuckDuckGo related result"),
                    snippet=str(topic["Text"])[:500],
                    source_url=str(topic.get("FirstURL") or "https://duckduckgo.com"),
                    provider="DuckDuckGo Instant Answer",
                    confidence="medium",
                )
            )

    if text:
        return SearchAnswer(
            answer=text[:1200],
            provider="DuckDuckGo Instant Answer",
            source_url=str(source_url),
            results=[
                SearchProviderResult(
                    title="DuckDuckGo Instant Answer",
                    snippet=text[:500],
                    source_url=str(source_url),
                    provider="DuckDuckGo Instant Answer",
                    confidence="high",
                )
            ] + results,
            exact=True,
            confidence="high",
        )

    if results:
        return SearchAnswer(
            answer=f"I found related DuckDuckGo results for '{query}'.",
            provider="DuckDuckGo Related Topics",
            source_url=results[0].source_url,
            results=results,
            exact=False,
            confidence="medium",
        )
    return None


def wikipedia_summary(query: str) -> SearchAnswer | None:
    title = urllib.parse.quote(query.strip().replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    data = _safe_get_json(url, ALLOWED_HOSTS)
    extract = (data or {}).get("extract") if isinstance(data, dict) else None
    if not extract:
        return None
    source_url = ((data or {}).get("content_urls") or {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{title}"
    result = SearchProviderResult(
        title=str((data or {}).get("title") or query),
        snippet=str(extract)[:500],
        source_url=str(source_url),
        provider="Wikipedia Summary",
        confidence="high",
    )
    return SearchAnswer(
        answer=str(extract)[:1200],
        provider="Wikipedia Summary",
        source_url=str(source_url),
        results=[result],
        exact=True,
        confidence="high",
    )


def wikipedia_search(query: str) -> SearchAnswer | None:
    encoded = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": "1",
            "srlimit": str(MAX_RESULTS),
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{encoded}"
    data = _safe_get_json(url, ALLOWED_HOSTS)
    rows = ((data or {}).get("query") or {}).get("search") or []
    results: list[SearchProviderResult] = []
    for row in rows[:MAX_RESULTS]:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        snippet = re.sub("<[^>]+>", "", str(row.get("snippet") or "")).strip()
        page = urllib.parse.quote(title.replace(" ", "_"))
        results.append(
            SearchProviderResult(
                title=title,
                snippet=snippet,
                source_url=f"https://en.wikipedia.org/wiki/{page}",
                provider="Wikipedia Search",
                confidence="medium",
            )
        )
    if not results:
        return None
    top = results[0]
    return SearchAnswer(
        answer=f"I found related public sources for '{query}'. Top result: {top.title}. {top.snippet}",
        provider="Wikipedia Search",
        source_url=top.source_url,
        results=results,
        exact=False,
        confidence="medium",
    )


def searxng_search(query: str) -> SearchAnswer | None:
    base_url = _env("NEXA_SEARXNG_URL")
    if not base_url:
        return None
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    url = f"{base_url.rstrip('/')}/search?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"
    data = _safe_get_json(url, None)
    rows = (data or {}).get("results") or []
    results: list[SearchProviderResult] = []
    for row in rows[:MAX_RESULTS]:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        results.append(
            SearchProviderResult(
                title=title,
                snippet=str(row.get("content") or row.get("snippet") or "")[:500],
                source_url=str(row.get("url") or ""),
                provider="SearXNG",
                confidence="medium",
            )
        )
    if not results:
        return None
    return SearchAnswer(
        answer=f"I found related SearXNG results for '{query}'. Top result: {results[0].title}. {results[0].snippet}",
        provider="SearXNG",
        source_url=results[0].source_url,
        results=results,
        exact=False,
        confidence="medium",
    )


def google_cse_search(query: str) -> SearchAnswer | None:
    key = _env("NEXA_GOOGLE_CSE_KEY")
    cx = _env("NEXA_GOOGLE_CSE_ID")
    if not key or not cx:
        return None
    url = "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode({"key": key, "cx": cx, "q": query})
    data = _safe_get_json(url, ALLOWED_HOSTS)
    rows = (data or {}).get("items") or []
    results = [
        SearchProviderResult(
            title=str(row.get("title") or ""),
            snippet=str(row.get("snippet") or "")[:500],
            source_url=str(row.get("link") or ""),
            provider="Google Custom Search",
            confidence="medium",
        )
        for row in rows[:MAX_RESULTS]
        if row.get("title")
    ]
    if not results:
        return None
    return SearchAnswer(
        answer=f"I found related Google Custom Search results for '{query}'. Top result: {results[0].title}. {results[0].snippet}",
        provider="Google Custom Search",
        source_url=results[0].source_url,
        results=results,
        exact=False,
        confidence="medium",
    )


def brave_search(query: str) -> SearchAnswer | None:
    key = _env("NEXA_BRAVE_SEARCH_KEY")
    if not key:
        return None
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": MAX_RESULTS})
    data = _safe_get_json(url, ALLOWED_HOSTS, headers={"X-Subscription-Token": key})
    rows = ((data or {}).get("web") or {}).get("results") or []
    results = [
        SearchProviderResult(
            title=str(row.get("title") or ""),
            snippet=str(row.get("description") or "")[:500],
            source_url=str(row.get("url") or ""),
            provider="Brave Search",
            confidence="medium",
        )
        for row in rows[:MAX_RESULTS]
        if row.get("title")
    ]
    if not results:
        return None
    return SearchAnswer(
        answer=f"I found related Brave Search results for '{query}'. Top result: {results[0].title}. {results[0].snippet}",
        provider="Brave Search",
        source_url=results[0].source_url,
        results=results,
        exact=False,
        confidence="medium",
    )


def serpapi_search(query: str) -> SearchAnswer | None:
    key = _env("NEXA_SERPAPI_KEY")
    if not key:
        return None
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode({"q": query, "api_key": key, "engine": "google"})
    data = _safe_get_json(url, ALLOWED_HOSTS)
    rows = (data or {}).get("organic_results") or []
    results = [
        SearchProviderResult(
            title=str(row.get("title") or ""),
            snippet=str(row.get("snippet") or "")[:500],
            source_url=str(row.get("link") or ""),
            provider="SerpAPI",
            confidence="medium",
        )
        for row in rows[:MAX_RESULTS]
        if row.get("title")
    ]
    if not results:
        return None
    return SearchAnswer(
        answer=f"I found related SerpAPI results for '{query}'. Top result: {results[0].title}. {results[0].snippet}",
        provider="SerpAPI",
        source_url=results[0].source_url,
        results=results,
        exact=False,
        confidence="medium",
    )


def _ordered_providers() -> list:
    mode = (_env("NEXA_SEARCH_PROVIDER") or "free").lower()
    free = [duckduckgo_instant, wikipedia_summary, wikipedia_search]
    optional = {
        "serper": [serper_search],
        "searxng": [searxng_search],
        "google_cse": [google_cse_search],
        "brave": [brave_search],
        "serpapi": [serpapi_search],
    }
    if mode == "free":
        return free
    return optional.get(mode, []) + free


def search_answer(raw_query: str) -> SearchAnswer:
    query = clean_search_query(raw_query)
    live_data = is_market_query(query)
    first_related: SearchAnswer | None = None

    for provider in _ordered_providers():
        result = provider(query)
        if result is None:
            continue
        result.live_data = live_data
        if result.exact:
            if live_data:
                result.answer = (
                    f"{result.answer}\n\nLive market data may change. "
                    f"Verify the value from the listed source before acting on it."
                )
            return result
        if first_related is None:
            first_related = result

    if first_related is not None:
        first_related.live_data = live_data
        return synthesize_related_answer(query, first_related, live_data)

    if live_data:
        return SearchAnswer(
            answer=(
                "I found related live sources for "
                f"{query}, but could not verify one exact live price. "
                "Prices/rates may vary by source and update time. "
                "Live market data may change; try enabling SearXNG or an API-key provider for stronger results."
            ),
            provider="Configured safe search providers",
            exact=False,
            confidence="low",
            live_data=True,
            error="No provider returned related market data.",
        )

    return SearchAnswer(
        answer=(
            "I could not find useful related sources from the configured safe providers. "
            "Try a more specific query or configure SearXNG/Google CSE/Brave/SerpAPI."
        ),
        provider="Configured safe search providers",
        exact=False,
        confidence="low",
        error="No provider returned results.",
    )


def to_chat_results(results: list[SearchProviderResult]) -> list[ChatSearchResult]:
    return _chat_results(results)

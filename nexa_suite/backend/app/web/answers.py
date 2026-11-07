"""Safe web answer service.

Only fixed, whitelisted public APIs are contacted:
- DuckDuckGo Instant Answer API
- Wikipedia REST summary (English and Bangla)

No scraping, no arbitrary URLs, no browsing. Answering a question never
opens a website or executes any action.
"""

from __future__ import annotations

import re
import urllib.parse

import httpx

ALLOWED_HOSTS = {"api.duckduckgo.com", "en.wikipedia.org", "bn.wikipedia.org"}
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_QUESTION_LENGTH = 300
MAX_ANSWER_LENGTH = 1200

_BANGLA_RE = re.compile(r"[ঀ-৿]")


def _contains_bangla(text: str) -> bool:
    return bool(_BANGLA_RE.search(text))


def _safe_get(url: str) -> httpx.Response | None:
    host = urllib.parse.urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        return None
    try:
        response = httpx.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "NexaAI-Desktop-Assistant/1.0"},
        )
        if response.status_code == 200:
            return response
    except Exception:
        return None
    return None


def _ask_duckduckgo(question: str) -> dict | None:
    encoded = urllib.parse.quote(question)
    url = (
        f"https://api.duckduckgo.com/?q={encoded}"
        "&format=json&no_html=1&skip_disambig=1"
    )
    response = _safe_get(url)
    if response is None:
        return None
    try:
        data = response.json()
    except Exception:
        return None

    answer = (data.get("Answer") or "").strip()
    abstract = (data.get("AbstractText") or "").strip()
    definition = (data.get("Definition") or "").strip()

    text = answer or abstract or definition
    if not text:
        topics = data.get("RelatedTopics") or []
        for topic in topics:
            if isinstance(topic, dict) and topic.get("Text"):
                text = str(topic["Text"]).strip()
                break
    if not text:
        return None

    source_url = (
        data.get("AbstractURL")
        or data.get("DefinitionURL")
        or "https://duckduckgo.com"
    )
    return {
        "text": text[:MAX_ANSWER_LENGTH],
        "source": "DuckDuckGo Instant Answer",
        "source_url": str(source_url),
    }


def _ask_wikipedia(question: str) -> dict | None:
    lang = "bn" if _contains_bangla(question) else "en"
    title = urllib.parse.quote(question.strip().replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    response = _safe_get(url)
    if response is None:
        return None
    try:
        data = response.json()
    except Exception:
        return None
    extract = (data.get("extract") or "").strip()
    if not extract:
        return None
    page_url = (
        (data.get("content_urls") or {}).get("desktop", {}).get("page")
        or f"https://{lang}.wikipedia.org"
    )
    return {
        "text": extract[:MAX_ANSWER_LENGTH],
        "source": f"Wikipedia ({lang})",
        "source_url": str(page_url),
    }


def answer_question(question: str) -> dict:
    """Answer a question through whitelisted public APIs. Never raises."""
    cleaned = (question or "").strip()
    if not cleaned:
        return {
            "status": "failed",
            "answered": False,
            "question": "",
            "answer": "",
            "source": None,
            "source_url": None,
            "error": "Question is empty.",
        }
    if len(cleaned) > MAX_QUESTION_LENGTH:
        cleaned = cleaned[:MAX_QUESTION_LENGTH]

    result = _ask_duckduckgo(cleaned) or _ask_wikipedia(cleaned)
    if result is None:
        return {
            "status": "no_answer",
            "answered": False,
            "question": cleaned,
            "answer": "",
            "source": None,
            "source_url": None,
            "error": (
                "No instant answer was found from the safe sources "
                "(DuckDuckGo/Wikipedia). Try rephrasing the question."
            ),
        }

    return {
        "status": "completed",
        "answered": True,
        "question": cleaned,
        "answer": result["text"],
        "source": result["source"],
        "source_url": result["source_url"],
        "error": None,
    }

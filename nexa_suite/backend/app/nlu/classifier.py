"""Deep Bangla/Banglish/English intent classifier for Nexa AI."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.nlu.banglish import normalize_banglish
from app.nlu.normalizer import detect_language_style, has_phrase_or_token, normalize_text
from app.nlu import patterns


@dataclass
class NLUClassification:
    intent: str
    confidence: float
    route: str
    language_style: str
    entities: dict[str, str] = field(default_factory=dict)
    normalized_text: str = ""
    raw_text: str = ""
    reason: str = ""
    needs_tool: bool = False
    needs_search: bool = False
    needs_llm: bool = False
    needs_action: bool = False
    needs_clarification: bool = False


def _result(
    *,
    intent: str,
    route: str,
    raw_text: str,
    normalized_text: str,
    language_style: str,
    confidence: float = 0.9,
    reason: str = "",
    entities: dict[str, str] | None = None,
    needs_tool: bool = False,
    needs_search: bool = False,
    needs_llm: bool = False,
    needs_action: bool = False,
    needs_clarification: bool = False,
) -> NLUClassification:
    return NLUClassification(
        intent=intent,
        confidence=confidence,
        route=route,
        language_style=language_style,
        entities=entities or {},
        normalized_text=normalized_text,
        raw_text=raw_text,
        reason=reason,
        needs_tool=needs_tool,
        needs_search=needs_search,
        needs_llm=needs_llm,
        needs_action=needs_action,
        needs_clarification=needs_clarification,
    )


def _contains_any(text: str, hints: set[str]) -> bool:
    return any(hint in text for hint in hints)


def _extract_app(text: str) -> str | None:
    for target in patterns.APP_TARGETS:
        if target in text:
            return target
    return None


def _extract_page_kind(text: str) -> str | None:
    for page in ("login page", "homepage", "landing page", "home page", "portfolio website", "react component"):
        if page in text:
            return "homepage" if page == "home page" else page
    return None


def _extract_youtube_query(text: str) -> str:
    query = text
    for token in ("youtube", "e", "te", "open", "khule", "খুলে", "search", "koro", "dao", "play", "chalao", "চালাও"):
        query = re.sub(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", " ", query)
    return " ".join(query.split()) or "youtube"


def _extract_contact_message(text: str) -> tuple[str | None, str | None]:
    match = (
        patterns.WHATSAPP_DRAFT_RE.search(text)
        or patterns.WHATSAPP_DRAFT_ALT_RE.search(text)
        or patterns.CONTACT_MESSAGE_RE.search(text)
    )
    if not match:
        return None, None
    return " ".join(match.group("recipient").strip().split()), " ".join(match.group("message").strip().split())


def _extract_contact_command(text: str) -> tuple[str | None, dict[str, str]]:
    save_match = patterns.CONTACT_SAVE_RE.search(text)
    if save_match:
        return "contact_save", {
            "name": " ".join(save_match.group("name").strip().split()),
            "phone": " ".join(save_match.group("phone").strip().split()),
        }
    delete_match = patterns.CONTACT_DELETE_RE.search(text)
    if delete_match:
        return "contact_delete", {"name": " ".join(delete_match.group("name").strip().split())}
    query_match = patterns.CONTACT_QUERY_RE.search(text)
    if query_match:
        return "contact_lookup", {"name": " ".join(query_match.group("name").strip().split())}
    return None, {}


def classify(message: str) -> NLUClassification:
    raw = message or ""
    raw_normalized = normalize_text(raw)
    normalized = normalize_banglish(raw)
    language_style = detect_language_style(raw, raw_normalized)

    if _contains_any(normalized, patterns.DANGEROUS_HINTS):
        return _result(
            intent="dangerous_block",
            route="blocked",
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.99,
            reason="Dangerous/system command matched.",
            needs_tool=True,
        )

    if patterns.MATH_RE.match(normalized) or patterns.PERCENT_RE.match(normalized):
        return _result(
            intent="calculator",
            route="local_calculator",
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.98,
            reason="Simple arithmetic pattern.",
            entities={"expression": normalized},
            needs_tool=True,
        )

    contact_intent, contact_entities = _extract_contact_command(normalized)
    if contact_intent:
        return _result(
            intent=contact_intent,
            route="local_contacts",
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.95,
            reason="Local WhatsApp contact command.",
            entities=contact_entities,
            needs_tool=True,
            needs_action=contact_intent != "contact_lookup",
        )

    if _contains_any(normalized, patterns.WEATHER_HINTS):
        return _result(intent="weather", route="weather_api", raw_text=raw, normalized_text=normalized, language_style=language_style, reason="Weather phrase.", needs_tool=True)

    if _contains_any(normalized, patterns.TIME_HINTS):
        return _result(intent="current_time", route="time_tool", raw_text=raw, normalized_text=normalized, language_style=language_style, reason="Time phrase.", needs_tool=True)

    if _contains_any(normalized, patterns.TRANSLATION_HINTS):
        return _result(intent="translation", route="translation_or_llm", raw_text=raw, normalized_text=normalized, language_style=language_style, reason="Translation/meaning phrase.", needs_tool=True)

    if "youtube" in normalized:
        wants_search = _contains_any(normalized, patterns.YOUTUBE_SEARCH_HINTS)
        intent = "youtube_search" if wants_search else "youtube_open"
        route = "youtube_search_url" if wants_search else "youtube_open_url"
        return _result(
            intent=intent,
            route=route,
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.96,
            reason="Explicit YouTube command.",
            entities={"query": _extract_youtube_query(normalized)} if wants_search else {"target": "youtube"},
            needs_tool=True,
            needs_action=True,
        )

    if "whatsapp" in normalized:
        recipient, text = _extract_contact_message(normalized)
        return _result(
            intent="whatsapp_draft" if recipient and text else "whatsapp_open",
            route="whatsapp_draft_tool" if recipient and text else "whatsapp_open_url",
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.95,
            reason="Explicit WhatsApp command.",
            entities={k: v for k, v in {"recipient": recipient, "message": text}.items() if v},
            needs_tool=True,
            needs_action=True,
            needs_clarification=not bool(recipient and text) and "open" not in normalized,
        )

    recipient, text = _extract_contact_message(normalized)
    if recipient and text:
        return _result(
            intent="contact_message_intent",
            route="confirm_whatsapp_or_contact_message",
            raw_text=raw,
            normalized_text=normalized,
            language_style=language_style,
            confidence=0.86,
            reason="Clear contact-message wording without explicit app.",
            entities={"recipient": recipient, "message": text},
            needs_action=True,
            needs_clarification=True,
        )

    if _contains_any(normalized, patterns.IDENTITY_HINTS):
        return _result(intent="identity", route="local_persona", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.97, reason="Assistant identity question.")

    if _contains_any(normalized, patterns.PROFILE_HINTS):
        return _result(intent="user_profile", route="local_profile_memory", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.94, reason="User profile/memory question.")

    if _contains_any(normalized, patterns.LOCATION_HINTS):
        return _result(intent="location_permission", route="location_permission_prompt", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.9, reason="Location requires permission.", needs_clarification=True)

    if _contains_any(normalized, patterns.LIVE_SEARCH_HINTS):
        return _result(intent="search_current", route="search_first", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.9, reason="Current/recent/live information.", entities={"query": normalized}, needs_search=True)

    app_target = _extract_app(normalized)
    if app_target and _contains_any(normalized, patterns.APP_OPEN_HINTS):
        return _result(intent="app_open_request", route="safe_app_launcher", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.93, reason="Safe app open request.", entities={"app": app_target}, needs_tool=True, needs_action=True)

    if _contains_any(normalized, patterns.CODE_GENERATION_HINTS):
        page_kind = _extract_page_kind(normalized)
        return _result(intent="llm_code_generation", route="llm_code_generation", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.9, reason="Code/page generation request.", entities={"artifact": page_kind or "code"}, needs_llm=True)

    if _contains_any(normalized, patterns.APP_PLANNING_HINTS) or (
        "want to create" in normalized
        and any(topic in normalized for topic in ("app", "software", "project"))
    ):
        return _result(intent="app_planning", route="app_planning", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.9, reason="App/project planning request.", entities={"artifact": "app"}, needs_llm=True)

    if _contains_any(normalized, patterns.CASUAL_HINTS) or has_phrase_or_token(normalized, patterns.GREETING_HINTS):
        return _result(intent="casual_chat", route="local_persona", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.86, reason="Casual/local persona message.")

    if normalized.startswith("what is ") or normalized.endswith(" ki") or _contains_any(normalized, {"computer", "internet", "ai", "programming"}):
        topic = normalized.replace("what is", "").replace("ki", "").strip() or normalized
        return _result(intent="general_qa", route="llm_or_local_general", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.82, reason="General knowledge question.", entities={"topic": topic}, needs_llm=True)

    if len(normalized.split()) <= 2:
        return _result(intent="clarification", route="ask_clarification", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.55, reason="Too short/incomplete.", needs_clarification=True)

    return _result(intent="general_qa", route="llm_or_local_general", raw_text=raw, normalized_text=normalized, language_style=language_style, confidence=0.72, reason="Default useful answer route.", entities={"topic": normalized}, needs_llm=True)

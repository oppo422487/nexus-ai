"""Safe universal chat orchestration for Nexa AI.

The chat endpoint answers inside the app. It never executes shell commands,
never opens arbitrary paths, never writes files, and only opens whitelisted apps
when Trusted Quick Launch Mode is enabled.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from contextvars import ContextVar
from datetime import datetime
import os
import re
import urllib.parse
from zoneinfo import ZoneInfo

import httpx

from app.actions import execute_open_app, execute_open_website, get_allowed_app, get_allowed_website_url, normalize_app_key
from app.actions.safety import contains_dangerous_keyword
from app.assistant.response_composer import address_label as compose_address_label, compose as compose_response, compose_intent
from app.audit.event_log import record_audit_event
from app.contacts import add_contact_alias, delete_contact, find_contact_matches, get_contact, list_contacts, save_contact
from app.email.composer import compose_formal_email
from app.email.service import send_email
from app.permissions import is_permission_enabled, permission_denied_message
from app.llm import complete as complete_llm
from app.llm.prompt_builder import build_task_context
from app.llm import should_use_llm, whatsapp_draft_needs_llm
from app.llm.schemas import LLMResponse
from app.memory.pending_tasks import (
    PendingTask,
    action_confirmation_task,
    email_confirmation_task,
    app_planning_task,
    clear_pending_task,
    file_summary_task,
    get_pending_task,
    is_cancel_message,
    is_confirm_message,
    llm_generation_task,
    location_permission_task,
    set_pending_task,
    whatsapp_message_task,
    whatsapp_number_task,
)
from app.schemas.action_execution import ActionExecutionRequest, ActionTarget
from app.schemas.chat import (
    ChatActionStatus,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatPendingTask,
    ChatSearchResult,
    ChatWeatherSnapshot,
)
from app.web import answer_question
from app.search import clean_search_query, is_market_query, search_answer, synthesize_related_answer, to_chat_results
from app.tools.calculator import calculate as calculate_local_expression
from app.youtube import parse_youtube_command
from app.nlu.normalizer import detect_language_style
from app.nlu.banglish import normalize_banglish
from app.productivity import productivity_chat_response

WEATHER_ALLOWED_HOSTS = {"api.open-meteo.com"}
SEARCH_ALLOWED_HOSTS = {"en.wikipedia.org", "bn.wikipedia.org"}
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=23.8103&longitude=90.4125&current="
    "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    "&timezone=Asia%2FDhaka"
)
DEFAULT_LOCATION = "Dhaka, Bangladesh"
REQUEST_TIMEOUT_SECONDS = 8.0
_PREFERRED_REPLY_LANGUAGE: ContextVar[str | None] = ContextVar("preferred_reply_language", default=None)


def set_preferred_reply_language(message: str, preference: str):
    normalized = normalize_text(message)
    if re.search(r"(?:reply|answer|respond|speak|write)\s+(?:to me\s+)?in\s+english|ইংরেজিতে\s+(?:উত্তর|বলো|বলুন|লিখ)", normalized):
        style = "english"
    elif re.search(r"(?:reply|answer|respond|speak|write)\s+(?:to me\s+)?in\s+(?:bangla|bengali)|বাংলা[য়তে]\s+(?:উত্তর|বলো|বলুন|লিখ)", normalized):
        style = "bangla"
    else:
        style = {"Bangla": "bangla", "English": "english"}.get(preference)
    return _PREFERRED_REPLY_LANGUAGE.set(style)


def reset_preferred_reply_language(token) -> None:
    _PREFERRED_REPLY_LANGUAGE.reset(token)


def enforce_reply_language(response: ChatMessageResponse, message: str, address_style: str | None) -> ChatMessageResponse:
    style = _PREFERRED_REPLY_LANGUAGE.get()
    if style not in {"bangla", "english"} or not response.answer.strip():
        return response
    answer = response.answer
    bangla_letters = len(re.findall(r"[\u0980-\u09ff]", answer))
    latin_letters = len(re.findall(r"[A-Za-z]", answer))
    wrong_language = (style == "bangla" and bangla_letters < max(8, latin_letters // 3)) or (style == "english" and bangla_letters > 10)
    if not wrong_language or "```" in answer:
        return response
    target = "natural Bengali written in Bengali script" if style == "bangla" else "natural English"
    translation = complete_llm(
        f"Translate the following assistant reply into {target}. Preserve all facts, warnings, addresses, URLs, code, and confirmation requirements exactly. Return only the translated reply.\n\n{answer}",
        address_style=address_style,
        language_style=style,
    )
    if translation and translation.answer.strip():
        response.answer = translation.answer.strip()
    return response

WEATHER_KEYWORDS = {
    "weather",
    "temperature",
    "temp",
    "forecast",
    "rain",
    "humidity",
    "wind",
    "ajker weather",
    "abohawa",
    "আবহাওয়া",
    "আবহাওয়া",
    "বৃষ্টি",
    "তাপমাত্রা",
}

TIME_KEYWORDS = {
    "time",
    "koita baje",
    "koyta baje",
    "কয়টা বাজে",
    "কয়টা বাজে",
    "baje",
}

IDENTITY_KEYWORDS = {
    "tomar nam ki",
    "tumr nam ki",
    "what is your name",
    "who are you",
    "tumi ke",
    "apni ke",
}

PROFILE_MEMORY_KEYWORDS = {
    "amar somporke ki jano",
    "amar somporke ki ki jano",
    "what do you know about me",
    "amar profile bolo",
    "my profile",
}

LOCATION_KEYWORDS = {
    "may location",
    "my location",
    "ami ekhon kothai achi",
    "ami ekhon kothay achi",
    "where am i",
}

TRANSLATION_KEYWORDS = {
    "translate",
    "translation",
    "bangla ki",
    "english ki",
    "bangla meaning",
    "meaning ki",
    "mane ki",
    "মানে কি",
    "বাংলা কি",
    "er bangla ki",
    "er english ki",
    "er bangla",
    "er english",
    "sentence er bangla ki",
}

ACTION_KEYWORDS = {
    "open",
    "launch",
    "start",
    "khulo",
    "kholo",
    "open koro",
    "খুলো",
    "চালাও",
}

YOUTUBE_KEYWORDS = {"youtube", "yutub", "you tube", "yt", "ইউটিউব"}
WHATSAPP_KEYWORDS = {"whatsapp", "whats app", "হোয়াটসঅ্যাপ", "হোয়াটসঅ্যাপ"}
SEARCH_ACTION_KEYWORDS = {"search", "search koro", "khuje", "khuje dao"}
MESSAGE_ACTION_KEYWORDS = {"message", "draft", "bolo", "send"}
CONTACT_SAVE_KEYWORDS = {"number save", "contact hisebe save", "whatsapp contact hisebe save", "save koro"}
CONTACT_QUERY_KEYWORDS = {"number ki", "number bolo", "contact ki"}
CONTACT_DELETE_KEYWORDS = {"contact delete", "whatsapp contact delete", "number delete"}
CONTACT_ALIAS_KEYWORDS = {"alias", "alias add"}
YOUTUBE_MEDIA_KEYWORDS = {"gaan", "song", "video", "chalao", "chalaw", "play", "গান", "চালাও", "খুলে"}

DANGEROUS_EXTRA_KEYWORDS = {
    "erase",
    "rm -rf",
    "del ",
    "rmdir",
    "destroy",
    "uninstall windows",
    "format drive",
    "ফরম্যাট",
    "ডিলিট",
    "মুছে ফেল",
}

LLM_INTENT_KEYWORDS = {
    "write code",
    "code",
    "code kore dao",
    "debug",
    "bug fix",
    "math explanation",
    "math solve",
    "solve koro",
    "explain",
    "rewrite",
    "formal",
    "friendly message",
    "compose",
    "home page",
    "home page banao",
    "homepage banao",
    "website banao",
    "landing page banao",
    "page banao",
    "page banaw",
    "banao",
    "banaw",
    "html css",
    "html css diye page banao",
    "react component",
    "portfolio website",
    "portfolio website banao",
    "login page",
    "log in page",
    "login page banabo",
    "log in page banabo",
    "ekta log in page banabo",
    "homepage",
    "homepage banaw",
    "landing page",
    "long writing",
    "report",
    "report likho",
    "likho",
    "essay",
    "paragraph",
}

APP_PLANNING_KEYWORDS = {
    "ami ekta app banate cai",
    "ami ekta app banate chai",
    "ami ekta project korte chai",
    "app idea dao",
    "software banate chai",
    "app banate chai",
    "project korte chai",
    "app want to create",
    "software want to create",
    "project want to create",
}

GENERAL_KNOWLEDGE_TOPICS: dict[str, str] = {
    "computer": (
        "A computer is an electronic machine that takes input, processes data using instructions, "
        "stores information, and gives output. Common parts include CPU, memory, storage, input devices, and display."
    ),
    "internet": (
        "The internet is a worldwide network of connected computers and servers. It lets people share information, "
        "visit websites, send messages, stream media, and use online services."
    ),
    "ai": (
        "AI, or artificial intelligence, means software that can do tasks that normally need human thinking, "
        "such as understanding language, recognizing patterns, answering questions, and helping with decisions."
    ),
    "programming": (
        "Programming is writing instructions for computers. Developers use programming languages to build apps, "
        "websites, games, automation, and data systems."
    ),
}

CALCULATOR_RE = re.compile(r"^\s*\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+\s*(?:=\s*)?\??\s*$")
PERCENT_RE = re.compile(r"^\s*(?:calculate\s+)?(?P<percent>\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(?P<base>\d+(?:\.\d+)?)\s*\??\s*$")


@dataclass
class SmartTaskRoute:
    intent: str
    confidence: str
    route: str
    reason: str
    needs_action: bool = False
    needs_llm: bool = False
    needs_search: bool = False
    needs_confirmation: bool = False


@dataclass
class WhatsAppDraftIntent:
    recipient: str | None = None
    raw_message: str | None = None
    tone: str = "normal"
    exact: bool = False


def _route_debug_enabled() -> bool:
    return (os.getenv("NEXA_DEBUG_TASK_ROUTER") or "").strip().lower() in {"1", "true", "yes", "on"}


def _with_route_debug(response: ChatMessageResponse, route: SmartTaskRoute) -> ChatMessageResponse:
    if _route_debug_enabled():
        response.route_debug = asdict(route)
    return response


def _pending_task_dto(task: PendingTask | None) -> ChatPendingTask | None:
    if task is None:
        return None
    return ChatPendingTask(
        kind=task.kind,
        status_label=task.status_label,
        prompt=task.prompt,
        recipient=task.recipient,
        message=task.message,
        expires_at=task.expires_at,
    )


def _response_with_pending(response: ChatMessageResponse, task: PendingTask | None) -> ChatMessageResponse:
    response.pending_task = _pending_task_dto(task)
    return response

GREETING_HINTS = {
    "hello",
    "hi",
    "hey",
    "assalamu alaikum",
    "salam",
    "salaam",
    "good morning",
    "good evening",
}

THANKS_HINTS = {"thanks", "thank you", "dhonnobad", "shukriya"}

CAPABILITY_HINTS = {
    "what can you do",
    "what do you do",
    "help me",
    "how can you help",
    "tumi ki korte paro",
    "ki korte paro",
    "nexa ki korte pare",
}

FRUSTRATION_HINTS = {
    "not working",
    "kaj kore na",
    "problem",
    "bug",
    "error",
    "ami frustrated",
    "bhalo lagche na",
    "ami tension e achi",
    "ami valo nai",
    "ami bhalo nai",
    "amar mon kharap",
}

CASUAL_PROJECT_HINTS = {
    "ami ekta project niye kaj kortesi",
    "ami project niye kaj korchi",
    "i am working on a project",
    "i am working on my project",
    "amar project niye help lagbe",
    "project niye help lagbe",
}

CASUAL_CONVERSATION_HINTS = {
    "how are you",
    "how are u",
    "how r u",
    "how was your day",
    "ki koro",
    "kemon aso",
    "ki obostha",
    "ami valo nai",
    "ami bhalo nai",
    "ami tension e achi",
    "amar mon kharap",
    "amar sathe kotha bolo",
    "tumi amar sathe kotha bolo",
    "tumi amar sathe normal kotha bolo",
    "normal kotha bolo",
}

LOCAL_CHAT_HINTS = (
    GREETING_HINTS
    | THANKS_HINTS
    | CAPABILITY_HINTS
    | FRUSTRATION_HINTS
    | CASUAL_PROJECT_HINTS
    | CASUAL_CONVERSATION_HINTS
    | {"who are you"}
)

WEATHER_CODE_SUMMARY = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def normalize_text(value: str) -> str:
    normalized = " ".join((value or "").strip().lower().split())
    normalized = re.sub(r"(?<![a-z0-9])kta(?=\s+(?:login|home|landing|page|website))", "ekta", normalized)
    return normalized


def _has_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _has_phrase_or_token(text: str, keywords: set[str]) -> bool:
    for keyword in keywords:
        if " " in keyword:
            if keyword in text:
                return True
        elif re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
            return True
    return False


def _compose_reply(text: str, address_style: str | None, language_style: str | None = None) -> str:
    return compose_response(text, address_style, language_style or "mixed")


def _looks_like_question(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "?",
            "ki",
            "what",
            "who",
            "why",
            "how",
            "latest",
            "news",
            "price",
            "current",
            "today",
            "ajker",
            "কি",
            "কী",
            "মানে",
            "খবর",
        )
    )


def _looks_like_math_request(text: str) -> bool:
    return bool(CALCULATOR_RE.match(text) or PERCENT_RE.match(text))


def _looks_like_search_request(text: str) -> bool:
    search_markers = (
        "google theke search",
        "google e khuje",
        "search kore bolo",
        "search koro",
        "internet theke bolo",
        "web theke bolo",
        "search",
        "khuje bolo",
        "khujte paro",
        "latest",
        "today news",
    )
    return any(marker in text for marker in search_markers)


def _looks_like_local_conversation(text: str) -> bool:
    return (
        _has_phrase_or_token(text, GREETING_HINTS)
        or any(hint in text for hint in THANKS_HINTS)
        or any(hint in text for hint in CAPABILITY_HINTS)
        or any(hint in text for hint in FRUSTRATION_HINTS)
        or any(hint in text for hint in CASUAL_PROJECT_HINTS)
        or any(hint in text for hint in CASUAL_CONVERSATION_HINTS)
        or text in {"achi", "hmm", "ok", "okay"}
    )


def _looks_like_llm_request(text: str) -> bool:
    if any(marker in text for marker in ("latest", "today", "current", "news", "price", "weather")):
        return False
    if _looks_like_local_conversation(text):
        return False
    return (
        _has_any(text, LLM_INTENT_KEYWORDS)
        or re.search(r"\b(?:home\s*page|homepage|website|landing page|portfolio|react component)\s+(?:banao|banaw|banai|make|create)\b", text) is not None
        or text.startswith("explain ")
        or text.startswith("why ")
        or text.startswith("how to ")
        or text.startswith("write ")
        or text.startswith("rewrite ")
        or text.startswith("compose ")
    )


def _looks_like_whatsapp_contact_message(text: str) -> bool:
    return bool(re.search(r"\b\S+\s+(?:ke|k)\s+(?:message|sms|bolo|draft|send|likho)\b", text))


def _looks_like_live_search(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "latest",
            "today",
            "current",
            "news",
            "recent global news",
            "latest global news",
            "current news",
            "today news",
            "gold price",
            "gold prize",
            "dollar rate",
            "current price",
            "python latest version",
            "ajker news",
            "latest update",
            "latest version",
        )
    )


def _looks_like_complex_translation(text: str) -> bool:
    return _has_any(text, TRANSLATION_KEYWORDS) and len(text) > 180


def _looks_like_contact_command(text: str) -> bool:
    if "number" not in text and "contact" not in text and "alias" not in text:
        return False
    return (
        any(marker in text for marker in CONTACT_SAVE_KEYWORDS)
        or any(marker in text for marker in CONTACT_QUERY_KEYWORDS)
        or any(marker in text for marker in CONTACT_DELETE_KEYWORDS)
        or any(marker in text for marker in CONTACT_ALIAS_KEYWORDS)
    )


def _looks_like_identity_question(text: str) -> bool:
    return any(marker in text for marker in IDENTITY_KEYWORDS)


def _looks_like_profile_memory_question(text: str) -> bool:
    return any(marker in text for marker in PROFILE_MEMORY_KEYWORDS)


def _looks_like_location_question(text: str) -> bool:
    return any(marker in text for marker in LOCATION_KEYWORDS)


def _looks_like_file_summary_request(text: str) -> bool:
    file_markers = ("pdf", "file", "document", "download folder", "downloads folder", "folder")
    summary_markers = ("summary", "summarize", "summary kore", "saransho", "সারাংশ")
    return any(marker in text for marker in file_markers) and any(marker in text for marker in summary_markers)


def _looks_like_app_planning_request(text: str) -> bool:
    return any(marker in text for marker in APP_PLANNING_KEYWORDS)


def _looks_like_pending_whatsapp_number(text: str, history: list | None) -> bool:
    if not re.search(r"(?:\+?88)?01\d{9}", text):
        return False
    if "number" in text:
        return True
    if not history:
        return False
    for item in reversed(history[-4:]):
        content = normalize_text(getattr(item, "content", "") or "")
        if "phone number" in content and "whatsapp" in content:
            return True
    return False


def _general_knowledge_topic(text: str) -> str | None:
    for topic in GENERAL_KNOWLEDGE_TOPICS:
        if re.search(rf"(?<![a-z0-9]){re.escape(topic)}(?![a-z0-9])", text):
            return topic
    return None


def _looks_truly_incomplete(text: str) -> bool:
    return text in {
        "how would that work",
        "how does that work",
        "what about that",
        "can you do that",
        "make it better",
        "eta koro",
        "oita koro",
    }


def _looks_like_generation_detail(text: str) -> bool:
    detail_markers = (
        "html css diye",
        "html css",
        "react diye",
        "react",
        "tailwind diye",
        "tailwind",
        "dark design",
        "dark",
        "login form add koro",
        "responsive koro",
        "responsive",
        "database add koro",
        "database",
        "frontend only",
        "backend shoho",
        "with backend",
        "with database",
        "mobile responsive",
        "blue theme",
        "dark theme",
        "light theme",
        "animation add koro",
        "form add koro",
        "food delivery",
        "food delivari",
        "login page",
        "home page",
        "homepage",
        "website",
        "landing page",
        "code deo",
        "code dao",
        "code kore dao",
        "tumi amake code deo",
        "web",
        "android",
        "desktop",
    )
    vague_markers = (
        "how would that work",
        "eta kivabe kaj kore",
        "what do you mean",
        "explain",
        "kivabe",
    )
    if any(marker in text for marker in vague_markers):
        return False
    return any(marker in text for marker in detail_markers)


def classify_task(message: str) -> SmartTaskRoute:
    normalized = normalize_banglish(normalize_text(message))
    if "email" in normalized or "ইমেইল" in normalized or "ই-মেইল" in normalized:
        return SmartTaskRoute(
            intent="email_skill",
            confidence="high",
            route="email_draft_confirmation",
            reason="Explicit email drafting or sending request.",
            needs_action=True,
            needs_confirmation=True,
        )
    if _looks_like_contact_command(normalized):
        return SmartTaskRoute(
            intent="contact_command",
            confidence="high",
            route="local_contacts",
            reason="Local contact save/lookup/delete command.",
            needs_action=True,
        )
    if contains_dangerous_keyword(normalized) or _has_any(normalized, DANGEROUS_EXTRA_KEYWORDS):
        return SmartTaskRoute(
            intent="blocked_dangerous",
            confidence="high",
            route="blocked",
            reason="Dangerous system/file command matched before any tool or LLM.",
        )
    if _looks_like_math_request(normalized):
        return SmartTaskRoute(
            intent="local_calculator",
            confidence="high",
            route="local_solver",
            reason="Simple arithmetic can be solved locally.",
        )
    if _looks_like_file_summary_request(normalized):
        return SmartTaskRoute(
            intent="file_summary_request",
            confidence="high",
            route="file_selection_required",
            reason="File/PDF summary requires explicit user file selection.",
        )
    if _looks_like_location_question(normalized):
        return SmartTaskRoute("location_permission", "high", "local_persona", "Exact location requires browser/device permission.")
    if _has_any(normalized, WEATHER_KEYWORDS):
        return SmartTaskRoute(
            intent="weather",
            confidence="high",
            route="weather_api",
            reason="Weather intent uses Open-Meteo/local API path.",
        )
    if _has_any(normalized, TIME_KEYWORDS):
        return SmartTaskRoute(
            intent="current_time",
            confidence="high",
            route="local_timezone",
            reason="Time intent uses local timezone database.",
        )
    if _looks_like_complex_translation(normalized):
        return SmartTaskRoute(
            intent="llm_assist",
            confidence="medium",
            route="llm",
            reason="Long or ambiguous translation benefits from LLM.",
            needs_llm=True,
        )
    if _has_any(normalized, TRANSLATION_KEYWORDS):
        return SmartTaskRoute(
            intent="translation",
            confidence="high",
            route="local_translation",
            reason="Short translation/explanation uses local helper first.",
        )
    if _has_phrase_or_token(normalized, YOUTUBE_KEYWORDS):
        return SmartTaskRoute(
            intent="youtube_skill",
            confidence="high",
            route="youtube_action",
            reason="Explicit YouTube keyword.",
            needs_action=True,
            needs_confirmation=not is_permission_enabled("trusted_youtube_auto_open"),
        )
    if _has_phrase_or_token(normalized, WHATSAPP_KEYWORDS) or _looks_like_whatsapp_contact_message(normalized):
        return SmartTaskRoute(
            intent="whatsapp_skill",
            confidence="high",
            route="whatsapp_draft_action",
            reason="Explicit WhatsApp or clear contact-message command.",
            needs_action=True,
            needs_llm=whatsapp_draft_needs_llm(message),
            needs_confirmation=not is_permission_enabled("trusted_whatsapp_draft_auto_open"),
        )
    if _looks_like_search_request(normalized) or _looks_like_live_search(normalized):
        return SmartTaskRoute(
            intent="web_search",
            confidence="high",
            route="search_first",
            reason="Explicit/current/live information request uses search first.",
            needs_search=True,
            needs_llm=True,
        )
    if _looks_like_identity_question(normalized):
        return SmartTaskRoute("assistant_identity", "high", "local_persona", "Assistant identity is answered locally.")
    if _looks_like_profile_memory_question(normalized):
        return SmartTaskRoute("profile_memory", "high", "local_persona", "User memory/profile is answered locally without inventing facts.")
    if _has_phrase_or_token(normalized, GREETING_HINTS):
        return SmartTaskRoute("greeting", "high", "local_persona", "Greeting uses local persona.")
    if any(hint in normalized for hint in THANKS_HINTS):
        return SmartTaskRoute("thanks", "high", "local_persona", "Thanks uses local persona.")
    if any(hint in normalized for hint in CAPABILITY_HINTS):
        return SmartTaskRoute("capabilities", "high", "local_persona", "Capability question uses local persona.")
    if any(hint in normalized for hint in FRUSTRATION_HINTS):
        return SmartTaskRoute("user_frustration", "high", "local_persona", "Supportive personal message uses local persona.")
    if any(hint in normalized for hint in CASUAL_PROJECT_HINTS):
        return SmartTaskRoute("casual_chat", "high", "local_persona", "Project/casual support uses local persona.")
    if any(hint in normalized for hint in CASUAL_CONVERSATION_HINTS):
        return SmartTaskRoute("casual_chat", "high", "local_persona", "Casual conversation uses local persona.")
    if _looks_like_app_planning_request(normalized):
        return SmartTaskRoute(
            intent="app_planning",
            confidence="high",
            route="local_or_llm_planning",
            reason="App/project planning request should get assistant planning support.",
            needs_llm=True,
        )
    if _looks_like_llm_request(normalized):
        return SmartTaskRoute(
            intent="llm_assist",
            confidence="high",
            route="llm",
            reason="Coding/writing/math/complex explanation request.",
            needs_llm=True,
        )
    if _has_any(normalized, ACTION_KEYWORDS):
        return SmartTaskRoute(
            intent="app_open_request",
            confidence="medium",
            route="safe_action",
            reason="Explicit open/launch intent.",
            needs_action=True,
            needs_confirmation=not is_permission_enabled("trusted_quick_launch"),
        )
    if _looks_truly_incomplete(normalized):
        return SmartTaskRoute(
            intent="clarify_or_llm",
            confidence="low",
            route="clarify",
            reason="Incomplete follow-up needs one precise clarification.",
            needs_llm=False,
        )
    if _general_knowledge_topic(normalized):
        return SmartTaskRoute(
            intent="general_knowledge",
            confidence="medium",
            route="local_or_llm_answer",
            reason="Common general knowledge question can be answered usefully.",
            needs_llm=True,
        )
    if normalized in LOCAL_CHAT_HINTS:
        return SmartTaskRoute("normal_chat", "medium", "local_persona", "Known local chat phrase.")
    if _looks_like_question(normalized) and not _looks_like_local_conversation(normalized):
        return SmartTaskRoute(
            intent="general_knowledge",
            confidence="low",
            route="local_or_llm_answer",
            reason="General question should use LLM/local fallback before clarification.",
            needs_llm=True,
        )
    return SmartTaskRoute("casual_chat", "medium", "local_persona", "Default to local assistant instead of random web search.")


def _should_defer_pending_task(route: SmartTaskRoute, task: PendingTask | None = None, message: str = "") -> bool:
    if route.intent == "llm_assist":
        normalized = normalize_text(message)
        if task and task.kind == "llm_generation_details" and not any(marker in normalized for marker in ("banao", "banabo", "banaw", "page", "homepage", "website", "code kore dao", "write code")):
            return False
        return True
    return route.intent in {
        "blocked_dangerous",
        "local_calculator",
        "location_permission",
        "weather",
        "current_time",
        "translation",
        "file_summary_request",
        "youtube_skill",
        "whatsapp_skill",
        "email_skill",
        "web_search",
        "contact_command",
        "app_open_request",
        "app_planning",
    }


def detect_chat_intent(message: str) -> str:
    return classify_task(message).intent


def _language_style(message: str) -> str:
    preferred = _PREFERRED_REPLY_LANGUAGE.get()
    if preferred:
        return preferred
    style = detect_language_style(message, normalize_text(message))
    # Existing response templates call romanized Bangla "mixed". Keep that
    # compatibility while distinguishing native Bangla script for Bangla TTS.
    return "mixed" if style == "banglish" else style


def _address_label(style: str | None, language_style: str) -> str:
    return compose_address_label(style, language_style)


def _with_address(text: str, address: str) -> str:
    if not address:
        return text
    return f"{address}, {text}"


def conversational_answer(message: str, intent: str, address_style: str | None = None) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    normalized = normalize_text(message)
    canonical = normalize_banglish(message)

    if intent == "greeting":
        if "assalamu" in canonical or "salam" in canonical:
            answer = _with_address("Wa alaikum assalam. কী সাহায্য লাগবে বলুন।", address)
        elif style == "bangla":
            answer = _with_address("হ্যালো। বলুন, কীভাবে সাহায্য করতে পারি?", address)
        elif style == "mixed":
            answer = _with_address("Hi. আমি কীভাবে সাহায্য করতে পারি?", address)
        else:
            answer = _with_address("Hello, how can I help you today?", address)
    elif intent == "thanks":
        answer = _with_address("You are welcome. আর কিছু লাগলে বলুন।", address) if style == "mixed" else _with_address("You are welcome. Tell me what you need next.", address)
    elif intent == "capabilities":
        answer = (
            _with_address(
                "আমি voice ও text command বুঝতে পারি; web search, আবহাওয়া, সময়, translation, project help, নিরাপদ app/website, YouTube, WhatsApp draft, reminder এবং read-only file/document কাজে সাহায্য করতে পারি।",
                address,
            )
            if style == "bangla"
            else
            _with_address(
                "আমি Dashboard chat-এর মধ্যেই web/search answer, weather, current time, translation/explanation, "
                "safe app opening preview, voice input, reminders, and read-only file/document help করতে পারি.",
                address,
            )
            if style == "mixed"
            else _with_address(
                "I can answer web/search questions, check weather and time, translate or explain text, preview safe app launches, use voice input, and help with reminders plus read-only files/documents.",
                address,
            )
        )
    elif intent == "user_frustration":
        answer = (
            _with_address("বুঝলাম. কী error দেখাচ্ছে বা কোন জায়গায় আটকে আছে বলুন, আমি ধাপে ধাপে help করি।", address)
            if style == "mixed"
            else _with_address("I hear you. Tell me what failed or what error you see, and I will help step by step.", address)
        )
    elif intent == "casual_chat":
        if any(hint in normalized for hint in CASUAL_PROJECT_HINTS):
            answer = (
                _with_address("ভালো. Project-er কোন অংশে help লাগবে: bug fix, design, backend, frontend, docs, নাকি testing?", address)
                if style == "mixed"
                else _with_address("Nice. Which part should we work on: bugs, design, backend, frontend, docs, or testing?", address)
            )
        else:
            answer = (
                _with_address("বলুন, কী নিয়ে help দরকার? আমি এখানে আছি.", address)
                if style == "mixed"
                else _with_address("Tell me what you want to do, and I will help.", address)
            )
    else:
        answer = _with_address("I am Nexa, your local desktop assistant. Ask me anything or give me a safe task to preview.", address)

    _record_chat_event(intent, "completed", message, "Local assistant conversation.")
    return ChatMessageResponse(
        status="completed",
        intent=intent,
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Local conversation",
        chips=["Local response", "Personal assistant", "No execution"],
    )


def _configured_chat_provider() -> str:
    provider = (os.getenv("NEXA_CHAT_PROVIDER") or "local").strip().lower()
    return provider if provider in {"local", "openai_compatible", "ollama"} else "local"


def _conversation_topic(message: str, history: list | None = None) -> str:
    normalized = normalize_text(message)
    if "project" in normalized:
        return "project"
    if any(marker in normalized for marker in ("tension", "mon kharap", "valo nai", "bhalo nai")):
        return "support"
    if history:
        for item in reversed(history[-4:]):
            content = normalize_text(getattr(item, "content", "") or "")
            if "project" in content:
                return "project"
            if "tension" in content or "mon kharap" in content:
                return "support"
    return "general"


def _external_chat_provider_answer(
    message: str,
    intent: str,
    address: str,
    style: str,
    history: list | None,
) -> str | None:
    provider = _configured_chat_provider()
    if provider == "local":
        return None
    # Provider interface placeholder for later phases. P3-D keeps local-first
    # behavior and does not upload conversation data without explicit setup.
    return None


def _llm_answer_response(
    message: str,
    *,
    address_style: str | None,
    language_style: str,
    context: str | None = None,
    intent: str = "llm_assist",
    pending_task: PendingTask | None = None,
) -> ChatMessageResponse | None:
    if context is None and intent in {"llm_assist", "llm_generation_continue"}:
        context = build_task_context(
            user_message=message,
            intent=intent,
            language_style=language_style,
            pending_task=pending_task,
        )
    result = complete_llm(message, address_style=address_style, language_style=language_style, context=context)
    if not result:
        return None
    _record_chat_event(intent, "completed", message, f"LLM provider: {result.provider}")
    return ChatMessageResponse(
        status="completed",
        intent=intent,
        message=message,
        answer=result.answer,
        provider=result.provider,
        source="Hosted LLM",
        chips=[result.provider],
        llm_used=True,
        llm_provider=result.provider,
        fallback_used=result.fallback_used,
        source_type="llm",
    )


def _llm_setup_answer(message: str, address_style: str | None, language_style: str, intent: str = "llm_assist") -> ChatMessageResponse:
    answer = compose_intent(
        "llm_setup_missing",
        address_style=address_style,
        language_style=language_style,
        user_message=message,
    )
    _record_chat_event(intent, "needs_configuration", message, "LLM provider not configured.")
    task = None
    if _looks_like_llm_request(normalize_text(message)) and not intent.endswith("_continue"):
        pending = llm_generation_task(message)
        context_bits = _extract_app_generation_context(message)
        if context_bits:
            pending.data.update(context_bits)
        if context_bits.get("artifact") in {"login page", "home page", "landing page"} and not pending.data.get("platform"):
            pending.data["platform"] = "web"
            pending.data["stack"] = "HTML/CSS/JS"
        task = set_pending_task(pending)
    return _response_with_pending(ChatMessageResponse(
        status="needs_configuration",
        intent=intent,
        message=message,
        answer=answer,
        chips=[],
        llm_used=False,
        source_type="llm",
        error=answer,
    ), task)


def _assistant_identity_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    answer = (
        "Ami Nexa AI, apnar local personal assistant. Voice/text chat, wake word, memory, notes/tasks, reminders, calendar, email/WhatsApp draft, files, live information, safe apps/media, YouTube, translation and diagnostics-e help korte pari."
        if style == "mixed"
        else "I am Nexa AI, your local personal assistant. I support voice/text chat, wake word, memory, notes and tasks, reminders, calendar, drafts, files, live information, safe apps and media, YouTube, translation, and diagnostics."
    )
    answer = _with_address(answer, address)
    _record_chat_event("assistant_identity", "completed", message, "Local assistant identity.")
    return ChatMessageResponse(
        status="completed",
        intent="assistant_identity",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Local conversation",
        chips=[],
        source_type="local",
    )


def _profile_memory_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    answer = (
        "Ekhono apnar personal profile/memory beshi save kora nei. Apni chaile ami apnar preference local memory te save korte pari."
        if style == "mixed"
        else "I do not have much saved personal profile or memory about you yet. If you want, I can store preferences locally for future help."
    )
    answer = _with_address(answer, address)
    _record_chat_event("profile_memory", "completed", message, "No invented personal facts.")
    return ChatMessageResponse(
        status="completed",
        intent="profile_memory",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Local profile memory",
        chips=[],
        source_type="local",
    )


def _location_permission_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    answer = (
        "Ami browser/device location permission chara apnar exact location dekhte pari na. Location permission dile ami help korte parbo."
        if style == "mixed"
        else "I cannot see your exact location without browser or device location permission. If you enable location permission, I can help."
    )
    answer = _with_address(answer, address)
    task = set_pending_task(location_permission_task(message))
    _record_chat_event("location_permission", "needs_permission", message, "Location permission required.")
    return _response_with_pending(ChatMessageResponse(
        status="needs_permission",
        intent="location_permission",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Device permission required",
        chips=[],
        source_type="local",
    ), task)


def _app_planning_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    answer = (
        "Nice. App ta kon platform-er--Android, web, desktop, na AI? Main feature gula bolen, ami plan, tech stack, UI flow, and database structure diye dibo."
        if style == "mixed"
        else "Nice. Which platform is the app for: Android, web, desktop, or AI? Tell me the main features and I can outline the plan, tech stack, UI flow, and database structure."
    )
    answer = _with_address(answer, address)
    task = set_pending_task(app_planning_task(message))
    _record_chat_event("app_planning", "needs_more_info", message, "Asked for platform/features.")
    return _response_with_pending(ChatMessageResponse(
        status="needs_more_info",
        intent="app_planning",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Local planning prompt",
        chips=[],
        source_type="local",
    ), task)


def _file_summary_request_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    answer = (
        "ami apnar Downloads folder direct access korte pari na. PDF ta upload/select korle ami summary kore dite parbo."
        if style == "mixed"
        else "I cannot directly access your Downloads folder. Please upload/select the PDF and I can summarize it."
    )
    answer = _compose_reply(answer, address_style, style)
    task = set_pending_task(file_summary_task(message))
    _record_chat_event("file_summary_request", "needs_file", message, "PDF upload or user-selected file required.")
    return _response_with_pending(ChatMessageResponse(
        status="needs_file",
        intent="file_summary_request",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="File selection required",
        chips=[],
        source_type="local",
        error=answer,
    ), task)


def _general_knowledge_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    llm_response = _llm_answer_response(
        message,
        address_style=address_style,
        language_style=style,
        intent="general_knowledge",
    )
    if llm_response:
        llm_response.intent = "general_knowledge"
        return llm_response
    topic = _general_knowledge_topic(normalize_text(message))
    if topic:
        short_answer = GENERAL_KNOWLEDGE_TOPICS[topic]
        if style == "mixed":
            answer = f"Short answer: {short_answer} Detailed answer-er jonno LLM provider key add korle aro bhalo explain korte parbo."
        else:
            answer = f"Short answer: {short_answer} Add an LLM provider key for a deeper explanation."
        _record_chat_event("general_knowledge", "completed", message, f"Local fallback topic: {topic}")
        return ChatMessageResponse(
            status="completed",
            intent="general_knowledge",
            message=message,
            answer=_with_address(answer, _address_label(address_style, style)),
            provider="Nexa local assistant",
            source="Local general answer fallback",
            chips=[],
            source_type="local",
        )
    return _llm_setup_answer(message, address_style, style, intent="general_knowledge")


def _specific_clarification_response(message: str, address_style: str | None) -> ChatMessageResponse:
    style = _language_style(message)
    answer = compose_intent(
        "clarification",
        address_style=address_style,
        language_style=style,
        user_message=message,
    )
    _record_chat_event("clarify", "needs_more_info", message, "Specific clarification requested.")
    return ChatMessageResponse(
        status="needs_more_info",
        intent="clarify",
        message=message,
        answer=answer,
        provider="Nexa local assistant",
        source="Local clarification",
        chips=[],
        source_type="local",
    )


def _pick_local_reply(options: list[str], message: str, history: list | None) -> str:
    if not options:
        return ""
    assistant_count = 0
    if history:
        assistant_count = sum(1 for item in history if getattr(item, "role", "") == "assistant")
    seed = sum(ord(char) for char in normalize_text(message)) + assistant_count
    return options[seed % len(options)]


def _local_conversation_debug_enabled() -> bool:
    return (os.getenv("NEXA_DEBUG_CHAT_CHIPS") or "").strip().lower() in {"1", "true", "yes", "on"}


def conversational_answer(
    message: str,
    intent: str,
    address_style: str | None = None,
    history: list | None = None,
) -> ChatMessageResponse:
    style = _language_style(message)
    address = _address_label(address_style, style)
    normalized = normalize_text(message)
    canonical = normalize_banglish(message)
    topic = _conversation_topic(message, history)
    provider_name = _configured_chat_provider()
    provider_answer = _external_chat_provider_answer(message, intent, address, style, history)

    if provider_answer:
        answer = provider_answer
    elif intent == "greeting":
        if "assalamu" in canonical or "salam" in canonical:
            answer = _with_address(
                _pick_local_reply(
                    ["ওয়ালাইকুম আসসালাম। বলুন, কীভাবে সাহায্য করতে পারি?"]
                    if style == "bangla"
                    else [
                        "Wa alaikum assalam. Ki sahajjo lagbe bolun.",
                        "Wa alaikum assalam. Bolun, aaj ki niye help korbo?",
                    ],
                    message,
                    history,
                ),
                address,
            )
        elif style == "bangla":
            answer = _with_address(
                _pick_local_reply(
                    ["হ্যালো। বলুন, কীভাবে সাহায্য করতে পারি?", "হ্যালো। আমি প্রস্তুত আছি, কী করতে হবে বলুন।"],
                    message,
                    history,
                ),
                address,
            )
        elif style == "mixed":
            answer = _with_address(
                _pick_local_reply(
                    [
                        "Hi. Ami kivabe help korte pari?",
                        "Hi. Bolun, ki niye help korbo?",
                        "Hello. Ami ready, ki help lagbe?",
                    ],
                    message,
                    history,
                ),
                address,
            )
        else:
            answer = _with_address(
                _pick_local_reply(
                    [
                        "Hello, how can I help you today?",
                        "Hello, what should we work on today? I can help.",
                        "Hello, tell me what you need and I will help.",
                    ],
                    message,
                    history,
                ),
                address,
            )
    elif intent == "thanks":
        answer = (
            _with_address("আপনাকে স্বাগতম। আর কিছু দরকার হলে বলুন।", address)
            if style == "bangla"
            else _with_address("You are welcome. Ar kichu lagle bolun.", address)
            if style == "mixed"
            else _with_address("You are welcome. Tell me what you need next.", address)
        )
    elif intent == "capabilities":
        answer = (
            _with_address(
                "আমি voice ও text command বুঝতে পারি; web search, আবহাওয়া, সময়, translation, project help, নিরাপদ app/website, YouTube, WhatsApp draft, reminder এবং read-only file/document কাজে সাহায্য করতে পারি।",
                address,
            )
            if style == "bangla"
            else
            _with_address(
                "Ami Dashboard chat-er moddhei web/search answer, weather, time, translation, project help, YouTube, WhatsApp draft, voice input, reminders, and read-only file/document help korte pari.",
                address,
            )
            if style == "mixed"
            else _with_address(
                "I can answer web/search questions, check weather and time, translate or explain text, help with projects, open safe YouTube/WhatsApp draft flows, use voice input, and help with reminders plus read-only files/documents.",
                address,
            )
        )
    elif intent == "user_frustration":
        answer = (
            _with_address(
                _pick_local_reply(
                    [
                        "বুঝতে পারছি। সমস্যাটা ধীরে ধীরে বলুন, আমি একসঙ্গে সমাধান করার চেষ্টা করব।",
                        "আমি শুনছি। কোন জায়গায় সমস্যা হচ্ছে বলুন, ধাপে ধাপে দেখি।",
                    ],
                    message,
                    history,
                ),
                address,
            )
            if style == "bangla"
            else
            _with_address(
                _pick_local_reply(
                    [
                        "বুঝতে পারছি। সমস্যাটা ধীরে ধীরে বলুন, আমি একসঙ্গে সমাধান করার চেষ্টা করব।",
                        "আমি শুনছি। কোন জায়গায় সমস্যা হচ্ছে বলুন, ধাপে ধাপে দেখি।",
                    ],
                    message,
                    history,
                ),
                address,
            )
            if style == "bangla"
            else
            _with_address(
                _pick_local_reply(
                    [
                        "Bujhlam. Ektu dhire dhire bolun ki niye tension--project, study, money, na onno kichu? Ami help korar try korchi.",
                        "Bujhte parchi. Tension-er jaygata ekta kore bolun, ami calm vabe help korbo.",
                        "Thik ache, age ektu breathe nin. Ki niye tension hocche bolun, ami step by step dekhi.",
                    ],
                    message,
                    history,
                ),
                address,
            )
            if style == "mixed"
            else _with_address(
                _pick_local_reply(
                    [
                        "I understand. Tell me what tension is weighing on you--project, study, money, or something else. I will help calmly.",
                        "I hear you. What is causing the tension right now? We can break it down together.",
                        "That tension sounds heavy. Tell me the main thing on your mind, and we will take it step by step.",
                    ],
                    message,
                    history,
                ),
                address,
            )
        )
    elif intent == "casual_chat":
        if style == "bangla":
            if "কেমন আছ" in normalized:
                answer = _with_address(
                    _pick_local_reply(
                        [
                            "আমি ভালো আছি। আপনি কেমন আছেন? আজ কী নিয়ে সাহায্য করব?",
                            "ভালো আছি। আপনার কী অবস্থা? কী করতে হবে বলুন।",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
            elif topic == "project":
                answer = _with_address("Project-এর কোন অংশে সাহায্য দরকার—idea, code, design, bug fix, নাকি testing?", address)
            elif topic == "support":
                answer = _with_address("বুঝতে পারছি। কী নিয়ে চিন্তা হচ্ছে ধীরে ধীরে বলুন, আমি একসঙ্গে সমাধান করার চেষ্টা করব।", address)
            else:
                answer = _with_address("বলুন, কী নিয়ে সাহায্য দরকার? আমি শুনছি।", address)
        elif any(marker in normalized for marker in ("how are you", "how are u", "how r u", "how was your day")):
            answer = (
                _with_address(
                    _pick_local_reply(
                        [
                            "Ami bhalo achi. Apni kemon achen? Aaj ki niye kaj korbo?",
                            "Ami valo achi. Apnar obostha kemon? Ki help lagbe?",
                            "Bhalo achi. Apni bolun, aaj kon kajta age dhorbo?",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
                if style == "mixed"
                else _with_address(
                    _pick_local_reply(
                        [
                            "I am doing well. How are you doing? What should we work on today?",
                            "I am good. How are you feeling today?",
                            "Doing well. Tell me what you want to tackle next.",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
            )
        elif "ki koro" in normalized:
            answer = (
                _with_address(
                    _pick_local_reply(
                        [
                            "Apnar command-er opekkhay achi. Search, project help, YouTube, WhatsApp draft--jeta dorkar bolun.",
                            "Ekhanei achi, apnar next command-er jonno ready. Ki korte hobe?",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
                if style == "mixed"
                else _with_address(
                    _pick_local_reply(
                        [
                            "I am waiting for your next command. Search, project help, YouTube, WhatsApp draft--tell me what you need.",
                            "I am here and ready for your next command. What should we do next?",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
            )
        elif topic == "support":
            answer = (
                _with_address("Bujhlam. Ektu dhire bolun ki niye tension--project, study, money, na onno kichu? Ami help korar try korchi.", address)
                if style == "mixed"
                else _with_address("I understand. Tell me what tension is weighing on you--project, study, money, or something else. I will help calmly.", address)
            )
        elif topic == "project":
            answer = (
                _with_address("Nice. Project-er kon part-e help lagbe--idea, code, design, bug fix, na documentation?", address)
                if style == "mixed"
                else _with_address("Nice. Which part should we work on: idea, code, design, bug fix, or documentation?", address)
            )
        elif "kemon aso" in normalized or "ki obostha" in normalized:
            answer = _with_address(
                _pick_local_reply(
                    [
                        "Bhalo achi. Apnar jonno ready. Ki niye kotha bolbo?",
                        "Valo achi. Apnar ki obostha? Ki help korte pari?",
                    ],
                    message,
                    history,
                ),
                address,
            )
        else:
            answer = (
                _with_address(
                    _pick_local_reply(
                        [
                            "Bolun, ki niye kotha bolte chan? Ami ekhane achi.",
                            "Ami shunchi. Apni normal vabe bolun, ami help korbo.",
                            "Bolun, ami apnar sathe achi. Kon dik theke shuru korbo?",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
                if style == "mixed"
                else _with_address(
                    _pick_local_reply(
                        [
                            "Tell me what you want to talk through. I am here.",
                            "I am listening. Say it naturally, and I will help.",
                            "Tell me where you want to start.",
                        ],
                        message,
                        history,
                    ),
                    address,
                )
            )
    else:
        answer = _with_address("I am Nexa, your local desktop assistant. Ask me anything or give me a safe task to preview.", address)

    _record_chat_event(intent, "completed", message, "Local assistant conversation.")
    debug = _local_conversation_debug_enabled()
    return ChatMessageResponse(
        status="completed",
        intent=intent,
        message=message,
        answer=answer,
        provider=f"Nexa {provider_name} assistant" if provider_name != "local" else "Nexa local assistant",
        source="Local conversation",
        chips=["Local response", "Personal assistant", f"Topic: {topic}", f"Provider: {provider_name}", "No execution"] if debug else [],
        source_type="local",
    )


def _safe_get_json(url: str, allowed_hosts: set[str]) -> dict | list | None:
    host = urllib.parse.urlparse(url).hostname or ""
    if host not in allowed_hosts:
        return None
    try:
        response = httpx.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "NexaAI-Desktop-Assistant/1.0"},
        )
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:
        return None


def fetch_weather() -> ChatWeatherSnapshot | None:
    data = _safe_get_json(WEATHER_URL, WEATHER_ALLOWED_HOSTS)
    current = (data or {}).get("current") if isinstance(data, dict) else {}
    if not current:
        return None
    code = current.get("weather_code")
    condition = WEATHER_CODE_SUMMARY.get(code, "Weather data available")
    humidity = current.get("relative_humidity_2m")
    return ChatWeatherSnapshot(
        location=DEFAULT_LOCATION,
        temperature_c=current.get("temperature_2m"),
        condition=condition,
        wind_kph=current.get("wind_speed_10m"),
        humidity_percent=int(humidity) if humidity is not None else None,
    )


def _weather_answer(snapshot: ChatWeatherSnapshot, language_style: str = "english") -> str:
    if language_style == "bangla":
        parts = [f"ঢাকার বর্তমান আবহাওয়া: {snapshot.condition or 'তথ্য পাওয়া গেছে'}।"]
        if snapshot.temperature_c is not None:
            parts.append(f"তাপমাত্রা {snapshot.temperature_c:g} ডিগ্রি সেলসিয়াস।")
        if snapshot.humidity_percent is not None:
            parts.append(f"আর্দ্রতা {snapshot.humidity_percent} শতাংশ।")
        if snapshot.wind_kph is not None:
            parts.append(f"বাতাসের গতি ঘণ্টায় {snapshot.wind_kph:g} কিলোমিটার।")
        parts.append("আর কিছু জানতে চান?")
        return " ".join(parts)
    parts = [f"Dhaka weather now: {snapshot.condition or 'current conditions available'}."]
    if snapshot.temperature_c is not None:
        parts.append(f"Temperature is {snapshot.temperature_c:g}°C.")
    if snapshot.humidity_percent is not None:
        parts.append(f"Humidity is {snapshot.humidity_percent}%.")
    if snapshot.wind_kph is not None:
        parts.append(f"Wind is {snapshot.wind_kph:g} km/h.")
    return " ".join(parts)


def clean_web_query(message: str) -> str:
    cleaned = normalize_text(message)
    replacements = [
        r"\bgoogle theke\b",
        r"\bgoogle থেকে\b",
        r"\bgoogle\b",
        r"\bsearch kore bolo\b",
        r"\bsearch করে বলো\b",
        r"\bsearch\b",
        r"\btheke\b",
        r"\bbolo\b",
        r"\bplease\b",
        r"\btell me\b",
        r"\bবল[ো]\b",
    ]
    for pattern in replacements:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()) or message.strip()


def wikipedia_search(query: str, lang: str = "en") -> list[ChatSearchResult]:
    encoded = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": "1",
            "srlimit": "3",
        }
    )
    host = "bn.wikipedia.org" if lang == "bn" else "en.wikipedia.org"
    url = f"https://{host}/w/api.php?{encoded}"
    data = _safe_get_json(url, SEARCH_ALLOWED_HOSTS)
    if not isinstance(data, dict):
        return []
    rows = ((data.get("query") or {}).get("search") or [])[:3]
    results: list[ChatSearchResult] = []
    for row in rows:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        snippet = re.sub("<[^>]+>", "", str(row.get("snippet") or "")).strip()
        page = urllib.parse.quote(title.replace(" ", "_"))
        results.append(
            ChatSearchResult(
                title=title,
                snippet=snippet,
                source_url=f"https://{host}/wiki/{page}",
                provider=f"Wikipedia Search ({lang})",
            )
        )
    return results


def search_with_fallback(query: str) -> tuple[str, str, str | None, list[ChatSearchResult], str | None]:
    instant = answer_question(query)
    if instant.get("answered"):
        return (
            instant.get("answer") or "",
            instant.get("source") or "DuckDuckGo/Wikipedia",
            instant.get("source_url"),
            [
                ChatSearchResult(
                    title=instant.get("source") or "Safe instant answer",
                    snippet=instant.get("answer") or "",
                    source_url=instant.get("source_url"),
                    provider=instant.get("source") or "DuckDuckGo/Wikipedia",
                )
            ],
            None,
        )

    results = wikipedia_search(query, "en")
    if results:
        top = results[0]
        answer = (
            f"I found this from safe public search results: {top.title}. "
            f"{top.snippet or 'Open the source for more details.'}"
        )
        return answer, top.provider, top.source_url, results, None

    error = (
        "I could not find a reliable result from the free safe providers "
        "available right now. Try a more specific query."
    )
    return error, "DuckDuckGo/Wikipedia", None, [], error


def _extract_translation_text(message: str) -> str:
    if ":" in message:
        return message.split(":", 1)[1].strip()
    cleaned = re.sub(
        r"(?i)^(translate this to bangla|translate to bangla|ei sentence er bangla ki|etar meaning ki|meaning ki|mane ki)\s*",
        "",
        message.strip(),
    )
    return cleaned.strip()


def translate_or_explain(message: str) -> tuple[str, str]:
    text = _extract_translation_text(message)
    if not text:
        return "Please include the sentence you want translated or explained.", "Local translation helper"
    phrase_map = {
        "i am working on my project": "আমি আমার প্রজেক্টে কাজ করছি।",
        "i am working on my project.": "আমি আমার প্রজেক্টে কাজ করছি।",
        "what does this mean": "এর মানে জানতে বাক্যটি লিখুন।",
    }
    key = normalize_text(text)
    if key in phrase_map:
        return f"Bangla: {phrase_map[key]}", "Local translation helper"

    words = {
        "i": "আমি",
        "am": "হচ্ছি/আছি",
        "working": "কাজ করছি",
        "on": "উপর/নিয়ে",
        "my": "আমার",
        "project": "প্রজেক্ট",
        "hello": "হ্যালো",
        "thanks": "ধন্যবাদ",
    }
    translated = [words.get(part.lower().strip(".,!?"), part) for part in text.split()]
    if translated != text.split():
        return "Bangla (simple): " + " ".join(translated), "Local translation helper"

    return (
        f"Meaning/explanation: '{text}' looks like a phrase or sentence. "
        "I can explain common English/Bangla/Banglish phrases locally; for specific factual meaning I will use safe web search.",
        "Local explanation helper",
    )


def current_time_answer(message: str) -> tuple[str, str]:
    normalized = normalize_text(message)
    if "india" in normalized or "kolkata" in normalized or "ভারত" in normalized:
        label = "India"
        tz_name = "Asia/Kolkata"
    elif "dhaka" in normalized or "bangladesh" in normalized or "বাংলাদেশ" in normalized:
        label = "Dhaka, Bangladesh"
        tz_name = "Asia/Dhaka"
    else:
        label = "Dhaka, Bangladesh"
        tz_name = "Asia/Dhaka"
    now = datetime.now(ZoneInfo(tz_name))
    if _language_style(message) == "bangla":
        return (
            f"{label}-এর বর্তমান সময় {now.strftime('%I:%M %p')}। আজ {now.strftime('%d-%m-%Y')}।",
            tz_name,
        )
    return (
        f"Current time in {label}: {now.strftime('%I:%M %p')} on {now.strftime('%A, %d %B %Y')} ({tz_name}).",
        tz_name,
    )


def _safe_calculator_answer(message: str) -> str:
    return calculate_local_expression(message)


def _record_chat_event(intent: str, status: str, message: str, detail: str = "") -> None:
    risk = "blocked" if status == "blocked" else "confirmation_required" if intent.endswith("request") else "safe"
    record_audit_event(
        source="chat",
        intent=intent,
        status=status,
        risk_level=risk,
        target=message[:120],
        message=detail[:240],
    )


def _parse_contact_save(message: str) -> tuple[str | None, str | None, str | None, str | None]:
    raw = " ".join(message.strip().split())
    patterns = [
        r"(?i)^(?P<name>.+?)\s+er\s+number\s+save\s+koro\s+(?P<phone>\+?[\d\s-]+?)(?:\s+relationship\s+(?P<relationship>boss|client|friend|family|unknown))?(?:\s+tone\s+(?P<tone>formal|friendly|normal))?$",
        r"(?i)^(?P<name>.+?)\s+ke\s+whatsapp\s+contact\s+hisebe\s+save\s+koro\s+(?P<phone>\+?[\d\s-]+?)(?:\s+relationship\s+(?P<relationship>boss|client|friend|family|unknown))?(?:\s+tone\s+(?P<tone>formal|friendly|normal))?$",
        r"(?i)^(?P<name>.+?)\s+ke\s+WhatsApp\s+contact\s+hisebe\s+save\s+koro\s+(?P<phone>\+?[\d\s-]+?)(?:\s+relationship\s+(?P<relationship>boss|client|friend|family|unknown))?(?:\s+tone\s+(?P<tone>formal|friendly|normal))?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return (
                " ".join(match.group("name").strip(" ,:").split()),
                " ".join(match.group("phone").strip().split()),
                match.groupdict().get("relationship"),
                match.groupdict().get("tone"),
            )
    return None, None, None, None


def _parse_contact_alias_add(message: str) -> tuple[str | None, str | None]:
    raw = " ".join(message.strip().split())
    patterns = [
        r"(?i)^(?P<name>.+?)\s+er\s+alias\s+(?P<alias>.+?)\s+add\s+koro$",
        r"(?i)^(?P<name>.+?)\s+alias\s+(?P<alias>.+?)\s+add\s+koro$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return (
                " ".join(match.group("name").strip(" ,:").split()),
                " ".join(match.group("alias").strip(" ,:").split()),
            )
    return None, None


def _parse_contact_name(message: str) -> str | None:
    raw = " ".join(message.strip().split())
    patterns = [
        r"(?i)^(?P<name>.+?)\s+er\s+number\s+ki$",
        r"(?i)^(?P<name>.+?)\s+er\s+whatsapp\s+contact\s+delete\s+koro$",
        r"(?i)^(?P<name>.+?)\s+er\s+contact\s+delete\s+koro$",
        r"(?i)^(?P<name>.+?)\s+er\s+number\s+delete\s+koro$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            return " ".join(match.group("name").strip(" ,:").split())
    return None


def _contact_command_response(message: str, address_style: str | None = None) -> ChatMessageResponse:
    normalized = normalize_text(message)
    style = _language_style(message)
    address = _address_label(address_style, style)

    if any(marker in normalized for marker in CONTACT_SAVE_KEYWORDS):
        name, phone, relationship, tone = _parse_contact_save(message)
        if not name or not phone:
            answer = _with_address("Contact save korte name and valid number din. Example: Rahim er number save koro 017xxxxxxxx.", address)
            return ChatMessageResponse(
                status="needs_more_info",
                intent="contact_save",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Need name and number", "No cloud sync"],
                error=answer,
            )
        try:
            record = save_contact(name, phone, relationship=relationship, default_tone=tone)
        except ValueError as exc:
            answer = _with_address(str(exc), address)
            return ChatMessageResponse(
                status="blocked",
                intent="contact_save",
                message=message,
                answer=answer,
                blocked=True,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Invalid phone", "No execution"],
                error=str(exc),
            )
        answer = _with_address(
            f"{record.name} saved locally for WhatsApp drafts: {record.phone_number}. "
            f"Relationship: {record.relationship}; default tone: {record.default_tone}.",
            address,
        )
        _record_chat_event("contact_save", "saved", message, record.name)
        return ChatMessageResponse(
            status="saved",
            intent="contact_save",
            message=message,
            answer=answer,
            provider="Local WhatsApp contacts",
            source="Local JSON contact store",
            chips=["Local contact", "Saved", "No cloud sync"],
        )

    if any(marker in normalized for marker in CONTACT_ALIAS_KEYWORDS):
        name, alias = _parse_contact_alias_add(message)
        if not name or not alias:
            answer = _with_address("Alias add korte contact name and alias din. Example: Rahim er alias Rohim add koro.", address)
            return ChatMessageResponse(
                status="needs_more_info",
                intent="contact_alias_add",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Need name and alias"],
                error=answer,
            )
        record = add_contact_alias(name, alias)
        if not record:
            answer = _with_address(f"{name} local contact-e pai nai, or match ambiguous.", address)
            return ChatMessageResponse(
                status="not_found",
                intent="contact_alias_add",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Alias not saved"],
                error=answer,
            )
        answer = _with_address(f"{record.name}-er alias saved: {alias}.", address)
        _record_chat_event("contact_alias_add", "saved", message, record.name)
        return ChatMessageResponse(
            status="saved",
            intent="contact_alias_add",
            message=message,
            answer=answer,
            provider="Local WhatsApp contacts",
            source="Local JSON contact store",
            chips=["Local contact", "Alias saved"],
        )

    name = _parse_contact_name(message)
    if any(marker in normalized for marker in CONTACT_QUERY_KEYWORDS):
        matches = find_contact_matches(name)
        if len(matches) > 1:
            names = ", ".join(contact.name for contact in matches[:5])
            answer = _with_address(f"Multiple local contacts match '{name}'. Please clarify: {names}.", address)
            return ChatMessageResponse(
                status="needs_more_info",
                intent="contact_lookup",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Ambiguous match", "No execution"],
                error=answer,
            )
        contact = matches[0] if matches else get_contact(name)
        if not contact:
            answer = _with_address(f"{name or 'Oi contact'}-er phone number local contact-e pai nai.", address)
            return ChatMessageResponse(
                status="not_found",
                intent="contact_lookup",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Not found"],
                error=answer,
            )
        answer = _with_address(f"{contact.name}-er WhatsApp number: {contact.phone_number}.", address)
        return ChatMessageResponse(
            status="completed",
            intent="contact_lookup",
            message=message,
            answer=answer,
            provider="Local WhatsApp contacts",
            source="Local JSON contact store",
            chips=["Local contact", "Found"],
        )

    if any(marker in normalized for marker in CONTACT_DELETE_KEYWORDS):
        matches = find_contact_matches(name)
        if len(matches) > 1:
            names = ", ".join(contact.name for contact in matches[:5])
            answer = _with_address(f"Multiple local contacts match '{name}'. Please clarify which one to delete: {names}.", address)
            return ChatMessageResponse(
                status="needs_more_info",
                intent="contact_delete",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Ambiguous match", "No execution"],
                error=answer,
            )
        resolved_name = matches[0].name if matches else name
        deleted = delete_contact(resolved_name)
        if not deleted:
            answer = _with_address(f"{name or 'Oi contact'} local contact-e pai nai.", address)
            return ChatMessageResponse(
                status="not_found",
                intent="contact_delete",
                message=message,
                answer=answer,
                provider="Local WhatsApp contacts",
                source="Local JSON contact store",
                chips=["Local contact", "Not found"],
                error=answer,
            )
        answer = _with_address(f"{resolved_name} local WhatsApp contacts theke delete kora hoyeche.", address)
        _record_chat_event("contact_delete", "deleted", message, resolved_name or "")
        return ChatMessageResponse(
            status="deleted",
            intent="contact_delete",
            message=message,
            answer=answer,
            provider="Local WhatsApp contacts",
            source="Local JSON contact store",
            chips=["Local contact", "Deleted"],
        )

    return conversational_answer(message, "casual_chat", address_style)


def _execute_trusted_website_open(
    *,
    url: str,
    label: str,
    original_text: str,
    intent: str,
    success_answer: str,
    action_kind: str = "website",
    recipient: str | None = None,
    draft_text: str | None = None,
    action_label: str | None = None,
    fallback_urls: list[str] | None = None,
    address_style: str | None = None,
) -> ChatMessageResponse:
    if not is_permission_enabled("actions_website"):
        denied = permission_denied_message("actions_website")
        _record_chat_event(intent, "blocked", original_text, denied)
        return ChatMessageResponse(
            status="blocked",
            intent=intent,
            message=original_text,
            answer=denied,
            blocked=True,
            requires_confirmation=False,
            execution_enabled=False,
            provider="Safe website whitelist",
            source="Security Center",
            source_url=url,
            chips=["Trusted skill", "Permission disabled"],
            error=denied,
        )
    urls_to_try = [url, *(fallback_urls or [])]
    result = None
    used_url = url
    for candidate_url in urls_to_try:
        request = ActionExecutionRequest(
            intent="open_website",
            target=ActionTarget(kind="url", value=candidate_url, label=label),
            original_text=original_text,
            normalized_text=normalize_text(original_text),
            confidence=100,
            user_confirmed=True,
            dry_run=False,
            source="chat_trusted_skill",
        )
        result = execute_open_website(request)
        used_url = candidate_url
        if result.executed:
            break
    assert result is not None
    if result.executed and action_kind == "whatsapp_draft":
        answer = compose_intent(
            "whatsapp_draft_done",
            address_style=address_style,
            language_style=_language_style(original_text),
            user_message=original_text,
        )
    elif result.executed and intent == "youtube_search":
        query = label.split(":", 1)[1].strip() if ":" in label else label
        answer = compose_intent(
            "youtube_search_done",
            address_style=address_style,
            language_style=_language_style(original_text),
            user_message=original_text,
            query=query,
        )
    elif result.executed and intent == "youtube_open":
        answer = compose_intent(
            "youtube_open_done",
            address_style=address_style,
            language_style=_language_style(original_text),
            user_message=original_text,
        )
    else:
        answer = _compose_reply(success_answer, address_style) if result.executed else result.error or result.message
    _record_chat_event(intent, result.status, original_text, answer)
    simple_chip = "WhatsApp draft" if action_kind == "whatsapp_draft" else ("YouTube search" if intent == "youtube_search" else ("YouTube" if intent == "youtube_open" else "Action"))
    return ChatMessageResponse(
        status=result.status,
        intent=intent,
        message=original_text,
        answer=answer,
        blocked=result.status == "blocked",
        requires_confirmation=False,
        execution_enabled=result.executed,
        auto_execute_safe=result.executed,
        provider="Trusted safe website action",
        source="Safe website whitelist",
        source_url=used_url,
        chips=[simple_chip],
        action=ChatActionStatus(
            kind=action_kind,
            target=used_url,
            label=label,
            executed=result.executed,
            requires_confirmation=False,
            message=answer,
            recipient=recipient,
            draft_text=draft_text,
            action_label=action_label,
        ),
        error=result.error,
    )


def _clean_youtube_query(message: str) -> str:
    query = normalize_text(message)
    replacements = [
        r"\bopen youtube and search\b",
        r"\byoutube e\b",
        r"\byoutube te\b",
        r"\byt te\b",
        r"\bon youtube\b",
        r"\byoutube\b",
        r"ইউটিউব",
        r"\byou tube\b",
        r"\byt\b",
        r"\bsearch koro\b",
        r"\bsearch dao\b",
        r"\bsearch\b",
        r"\bgaan chalao\b",
        r"\bsong chalao\b",
        r"\bvideo chalao\b",
        r"\bplay\b",
        r"গান চালাও",
        r"চালাও",
        r"খুলে",
        r"\bkhuje dao\b",
        r"\bkhuje\b",
        r"\bopen koro\b",
        r"\bopen\b",
        r"\bkoro\b",
    ]
    for pattern in replacements:
        query = re.sub(pattern, " ", query, flags=re.IGNORECASE)
    return " ".join(query.split())


def _youtube_skill_response(message: str, address_style: str | None = None) -> ChatMessageResponse:
    if not is_permission_enabled("youtube_skill"):
        denied = permission_denied_message("youtube_skill")
        _record_chat_event("youtube_skill", "blocked", message, denied)
        return ChatMessageResponse(
            status="blocked",
            intent="youtube_skill",
            message=message,
            answer=denied,
            blocked=True,
            chips=["YouTube skill", "Permission disabled"],
            error=denied,
        )

    normalized = normalize_text(message)
    parsed_control = parse_youtube_command(message)
    if parsed_control.action not in {"launch", "search"}:
        if not is_permission_enabled("youtube_control"):
            denied = permission_denied_message("youtube_control")
            _record_chat_event("youtube_control", "blocked", message, denied)
            return ChatMessageResponse(
                status="blocked",
                intent="youtube_control",
                message=message,
                answer=denied,
                blocked=True,
                chips=["YouTube control", "Permission disabled"],
                error=denied,
            )
        action_label = (
            f"Play {parsed_control.query}"
            if parsed_control.query
            else parsed_control.action.replace("_", " ").title()
        )
        answer = (
            f"Ready to apply YouTube control: {action_label}. "
            "Confirm it below; Nexa will only control its dedicated YouTube window."
        )
        _record_chat_event("youtube_control", "preview_only", message, parsed_control.action)
        return ChatMessageResponse(
            status="preview_only",
            intent="youtube_control",
            message=message,
            answer=answer,
            requires_confirmation=True,
            provider="Nexa YouTube Controller",
            source="Controlled Chrome player",
            chips=["YouTube", action_label, "Confirmation required"],
            action=ChatActionStatus(
                kind="youtube_control",
                target=message,
                label=f"YouTube: {action_label}",
                executed=False,
                requires_confirmation=True,
                message=answer,
                action_label=f"Confirm {action_label}",
            ),
        )

    wants_search = _has_any(normalized, SEARCH_ACTION_KEYWORDS) or _has_any(normalized, YOUTUBE_MEDIA_KEYWORDS) or "search" in normalized
    query = _clean_youtube_query(message) if wants_search else ""
    if wants_search and query:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
        if is_permission_enabled("trusted_youtube_auto_open"):
            return _execute_trusted_website_open(
                url=url,
                label=f"YouTube search: {query}",
                original_text=message,
                intent="youtube_search",
                success_answer=f"ami YouTube search open kortesi for '{query}'.",
                action_label="YouTube search opened",
                address_style=address_style,
            )

        answer = f"Ready to search YouTube for '{query}'. I will open the safe YouTube search URL only after you confirm."
        results: list[ChatSearchResult] = []
        provider = "YouTube safe URL"
        if is_permission_enabled("web_answers"):
            try:
                result = search_answer(f"site:youtube.com {query}")
                results = to_chat_results(result.results[:3])
                if result.provider:
                    provider = result.provider
                if result.answer and not result.error:
                    answer = (
                        f"Ready to search YouTube for '{query}'. "
                        f"Related source-backed result: {result.answer[:500]}"
                    )
            except Exception:
                results = []
        _record_chat_event("youtube_search", "preview_only", message, url)
        return ChatMessageResponse(
            status="preview_only",
            intent="youtube_search",
            message=message,
            answer=answer,
            requires_confirmation=True,
            provider=provider,
            source="YouTube safe search URL",
            source_url=url,
            chips=["YouTube", "Search", "Confirmation required", "No browser automation"],
            search_results=results,
            show_search_results_by_default=False,
            action=ChatActionStatus(
                kind="website",
                target=url,
                label=f"YouTube search: {query}",
                executed=False,
                requires_confirmation=True,
                message=answer,
                action_label="Open YouTube search",
            ),
        )

    url = "https://www.youtube.com"
    if is_permission_enabled("trusted_youtube_auto_open"):
        return _execute_trusted_website_open(
            url=url,
            label="YouTube",
            original_text=message,
            intent="youtube_open",
            success_answer="ami YouTube open kortesi.",
            action_label="YouTube opened",
            address_style=address_style,
        )

    answer = "Ready to open YouTube. I will only open the whitelisted YouTube URL after you confirm."
    _record_chat_event("youtube_open", "preview_only", message, url)
    return ChatMessageResponse(
        status="preview_only",
        intent="youtube_open",
        message=message,
        answer=answer,
        requires_confirmation=True,
        provider="YouTube safe URL",
        source="Safe website whitelist",
        source_url=url,
        chips=["YouTube", "Open", "Confirmation required"],
        action=ChatActionStatus(
            kind="website",
            target=url,
            label="YouTube",
            executed=False,
            requires_confirmation=True,
            message=answer,
            action_label="Open YouTube",
        ),
    )


def _infer_tone(text: str, contact=None) -> str:
    normalized = normalize_text(text)
    if any(marker in normalized for marker in ("formal", "professionally", "professional", "sir", "boss", "client")):
        return "formal"
    if any(marker in normalized for marker in ("friendly", "friend", "bhai", "vai", "ভাই")):
        return "friendly"
    if contact is not None:
        tone = getattr(contact, "default_tone", "normal") or "normal"
        relationship = getattr(contact, "relationship", "unknown") or "unknown"
        if tone in {"formal", "friendly", "normal"}:
            return tone
        if relationship in {"boss", "client"}:
            return "formal"
        if relationship in {"friend", "family"}:
            return "friendly"
    return "normal"


def _clean_draft_text(text: str) -> str:
    cleaned = re.sub(r"(?i)\b(formal|friendly|professional|shundor kore|valo kore|same message|exact message|hubohu)\b", " ", text)
    return " ".join(cleaned.split()).strip(" ,:")


def _parse_whatsapp_draft(message: str) -> WhatsAppDraftIntent:
    raw = " ".join(message.strip().split())
    normalized = normalize_text(raw)
    exact = any(marker in normalized for marker in ("same message", "exact message", "hubohu", "as it is"))
    patterns = [
        r"(?i)whatsapp\s+e\s+(?P<recipient>.+?)\s+ke\s+(?:bolo|likho|message\s+dao|message|draft\s+koro|draft|send|sms\s+dao|pathanor\s+jonno\s+ready\s+koro)\s+(?P<text>.+)",
        r"(?i)(?P<recipient>.+?)\s+(?:ke|k)\s+whatsapp\s+e\s+(?:bolo|likho|message\s+dao|message|draft\s+koro|draft|send|sms\s+dao|pathanor\s+jonno\s+ready\s+koro)\s+(?P<text>.+)",
        r"(?i)(?P<recipient>.+?)\s+(?:ke|k)\s+(?:message\s+dao|sms\s+dao|sms|bolo|likho|draft\s+koro|draft)\s+(?P<text>.+)",
        r"(?i)whatsapp\s+(?:message|draft)\s+(?P<recipient>.+?)\s*:\s*(?P<text>.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match:
            recipient = " ".join(match.group("recipient").strip(" ,:").split())
            recipient = re.sub(r"(?i)^amar\s+", "", recipient).strip()
            text = _clean_draft_text(" ".join(match.group("text").strip(" ,:").split()))
            return WhatsAppDraftIntent(recipient or None, text or None, _infer_tone(raw), exact)
    missing_text_patterns = [
        r"(?i)^whatsapp\s+(?P<recipient>.+?)\s+draft$",
        r"(?i)^whatsapp\s+e\s+(?P<recipient>.+?)\s+draft$",
        r"(?i)^(?P<recipient>.+?)\s+ke\s+whatsapp\s+draft$",
    ]
    for pattern in missing_text_patterns:
        match = re.search(pattern, raw)
        if match:
            recipient = re.sub(r"(?i)^amar\s+", "", " ".join(match.group("recipient").strip(" ,:").split())).strip()
            return WhatsAppDraftIntent(recipient or None, None, _infer_tone(raw), exact)
    return WhatsAppDraftIntent()


def _should_use_llm_for_draft(message: str, contact, intent: WhatsAppDraftIntent) -> bool:
    if intent.exact:
        return False
    relationship = getattr(contact, "relationship", "unknown") or "unknown"
    tone = intent.tone or getattr(contact, "default_tone", "normal") or "normal"
    raw = intent.raw_message or ""
    return (
        whatsapp_draft_needs_llm(message)
        or relationship in {"boss", "client"}
        or tone == "formal"
        or len(raw.split()) > 16
    )


def _normalize_whatsapp_target(value: str | None) -> str:
    target = normalize_text(value or "auto").replace("_", " ").replace("-", " ")
    if target in {"app", "whatsapp app", "desktop", "whatsapp desktop"}:
        return "app"
    if target in {"web", "whatsapp web"}:
        return "web"
    if target in {"wa", "wa me", "wame", "wa.me", "fallback"}:
        return "wa_me"
    return "auto"


def _whatsapp_draft_urls(phone: str, text: str, preference: str | None) -> list[str]:
    encoded = urllib.parse.quote_plus(text)
    app_url = f"whatsapp://send?phone={phone}&text={encoded}"
    web_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"
    wa_url = f"https://wa.me/{phone}?text={encoded}"
    target = _normalize_whatsapp_target(preference)
    if target == "app":
        return [app_url, wa_url, web_url]
    if target == "web":
        return [web_url]
    if target == "wa_me":
        return [wa_url]
    return [app_url, wa_url, web_url]


def _local_compose_whatsapp_draft(contact, raw_message: str, tone: str, exact: bool = False) -> str:
    cleaned = " ".join(raw_message.strip().split())
    if exact:
        return cleaned
    relationship = getattr(contact, "relationship", "unknown") or "unknown"
    if tone == "formal" or relationship in {"boss", "client"}:
        lower = normalize_text(cleaned)
        if "office" in lower and ("aste parbo na" in lower or "come" in lower):
            return (
                "Assalamu Alaikum Sir,\n"
                "Due to an unavoidable reason, I will not be able to come to the office tomorrow.\n"
                "Thank you."
            )
        return f"Assalamu Alaikum Sir,\n{cleaned}.\nThank you."
    if tone == "friendly" or relationship in {"friend", "family"}:
        if normalize_text(cleaned) == "ami pore call korbo":
            return "ভাই, আমি পরে call করব।"
        return f"ভাই, {cleaned}."
    if normalize_text(cleaned) == "ami pore call korbo":
        return "ভাই, আমি পরে call করব।"
    return cleaned


def _whatsapp_skill_response(
    message: str,
    draft_open_target: str | None = "auto",
    address_style: str | None = None,
) -> ChatMessageResponse:
    if not is_permission_enabled("whatsapp_draft_skill") and not is_permission_enabled("trusted_whatsapp_draft_auto_open"):
        denied = permission_denied_message("whatsapp_draft_skill")
        _record_chat_event("whatsapp_skill", "blocked", message, denied)
        return ChatMessageResponse(
            status="blocked",
            intent="whatsapp_skill",
            message=message,
            answer=denied,
            blocked=True,
            chips=["WhatsApp skill", "Permission disabled"],
            error=denied,
        )

    normalized = normalize_text(message)
    draft_intent = _parse_whatsapp_draft(message)
    recipient = draft_intent.recipient
    draft_text = draft_intent.raw_message
    wants_draft = bool(recipient or draft_text) or _has_any(normalized, MESSAGE_ACTION_KEYWORDS)
    if wants_draft:
        if not _has_phrase_or_token(normalized, WHATSAPP_KEYWORDS):
            answer = _compose_reply(
                "eta WhatsApp draft hisebe ready korbo? Contact number thakle open kore dite parbo. Send ami click korbo na.",
                address_style,
            )
            _record_chat_event("whatsapp_draft", "needs_more_info", message, "Implicit contact-message command needs WhatsApp confirmation.")
            return ChatMessageResponse(
                status="needs_more_info",
                intent="whatsapp_draft",
                message=message,
                answer=answer,
                requires_confirmation=False,
                execution_enabled=False,
                provider="WhatsApp safe draft",
                source="Local contact resolver",
                chips=["WhatsApp draft"],
                action=ChatActionStatus(
                    kind="whatsapp_draft",
                    target="",
                    label=f"WhatsApp draft to {recipient or 'contact'}",
                    executed=False,
                    requires_confirmation=False,
                    message=answer,
                    recipient=recipient,
                    draft_text=draft_text,
                    action_label="Confirm WhatsApp draft",
                ),
            )
        if not recipient:
            answer = "I can prepare a WhatsApp draft, but I need the contact name. Example: whatsapp e Rahim ke bolo ami pore call korbo."
            _record_chat_event("whatsapp_draft", "needs_more_info", message, "Missing recipient or draft text.")
            return ChatMessageResponse(
                status="needs_more_info",
                intent="whatsapp_draft",
                message=message,
                answer=answer,
                requires_confirmation=False,
                chips=["WhatsApp", "Draft only", "Need contact and message"],
                error=answer,
            )
        matches = find_contact_matches(recipient)
        if len(matches) > 1:
            names = ", ".join(contact.name for contact in matches[:5])
            answer = (
                f"Multiple local WhatsApp contacts match '{recipient}': {names}. "
                "Please use the exact contact name. Nexa will not send anything automatically."
            )
            _record_chat_event("whatsapp_draft", "needs_more_info", message, f"Ambiguous contact: {recipient}")
            return ChatMessageResponse(
                status="needs_more_info",
                intent="whatsapp_draft",
                message=message,
                answer=answer,
                requires_confirmation=False,
                execution_enabled=False,
                provider="WhatsApp safe draft",
                source="Local contact resolver",
                chips=["WhatsApp", "Draft only", "Ambiguous contact", "Auto-send locked"],
                action=ChatActionStatus(
                    kind="whatsapp_draft",
                    target="",
                    label=f"WhatsApp draft to {recipient}",
                    executed=False,
                    requires_confirmation=False,
                    message=answer,
                    recipient=recipient,
                    draft_text=draft_text,
                    action_label="Clarify contact",
                ),
                error=answer,
            )
        contact = matches[0] if matches else get_contact(recipient)
        if not contact:
            task = set_pending_task(whatsapp_number_task(recipient, draft_text or "", message))
            answer = (
                f"{recipient}-er phone number ta den Boss, ami local contact hisebe save kore next time draft open kore dibo. "
                "Nexa will not send anything automatically."
            )
            _record_chat_event("whatsapp_draft", "needs_more_info", message, f"Unknown contact: {recipient}")
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="whatsapp_draft",
                message=message,
                answer=answer,
                requires_confirmation=False,
                provider="WhatsApp safe draft",
                source="Local contact resolver",
                chips=["WhatsApp", "Draft only", "Phone number needed", "Auto-send locked"],
                action=ChatActionStatus(
                    kind="whatsapp_draft",
                    target="",
                    label=f"WhatsApp draft to {recipient}",
                    executed=False,
                    requires_confirmation=False,
                    message=answer,
                    recipient=recipient,
                    draft_text=draft_text,
                    action_label="Phone number needed",
                ),
                error=answer,
            ), task)
        if not draft_text:
            task = set_pending_task(whatsapp_message_task(contact.name, message))
            answer = f"Boss, {contact.name}-er jonno message ta ki likhbo?"
            _record_chat_event("whatsapp_draft", "needs_more_info", message, f"Missing message for {contact.name}")
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="whatsapp_draft",
                message=message,
                answer=answer,
                requires_confirmation=False,
                execution_enabled=False,
                provider="WhatsApp safe draft",
                source="Local contact resolver",
                chips=["WhatsApp", "Draft only", "Message needed", "Auto-send locked"],
                action=ChatActionStatus(
                    kind="whatsapp_draft",
                    target="",
                    label=f"WhatsApp draft to {contact.name}",
                    executed=False,
                    requires_confirmation=False,
                    message=answer,
                    recipient=contact.name,
                    action_label="Message needed",
                ),
                error=answer,
            ), task)

        phone = contact.phone_number
        draft_intent.tone = _infer_tone(message, contact)
        final_draft = _local_compose_whatsapp_draft(contact, draft_text, draft_intent.tone, draft_intent.exact)
        composed = None
        if _should_use_llm_for_draft(message, contact, draft_intent):
            composed = complete_llm(
                (
                    "Compose only the final WhatsApp draft message text. "
                    "Do not include explanations. Do not send anything. "
                    f"Recipient: {contact.name}. Relationship: {contact.relationship}. "
                    f"Tone: {draft_intent.tone}. Draft idea: {draft_text}"
                ),
                address_style=None,
                language_style=_language_style(message),
            )
            if composed and composed.answer.strip():
                final_draft = composed.answer.strip().strip('"')
        urls = _whatsapp_draft_urls(phone, final_draft, draft_open_target)
        url = urls[0]
        if is_permission_enabled("trusted_whatsapp_draft_auto_open"):
            response = _execute_trusted_website_open(
                url=url,
                label=f"WhatsApp draft to {contact.name}",
                original_text=message,
                intent="whatsapp_draft",
                success_answer=f"WhatsApp draft ready kore dilam for {contact.name}. Please review and press Send manually. Send ami click kori nai. Nexa did not click Send.",
                action_kind="whatsapp_draft",
                recipient=contact.name,
                draft_text=final_draft,
                action_label="WhatsApp draft opened",
                fallback_urls=urls[1:],
                address_style=address_style,
            )
            if composed:
                response.llm_used = True
                response.llm_provider = composed.provider
                response.fallback_used = composed.fallback_used
                response.source_type = "hybrid"
                response.chips.append(composed.provider)
            return response

        answer = (
            f"WhatsApp draft ready for {contact.name}: \"{final_draft}\". "
            "Confirm to open WhatsApp with this prepared text. Nexa will not click Send."
        )
        _record_chat_event("whatsapp_draft", "preview_only", message, f"{contact.name}: {final_draft}")
        return ChatMessageResponse(
            status="preview_only",
            intent="whatsapp_draft",
            message=message,
            answer=answer,
            requires_confirmation=True,
            provider="WhatsApp safe draft",
            source="WhatsApp draft URL",
            source_url=url,
            chips=["WhatsApp", "Draft only", "Confirmation required", "Auto-send locked"],
            llm_used=bool(composed),
            llm_provider=composed.provider if composed else None,
            fallback_used=composed.fallback_used if composed else False,
            source_type="hybrid" if composed else "tool",
            action=ChatActionStatus(
                kind="whatsapp_draft",
                target=url,
                label=f"WhatsApp draft to {contact.name}",
                executed=False,
                requires_confirmation=True,
                message=answer,
                recipient=contact.name,
                draft_text=final_draft,
                action_label="Open WhatsApp draft",
            ),
        )

    url = "https://web.whatsapp.com"
    if is_permission_enabled("trusted_whatsapp_draft_auto_open"):
        return _execute_trusted_website_open(
            url=url,
            label="WhatsApp Web",
            original_text=message,
            intent="whatsapp_open",
            success_answer="Done. WhatsApp Web opened.",
            action_label="WhatsApp opened",
        )

    answer = "Ready to open WhatsApp Web. I will only open the whitelisted WhatsApp URL after you confirm."
    _record_chat_event("whatsapp_open", "preview_only", message, url)
    return ChatMessageResponse(
        status="preview_only",
        intent="whatsapp_open",
        message=message,
        answer=answer,
        requires_confirmation=True,
        provider="WhatsApp Web",
        source="Safe website whitelist",
        source_url=url,
        chips=["WhatsApp", "Open", "Confirmation required", "No chat reading"],
        action=ChatActionStatus(
            kind="website",
            target=url,
            label="WhatsApp Web",
            executed=False,
            requires_confirmation=True,
            message=answer,
            action_label="Open WhatsApp",
        ),
    )


def _extract_phone_number(text: str) -> str | None:
    match = re.search(r"(?:\+?88)?01\d{9}", text)
    return match.group(0) if match else None


def _pending_whatsapp_from_history(history: list | None) -> tuple[str | None, str | None, str | None]:
    if not history:
        return None, None, None
    for item in reversed(history[-6:]):
        if getattr(item, "role", "") != "user":
            continue
        content = getattr(item, "content", "") or ""
        if "whatsapp" not in normalize_text(content) and not _looks_like_whatsapp_contact_message(normalize_text(content)):
            continue
        intent = _parse_whatsapp_draft(content)
        if intent.recipient and intent.raw_message:
            return intent.recipient, intent.raw_message, content
    return None, None, None


def _pending_whatsapp_number_response(
    message: str,
    history: list | None,
    draft_open_target: str | None,
    address_style: str | None,
) -> ChatMessageResponse | None:
    phone = _extract_phone_number(message)
    if not phone:
        return None
    pending_recipient, pending_text, pending_message = _pending_whatsapp_from_history(history)
    if not pending_recipient or not pending_text or not pending_message:
        return None
    explicit_name_match = re.match(r"(?i)^\s*(?P<name>[a-z][\w\s]{1,40}?)\s+number\s+", message.strip())
    name = " ".join(explicit_name_match.group("name").split()) if explicit_name_match else pending_recipient
    if normalize_text(name) not in {normalize_text(pending_recipient), "number"}:
        # Only continue the pending draft when the supplied name safely matches
        # the missing recipient or no explicit name was supplied.
        return None
    try:
        save_contact(pending_recipient, phone)
    except Exception as exc:
        answer = _compose_reply(str(exc), address_style)
        return ChatMessageResponse(
            status="blocked",
            intent="whatsapp_contact_continue",
            message=message,
            answer=answer,
            blocked=True,
            chips=["WhatsApp draft"],
            error=answer,
        )
    return _whatsapp_skill_response(pending_message, draft_open_target, address_style)


def _is_platform_only_detail(text: str) -> str | None:
    normalized = normalize_text(text)
    platforms = {
        "web": "web",
        "website": "web",
        "android": "android",
        "android app": "android",
        "desktop": "desktop",
        "desktop app": "desktop",
        "ai": "ai",
        "ai app": "ai",
    }
    return platforms.get(normalized)


def _extract_app_generation_context(text: str) -> dict[str, str]:
    normalized = normalize_text(text)
    data: dict[str, str] = {}
    if "food delivery" in normalized or "food delivari" in normalized:
        data["app_type"] = "food delivery"
    elif "ecommerce" in normalized or "e commerce" in normalized:
        data["app_type"] = "ecommerce"
    elif "medicine" in normalized:
        data["app_type"] = "medicine reminder"
    if "login page" in normalized or "log in page" in normalized:
        data["artifact"] = "login page"
    elif "home page" in normalized or "homepage" in normalized:
        data["artifact"] = "home page"
    elif "landing page" in normalized:
        data["artifact"] = "landing page"
    return data


def _looks_like_code_delivery_request(text: str) -> bool:
    normalized = normalize_text(text)
    return any(
        marker in normalized
        for marker in (
            "code deo",
            "code dao",
            "code kore dao",
            "tumi amake code deo",
            "write code",
            "generate code",
        )
    )


def _location_pending_matches(message: str) -> bool:
    normalized = normalize_text(message)
    return any(
        marker in normalized
        for marker in (
            "permission enabled",
            "allow location",
            "location allow",
            "share location",
            "location permission",
            "coordinates",
            "latitude",
            "longitude",
            "lat ",
            "lng ",
        )
    )


def _generation_or_setup_response(
    *,
    message: str,
    request: ChatMessageRequest,
    pending_task: PendingTask | None,
    intent: str = "llm_generation_continue",
) -> ChatMessageResponse:
    style = _language_style(message)
    context = build_task_context(
        user_message=message,
        intent=intent,
        language_style=style,
        pending_task=pending_task,
    )
    llm_response = _llm_answer_response(
        message,
        address_style=request.address_style,
        language_style=style,
        context=context,
        intent="llm_assist",
        pending_task=pending_task,
    )
    if llm_response:
        llm_response.intent = intent
        return llm_response
    return _llm_setup_answer(message, request.address_style, style, intent=intent)


def _handle_pending_task(message: str, task: PendingTask, request: ChatMessageRequest) -> ChatMessageResponse | None:
    if is_cancel_message(message):
        clear_pending_task()
        answer = compose_intent(
            "pending_cancelled",
            address_style=request.address_style,
            language_style=_language_style(message),
            user_message=message,
        )
        _record_chat_event("pending_task", "cancelled", message, task.kind)
        return ChatMessageResponse(
            status="cancelled",
            intent="pending_task_cancel",
            message=message,
            answer=answer,
            provider="Nexa local memory",
            source="Pending task state",
            chips=[],
            source_type="local",
        )

    if task.kind == "email_send_confirmation":
        if not is_confirm_message(message):
            # Keep the draft pending when speech recognition returns filler or an unclear answer.
            return _response_with_pending(ChatMessageResponse(
                status="needs_confirmation",
                intent="email_send_confirmation",
                message=message,
                answer="I have not sent it. Please say Yes to send, or Cancel to discard the draft.",
                requires_confirmation=True,
                provider="Nexa email",
                source="Pending email draft",
                chips=["Yes, send", "Cancel"],
            ), task)
        clear_pending_task()
        recipient = task.recipient or ""
        subject = str(task.data.get("subject") or "")
        body = str(task.data.get("body") or task.message or "")
        try:
            result = send_email(recipient=recipient, subject=subject, body=body)
        except Exception as exc:
            answer = f"I could not send the email: {exc}"
            return ChatMessageResponse(status="blocked", intent="email_send_confirmation", message=message, answer=answer, blocked=True, error=str(exc), chips=["Email not sent"])
        answer = f"Email sent successfully to {task.data.get('contact_name') or recipient}."
        return ChatMessageResponse(status="completed", intent="email_send_confirmation", message=message, answer=answer, execution_enabled=True, provider=str(result.get("provider") or "SMTP"), source="Confirmed email delivery", chips=["Email sent"], action=ChatActionStatus(kind="email", target=recipient, label="Send email", executed=True, requires_confirmation=False, message=answer, recipient=recipient, draft_text=body))

    if task.kind == "action_confirmation":
        if not is_confirm_message(message):
            clear_pending_task()
            return None

        clear_pending_task()
        action_kind = str(task.data.get("action_kind") or "")
        target = str(task.data.get("target") or "")
        label = str(task.data.get("label") or target)
        original_text = str(task.data.get("original_text") or message)
        language_style = _language_style(original_text)
        permission_key = "actions_app" if action_kind == "app" else "actions_website"
        if not is_permission_enabled(permission_key):
            denied = permission_denied_message(permission_key)
            return ChatMessageResponse(
                status="blocked",
                intent="voice_action_confirmation",
                message=message,
                answer=denied,
                blocked=True,
                chips=["Permission disabled"],
                error=denied,
            )

        action_request = ActionExecutionRequest(
            intent="open_app" if action_kind == "app" else "open_website",
            target=ActionTarget(kind=action_kind, value=target, label=label),
            original_text=original_text,
            normalized_text=normalize_text(original_text),
            confidence=100,
            user_confirmed=True,
            dry_run=False,
            source="voice_confirmation",
        )
        result = execute_open_app(action_request) if action_kind == "app" else execute_open_website(action_request)
        if result.executed:
            answer_text = (
                f"আপনার অনুমতি অনুযায়ী {label} খুলে দিয়েছি। আর কিছু করতে পারি?"
                if language_style == "bangla"
                else f"Opened {label}. What would you like me to do next?"
            )
        else:
            answer_text = result.error or result.message
        answer = _compose_reply(answer_text, request.address_style, language_style)
        status = result.status
        _record_chat_event("voice_action_confirmation", status, original_text, answer)
        return ChatMessageResponse(
            status=status,
            intent="voice_action_confirmation",
            message=message,
            answer=answer,
            blocked=status == "blocked",
            execution_enabled=result.executed,
            auto_execute_safe=result.executed,
            provider="Safe action whitelist",
            source="Voice confirmation",
            chips=["Voice confirmation"],
            action=ChatActionStatus(
                kind=action_kind,
                target=target,
                label=label,
                executed=result.executed,
                requires_confirmation=False,
                message=answer,
            ),
            error=result.error,
        )

    if task.kind == "whatsapp_contact_number":
        phone = _extract_phone_number(message)
        if not phone:
            return None
        recipient = task.recipient or "contact"
        draft_text = task.message or ""
        try:
            save_contact(recipient, phone)
        except Exception as exc:
            answer = _compose_reply(str(exc), request.address_style)
            return _response_with_pending(ChatMessageResponse(
                status="blocked",
                intent="whatsapp_contact_continue",
                message=message,
                answer=answer,
                blocked=True,
                chips=["WhatsApp draft"],
                error=answer,
            ), task)
        clear_pending_task()
        original = str(task.data.get("original_text") or f"whatsapp e {recipient} ke bolo {draft_text}")
        return _whatsapp_skill_response(original, request.whatsapp_draft_open_target, request.address_style)

    if task.kind == "whatsapp_message_text":
        recipient = task.recipient
        if not recipient or len(message.strip()) < 2:
            return None
        clear_pending_task()
        original = f"whatsapp e {recipient} ke bolo {message.strip()}"
        return _whatsapp_skill_response(original, request.whatsapp_draft_open_target, request.address_style)

    if task.kind == "app_planning_details":
        normalized_pending_message = normalize_text(message)
        if _looks_truly_incomplete(normalized_pending_message):
            clear_pending_task()
            return None
        platform = _is_platform_only_detail(message)
        if platform:
            task.data["platform"] = platform
            task.prompt = "Need app type and main feature/page"
            task.status_label = "Waiting for app type/features"
            set_pending_task(task)
            answer = _compose_reply(
                f"platform {platform} hisebe nilam. App ta kon type-er--food delivery, ecommerce, medicine reminder, na onno kichu? Login page/code lagle bolun.",
                request.address_style,
                _language_style(message),
            )
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="app_planning_continue",
                message=message,
                answer=answer,
                provider="Nexa local assistant",
                source="Pending task state",
                chips=[],
                source_type="local",
            ), task)

        context_bits = _extract_app_generation_context(message)
        if context_bits.get("artifact") and not context_bits.get("app_type") and not task.data.get("app_type"):
            task.data.update(context_bits)
            task.prompt = "Need app type for requested page"
            task.status_label = "Waiting for app type/page context"
            set_pending_task(task)
            answer = _compose_reply(
                "kon app-er login page? Food delivery, ecommerce, medicine reminder, na onno kichu?",
                request.address_style,
                _language_style(message),
            )
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="app_planning_continue",
                message=message,
                answer=answer,
                provider="Nexa local assistant",
                source="Pending task state",
                chips=[],
                source_type="local",
            ), task)

        if context_bits.get("artifact") or _looks_like_code_delivery_request(message):
            task.data.update(context_bits)
            original = str(task.data.get("original_text") or "app generation request")
            pieces = [original]
            if task.data.get("platform"):
                pieces.append(f"platform: {task.data['platform']}")
            if task.data.get("app_type"):
                pieces.append(f"app type: {task.data['app_type']}")
            if task.data.get("artifact"):
                pieces.append(f"artifact: {task.data['artifact']}")
            pieces.append(f"latest user detail: {message.strip()}")
            combined = ". ".join(pieces)
            clear_pending_task()
            return _generation_or_setup_response(message=combined, request=request, pending_task=task)

        clear_pending_task()
        style = _language_style(message)
        answer = (
            f"Nice. {message.strip()} basis-e MVP plan: 1) core reminders, 2) medicine schedule, "
            "3) notification flow, 4) local storage, 5) simple dashboard. Next step: features, screens, and database fields finalize kori."
            if style == "mixed"
            else f"Great. Based on '{message.strip()}', start with an MVP plan: core reminders, schedule entry, notifications, local storage, and a simple dashboard. Next, define screens, features, and data fields."
        )
        answer = _compose_reply(answer, request.address_style, style)
        _record_chat_event("app_planning_continue", "completed", message, "Pending app planning details supplied.")
        return ChatMessageResponse(
            status="completed",
            intent="app_planning_continue",
            message=message,
            answer=answer,
            provider="Nexa local assistant",
            source="Pending task state",
            chips=[],
            source_type="local",
        )

    if task.kind == "llm_generation_details":
        normalized_pending_message = normalize_text(message)
        if not _looks_like_generation_detail(normalized_pending_message):
            if _looks_truly_incomplete(normalized_pending_message):
                clear_pending_task()
            return None
        platform = _is_platform_only_detail(message)
        if platform and not _looks_like_code_delivery_request(message):
            task.data["platform"] = platform
            task.data.setdefault("stack", "HTML/CSS/JS" if platform == "web" else "default")
            task.prompt = "Need app type/page details or code confirmation"
            task.status_label = "Waiting for app type/page details"
            set_pending_task(task)
            answer = _compose_reply(
                f"platform {platform} hisebe nilam. Ebar app type/page details bolun, ba code lagle bolun.",
                request.address_style,
                _language_style(message),
            )
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="llm_generation_continue",
                message=message,
                answer=answer,
                provider="Nexa local assistant",
                source="Pending task state",
                chips=[],
                source_type="local",
            ), task)
        context_bits = _extract_app_generation_context(message)
        if context_bits and not _looks_like_code_delivery_request(message):
            task.data.update(context_bits)
            task.data.setdefault("platform", "web")
            task.data.setdefault("stack", "HTML/CSS/JS")
            task.prompt = "Need code confirmation or technology details"
            task.status_label = "Waiting for code confirmation/details"
            set_pending_task(task)
            answer = _compose_reply(
                "context save kore nilam. Code generate korte bolle ami ei context use korbo.",
                request.address_style,
                _language_style(message),
            )
            return _response_with_pending(ChatMessageResponse(
                status="needs_more_info",
                intent="llm_generation_continue",
                message=message,
                answer=answer,
                provider="Nexa local assistant",
                source="Pending task state",
                chips=[],
                source_type="local",
            ), task)
        clear_pending_task()
        original = str(task.data.get("original_text") or "generation request")
        pieces = [original]
        if task.data.get("platform"):
            pieces.append(f"platform: {task.data['platform']}")
        if task.data.get("app_type"):
            pieces.append(f"app type: {task.data['app_type']}")
        if task.data.get("artifact"):
            pieces.append(f"artifact: {task.data['artifact']}")
        if task.data.get("stack"):
            pieces.append(f"stack: {task.data['stack']}")
        pieces.append(f"Details: {message.strip()}")
        combined = ". ".join(pieces)
        return _generation_or_setup_response(message=combined, request=request, pending_task=task)

    if task.kind == "youtube_search_query":
        clear_pending_task()
        return _youtube_skill_response(f"youtube e {message.strip()} search koro", request.address_style)

    if task.kind == "location_permission":
        if not _location_pending_matches(message):
            return None
        clear_pending_task()
        return _location_permission_response(message, request.address_style)

    return None


def _parse_email_request(message: str) -> tuple[str | None, str | None]:
    text = " ".join(message.strip().split())
    patterns = (
        r"(?:email|ইমেইল|ই-মেইল)(?:টা)?\s+(?:to\s+)?(?P<recipient>.+?)\s+(?:লিখে দাও|লিখে দিন|write|draft|send)(?:\s+(?:যে|that))?\s+(?P<brief>.+)",
        r"(?P<recipient>.+?)(?:কে|\s+ke)\s+(?:একটা\s+)?(?:email|ইমেইল|ই-মেইল)(?:টা)?\s+(?:লিখে দাও|লিখে দিন|write|draft|send)(?:\s+(?:যে|that))?\s+(?P<brief>.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            recipient = re.sub(r"^(?:আমার|my)\s+", "", match.group("recipient"), flags=re.IGNORECASE).strip()
            return recipient, match.group("brief").strip()
    return None, None


def _email_skill_response(message: str, address_style: str | None) -> ChatMessageResponse:
    recipient_name, brief = _parse_email_request(message)
    if not recipient_name or not brief:
        return ChatMessageResponse(status="needs_more_info", intent="email_skill", message=message, answer="Please tell me who the email is for and what it should say.", chips=["Email draft"])
    matches = find_contact_matches(recipient_name)
    if not matches and normalize_text(recipient_name) in {"boss", "my boss", "বস", "আমার বস"}:
        matches = [contact for contact in list_contacts() if contact.relationship == "boss"]
    if len(matches) != 1:
        return ChatMessageResponse(status="needs_more_info", intent="email_skill", message=message, answer=f"I could not uniquely find '{recipient_name}'. Save that contact and email address in Settings first.", chips=["Contact needed"])
    contact = matches[0]
    if not contact.email_address:
        return ChatMessageResponse(status="needs_more_info", intent="email_skill", message=message, answer=f"I found {contact.name}, but no email address is saved. Add it in Settings, then try again.", chips=["Email address needed"])
    bangla = bool(re.search(r"[\u0980-\u09ff]", message))
    subject, body = compose_formal_email(brief, contact.name, bangla=bangla)
    task = set_pending_task(email_confirmation_task(recipient=contact.email_address, contact_name=contact.name, subject=subject, body=body))
    answer = f"Email draft for {contact.name}\n\nSubject: {subject}\n\n{body}\n\nMay I send this email? Say Yes to send or Cancel to discard it."
    return _response_with_pending(ChatMessageResponse(status="needs_confirmation", intent="email_skill", message=message, answer=answer, requires_confirmation=True, provider="Nexa formal email composer", source="Local draft; SMTP only after confirmation", chips=["Yes, send", "Cancel"], action=ChatActionStatus(kind="email", target=contact.email_address, label=f"Email {contact.name}", executed=False, requires_confirmation=True, message="Waiting for explicit confirmation.", recipient=contact.email_address, draft_text=body)), task)


def _attach_voice_action_confirmation(
    response: ChatMessageResponse,
    original_text: str,
    source: str | None,
) -> ChatMessageResponse:
    if "voice" not in (source or "").lower():
        return response
    action = response.action
    if not response.requires_confirmation or action is None or action.executed:
        return response
    action_kind = "app" if action.kind == "app" else "website"
    task = set_pending_task(
        action_confirmation_task(
            action_kind=action_kind,
            target=action.target,
            label=action.label,
            original_text=original_text,
        )
    )
    return _response_with_pending(response, task)


def _app_action_response(
    message: str,
    address_style: str | None = None,
    *,
    voice_mode: bool = False,
) -> ChatMessageResponse:
    allowed, meta, reason = get_allowed_app(message)
    if not allowed or meta is None:
        website_allowed, url, website_reason = get_allowed_website_url(message)
        if website_allowed and url is not None:
            language_style = _language_style(message)
            answer = (
                _compose_reply("ওয়েবসাইটটি নিরাপদ তালিকায় আছে। খুলতে বলুন ‘হ্যাঁ করো’।", address_style, language_style)
                if language_style == "bangla"
                else "Ready to open that whitelisted website. Say 'confirm' or use the confirmation button."
            )
            _record_chat_event("app_open_request", "preview_only", message, "Website confirmation required.")
            response = ChatMessageResponse(
                status="preview_only",
                intent="app_open_request",
                message=message,
                answer=answer,
                requires_confirmation=True,
                chips=["Website launch", "Confirmation required", "No auto-open"],
                action=ChatActionStatus(
                    kind="website",
                    target=url,
                    label=message,
                    executed=False,
                    requires_confirmation=True,
                    message=answer,
                ),
            )
            if voice_mode:
                task = set_pending_task(
                    action_confirmation_task(
                        action_kind="website",
                        target=url,
                        label=message,
                        original_text=message,
                    )
                )
                return _response_with_pending(response, task)
            return response
        answer = "I could not find that installed app in the safe whitelist. I did not execute anything."
        _record_chat_event("app_open_request", "blocked", message, website_reason or reason)
        return ChatMessageResponse(
            status="not_found",
            intent="app_open_request",
            message=message,
            answer=answer,
            blocked=False,
            chips=["App launch", "Not found", "No execution"],
            error=answer,
        )

    label = meta["label"]
    command = meta["command"]
    if not is_permission_enabled("trusted_quick_launch"):
        language_style = _language_style(message)
        answer = (
            _compose_reply(
                f"{label} খুলতে আপনার অনুমতি দরকার। Confirm করলে খুলে দেব।",
                address_style,
                language_style,
            )
            if language_style == "bangla"
            else f"Ready to open {label}. Trusted Quick Launch Mode is off, so confirmation is required."
        )
        _record_chat_event("app_open_request", "preview_only", message, f"Confirmation required for {label}.")
        response = ChatMessageResponse(
            status="preview_only",
            intent="app_open_request",
            message=message,
            answer=answer,
            requires_confirmation=True,
            chips=["App launch", "Confirmation required", "Trusted Quick Launch off"],
            action=ChatActionStatus(
                target=normalize_app_key(message),
                label=label,
                executed=False,
                requires_confirmation=True,
                message=answer,
            ),
        )
        if voice_mode:
            task = set_pending_task(
                action_confirmation_task(
                    action_kind="app",
                    target=normalize_app_key(message),
                    label=label,
                    original_text=message,
                )
            )
            return _response_with_pending(response, task)
        return response

    if not is_permission_enabled("actions_app"):
        denied = permission_denied_message("actions_app")
        _record_chat_event("app_open_request", "blocked", message, denied)
        return ChatMessageResponse(
            status="blocked",
            intent="app_open_request",
            message=message,
            answer=denied,
            blocked=True,
            chips=["App launch", "Permission disabled"],
            error=denied,
        )

    request = ActionExecutionRequest(
        intent="open_app",
        target=ActionTarget(kind="app", value=normalize_app_key(message), label=label),
        original_text=message,
        normalized_text=normalize_text(message),
        confidence=100,
        user_confirmed=True,
        dry_run=False,
        source="chat_trusted_quick_launch",
    )
    result = execute_open_app(request)
    status = result.status
    if result.executed:
        if normalize_app_key(message) == "calculator":
            answer = compose_intent(
                "calculator_open_done",
                address_style=address_style,
                language_style=_language_style(message),
                user_message=message,
            )
        else:
            language_style = _language_style(message)
            answer = _compose_reply(
                f"আপনার জন্য {label} খুলে দিয়েছি। আর কিছু করতে পারি?"
                if language_style == "bangla"
                else f"{label} open kore dilam.",
                address_style,
                language_style,
            )
    elif status == "failed":
        answer = (
            "এই কম্পিউটারে অ্যাপটি খুঁজে পাইনি।"
            if _language_style(message) == "bangla"
            else "I could not find that installed app on this system."
        )
    else:
        answer = result.error or result.message
    _record_chat_event("app_open_request", status, message, answer)
    return ChatMessageResponse(
        status=status,
        intent="app_open_request",
        message=message,
        answer=answer,
        blocked=status == "blocked",
        execution_enabled=result.executed,
        auto_execute_safe=status in {"executed", "failed"},
        provider="Trusted Quick Launch" if result.executed else "Safe app whitelist",
        source="Safe app whitelist",
        chips=["App launch"],
        action=ChatActionStatus(
            target=command,
            label=label,
            executed=result.executed,
            requires_confirmation=False,
            message=answer,
        ),
        error=result.error,
    )


def handle_chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    message = request.message.strip()
    route = classify_task(message)
    intent = route.intent
    if intent == "blocked_dangerous":
        language_style = _language_style(message)
        answer = (
            _compose_reply(
                "নিরাপত্তার জন্য এই command ব্লক করেছি। ক্ষতিকর system command আমি execute করব না।",
                request.address_style,
                language_style,
            )
            if language_style == "bangla"
            else "Blocked for safety. Nexa will not execute or assist with destructive system commands."
        )
        _record_chat_event(intent, "blocked", message, answer)
        return _with_route_debug(ChatMessageResponse(
            status="blocked",
            intent=intent,
            message=message,
            answer=answer,
            blocked=True,
            chips=["Blocked", "Dangerous command", "Audit recorded"],
            source_type="tool",
        ), route)

    pending_task = get_pending_task()
    if pending_task is not None and not _should_defer_pending_task(route, pending_task, message):
        pending_response = _handle_pending_task(message, pending_task, request)
        if pending_response is not None:
            return _with_route_debug(pending_response, route)

    pending_whatsapp = _pending_whatsapp_number_response(
        message,
        request.history,
        request.whatsapp_draft_open_target,
        request.address_style,
    )
    if pending_whatsapp is not None:
        return pending_whatsapp

    productivity_response = productivity_chat_response(request)
    if productivity_response is not None:
        _record_chat_event(productivity_response.intent, productivity_response.status, message, productivity_response.answer)
        return _with_route_debug(productivity_response, route)
    style = _language_style(message)

    if intent in {"greeting", "thanks", "capabilities", "user_frustration", "casual_chat", "normal_chat"}:
        return _with_route_debug(conversational_answer(message, intent, request.address_style, request.history), route)

    if intent == "assistant_identity":
        return _with_route_debug(_assistant_identity_response(message, request.address_style), route)

    if intent == "profile_memory":
        return _with_route_debug(_profile_memory_response(message, request.address_style), route)

    if intent == "location_permission":
        return _with_route_debug(_location_permission_response(message, request.address_style), route)

    if intent == "file_summary_request":
        return _with_route_debug(_file_summary_request_response(message, request.address_style), route)

    if intent == "app_planning":
        return _with_route_debug(_app_planning_response(message, request.address_style), route)

    if intent == "general_knowledge":
        return _with_route_debug(_general_knowledge_response(message, request.address_style), route)

    if intent in {"llm_assist", "clarify_or_llm"}:
        llm_response = _llm_answer_response(message, address_style=request.address_style, language_style=style)
        if llm_response:
            llm_response.intent = "llm_assist" if intent == "clarify_or_llm" else intent
            return _with_route_debug(llm_response, route)
        if intent == "llm_assist":
            return _with_route_debug(_llm_setup_answer(message, request.address_style, style, intent="llm_assist"), route)
        if intent == "clarify_or_llm":
            return _with_route_debug(_specific_clarification_response(message, request.address_style), route)
        return _with_route_debug(_llm_setup_answer(message, request.address_style, style, intent="llm_assist"), route)

    if intent == "contact_command":
        return _with_route_debug(_contact_command_response(message, request.address_style), route)

    if intent == "youtube_skill":
        response = _youtube_skill_response(message, request.address_style)
        return _with_route_debug(_attach_voice_action_confirmation(response, message, request.source), route)

    if intent == "whatsapp_skill":
        response = _whatsapp_skill_response(message, request.whatsapp_draft_open_target, request.address_style)
        return _with_route_debug(_attach_voice_action_confirmation(response, message, request.source), route)

    if intent == "email_skill":
        return _with_route_debug(_email_skill_response(message, request.address_style), route)

    if intent == "app_open_request":
        return _with_route_debug(
            _app_action_response(
                message,
                request.address_style,
                voice_mode="voice" in (request.source or "").lower(),
            ),
            route,
        )

    if intent == "local_calculator":
        try:
            answer = _safe_calculator_answer(message)
            if style == "bangla":
                answer = _compose_reply(f"হিসাবের ফল: {answer}", request.address_style, style)
            status = "completed"
            error = None
        except Exception as exc:
            answer = str(exc)
            status = "blocked"
            error = answer
        _record_chat_event(intent, status, message, "Local calculator.")
        return _with_route_debug(ChatMessageResponse(
            status=status,
            intent=intent,
            message=message,
            answer=answer,
            blocked=status == "blocked",
            provider="Local calculator",
            source="Local arithmetic solver",
            chips=["Calculator", "Local solver"],
            source_type="local",
            error=error,
        ), route)

    if intent == "current_time":
        answer, tz_name = current_time_answer(message)
        _record_chat_event(intent, "completed", message, tz_name)
        return _with_route_debug(ChatMessageResponse(
            status="completed",
            intent=intent,
            message=message,
            answer=answer,
            provider="Local timezone database",
            source="Local timezone database",
            chips=["Current time", tz_name, "Local timezone database"],
            source_type="tool",
        ), route)

    if intent == "translation":
        answer, provider = translate_or_explain(message)
        _record_chat_event(intent, "completed", message, provider)
        response = ChatMessageResponse(
            status="completed",
            intent=intent,
            message=message,
            answer=answer,
            provider=provider,
            source=provider,
            chips=["Translation/explanation", provider],
            source_type="local",
        )
        if route.needs_llm:
            llm_response = _llm_answer_response(message, address_style=request.address_style, language_style=style, intent="translation")
            if llm_response:
                return _with_route_debug(llm_response, route)
        return _with_route_debug(response, route)

    if intent == "weather":
        if not is_permission_enabled("web_answers"):
            denied = permission_denied_message("web_answers")
            _record_chat_event(intent, "blocked", message, denied)
            return _with_route_debug(ChatMessageResponse(
                status="blocked",
                intent=intent,
                message=message,
                answer=denied,
                blocked=True,
                provider="Open-Meteo",
                source="Open-Meteo",
                chips=["Backend required", "Permission disabled"],
                error=denied,
                source_type="tool",
            ), route)
        weather = fetch_weather()
        if weather is None:
            answer = (
                _compose_reply("এই মুহূর্তে আবহাওয়ার তথ্য পাওয়া যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।", request.address_style, style)
                if style == "bangla"
                else "Weather is unavailable from Open-Meteo right now. Please try again later."
            )
            _record_chat_event(intent, "no_answer", message, "Open-Meteo unavailable.")
            return _with_route_debug(ChatMessageResponse(
                status="no_answer",
                intent=intent,
                message=message,
                answer=answer,
                provider="Open-Meteo",
                source="Open-Meteo",
                source_url="https://open-meteo.com/",
                chips=["Weather", "Open-Meteo", "Unavailable"],
                error=answer,
                source_type="tool",
            ), route)
        answer = _compose_reply(_weather_answer(weather, style), request.address_style, style)
        _record_chat_event(intent, "completed", message, "Open-Meteo weather answer.")
        return _with_route_debug(ChatMessageResponse(
            status="completed",
            intent=intent,
            message=message,
            answer=answer,
            provider="Open-Meteo",
            source="Open-Meteo",
            source_url="https://open-meteo.com/",
            chips=["Weather", "Dhaka default", "Open-Meteo"],
            weather=weather,
            source_type="tool",
        ), route)

    if intent == "web_search":
        if not is_permission_enabled("web_answers"):
            denied = permission_denied_message("web_answers")
            _record_chat_event(intent, "blocked", message, denied)
            return _with_route_debug(ChatMessageResponse(
                status="blocked",
                intent=intent,
                message=message,
                answer=denied,
                blocked=True,
                chips=["Backend required", "Permission disabled"],
                error=denied,
                source_type="search",
            ), route)
        query = clean_search_query(message)
        query_is_market = is_market_query(query)
        result = search_answer(query)
        if not result.exact and result.results:
            result = synthesize_related_answer(query, result, result.live_data or query_is_market)
        live_data = result.live_data or query_is_market
        answer = result.answer
        llm_result: LLMResponse | None = None
        preserve_market_fallback = live_data and not result.exact and result.confidence == "low"
        if (
            result.results
            and should_use_llm(message, "market_search" if live_data else "web_search") == "use_llm_after_search"
        ):
            context = "\n".join(
                f"- {item.title}: {item.snippet} ({item.source_url or item.provider})"
                for item in result.results[:5]
            )
            llm_result = complete_llm(
                message,
                address_style=request.address_style,
                language_style=style,
                context=context,
            )
            if llm_result and llm_result.answer.strip():
                if not preserve_market_fallback:
                    answer = llm_result.answer
        provider = result.provider
        source_url = result.source_url
        results = to_chat_results(result.results)
        error = result.error
        status = "completed" if error is None else "no_answer"
        _record_chat_event(intent, status, message, provider)
        chips = ["Web search", provider, f"Confidence: {result.confidence}", "No Google scraping"]
        if llm_result:
            chips.append(llm_result.provider)
        if live_data:
            chips.append("Live data may vary")
        sources = []
        for item in results[:4]:
            label = item.title or item.provider
            if label not in sources:
                sources.append(label)
        return _with_route_debug(ChatMessageResponse(
            status=status,
            intent="market_search" if live_data else intent,
            message=message,
            answer=answer,
            provider=provider,
            source=provider,
            source_url=source_url,
            chips=chips if results or error is None else ["Web search", "No reliable result"],
            sources=sources,
            search_results=results,
            show_search_results_by_default=False,
            confidence=result.confidence,
            live_data=live_data,
            live_data_warning=live_data,
            llm_used=bool(llm_result),
            llm_provider=llm_result.provider if llm_result else None,
            fallback_used=llm_result.fallback_used if llm_result else False,
            source_type="hybrid" if llm_result else "search",
            error=error,
        ), route)

    return _with_route_debug(conversational_answer(message, "casual_chat", request.address_style, request.history), route)

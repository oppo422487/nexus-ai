from __future__ import annotations

import pytest

from app.nlu.classifier import NLUClassification, classify
from app.router.task_router import route_task


Case = tuple[str, str, str, float, dict[str, str]]


CASES: list[Case] = [
    ("what is the computer", "general_qa", "llm_or_local_general", 0.8, {"topic": "computer"}),
    ("computer ki", "general_qa", "llm_or_local_general", 0.8, {"topic": "computer"}),
    ("internet ki", "general_qa", "llm_or_local_general", 0.8, {"topic": "internet"}),
    ("AI ki", "general_qa", "llm_or_local_general", 0.8, {"topic": "ai"}),
    ("programming ki", "general_qa", "llm_or_local_general", 0.8, {"topic": "programming"}),
    ("what is programming", "general_qa", "llm_or_local_general", 0.8, {"topic": "programming"}),
    ("what is internet", "general_qa", "llm_or_local_general", 0.8, {"topic": "internet"}),
    ("what is AI", "general_qa", "llm_or_local_general", 0.8, {"topic": "ai"}),
    ("computer er kaj ki", "general_qa", "llm_or_local_general", 0.8, {"topic": "computer"}),
    ("internet mane ki", "translation", "translation_or_llm", 0.85, {}),
    ("tomar nam ki", "identity", "local_persona", 0.9, {}),
    ("tumi ke", "identity", "local_persona", 0.9, {}),
    ("who are you", "identity", "local_persona", 0.9, {}),
    ("what is your name", "identity", "local_persona", 0.9, {}),
    ("apni ke", "identity", "local_persona", 0.9, {}),
    ("amar somporke ki jano", "user_profile", "local_profile_memory", 0.9, {}),
    ("amar profile bolo", "user_profile", "local_profile_memory", 0.9, {}),
    ("what do you know about me", "user_profile", "local_profile_memory", 0.9, {}),
    ("my profile bolo", "user_profile", "local_profile_memory", 0.9, {}),
    ("amar somporke bolo", "user_profile", "local_profile_memory", 0.9, {}),
    ("recent global news ki", "search_current", "search_first", 0.85, {"query": "recent global news ki"}),
    ("latest global news", "search_current", "search_first", 0.85, {"query": "latest global news"}),
    ("today news", "search_current", "search_first", 0.85, {"query": "today news"}),
    ("current news", "search_current", "search_first", 0.85, {"query": "current news"}),
    ("ajker news update", "search_current", "search_first", 0.85, {"query": "ajker news update"}),
    ("python latest version", "search_current", "search_first", 0.85, {"query": "python latest version"}),
    ("latest Python version", "search_current", "search_first", 0.85, {"query": "latest python version"}),
    ("today gold price Bangladesh", "search_current", "search_first", 0.85, {"query": "today gold price bangladesh"}),
    ("current dollar rate", "search_current", "search_first", 0.85, {"query": "current dollar rate"}),
    ("latest update about Bangladesh", "search_current", "search_first", 0.85, {"query": "latest update about bangladesh"}),
    ("bitcoin current price", "search_current", "search_first", 0.85, {"query": "bitcoin current price"}),
    ("gold price today", "search_current", "search_first", 0.85, {"query": "gold price today"}),
    ("Bangladesh news today", "search_current", "search_first", 0.85, {"query": "bangladesh news today"}),
    ("recent AI update", "search_current", "search_first", 0.85, {"query": "recent ai update"}),
    ("current fuel price", "search_current", "search_first", 0.85, {"query": "current fuel price"}),
    ("2+2=?", "calculator", "local_calculator", 0.95, {"expression": "2+2"}),
    ("2 + 2", "calculator", "local_calculator", 0.95, {"expression": "2 + 2"}),
    ("10*5", "calculator", "local_calculator", 0.95, {"expression": "10*5"}),
    ("100/4", "calculator", "local_calculator", 0.95, {"expression": "100/4"}),
    ("12 - 7", "calculator", "local_calculator", 0.95, {"expression": "12 - 7"}),
    ("3.5 + 2.5", "calculator", "local_calculator", 0.95, {"expression": "3.5 + 2.5"}),
    ("calculate 20 percent of 500", "calculator", "local_calculator", 0.95, {"expression": "calculate 20 percent of 500"}),
    ("20% of 500", "calculator", "local_calculator", 0.95, {"expression": "20% of 500"}),
    ("50 percent of 200", "calculator", "local_calculator", 0.95, {"expression": "50 percent of 200"}),
    ("8/2+3", "calculator", "local_calculator", 0.95, {"expression": "8/2+3"}),
    ("ami ekta app banate cai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("ami ekta app banate chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("ami ekta software banate chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("ami ekta project korte chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("app idea dao", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("software banate cai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("project korte chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("amar ekta app idea lagbe", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("mobile app banate chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("web app banate chai", "app_planning", "app_planning", 0.85, {"artifact": "app"}),
    ("ekta login page banabo", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "login page"}),
    ("home page banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "homepage"}),
    ("homepage banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "homepage"}),
    ("landing page banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "landing page"}),
    ("login page banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "login page"}),
    ("code kore dao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("code dao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("html css diye page banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("react component banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "react component"}),
    ("portfolio website banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "portfolio website"}),
    ("website banao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("amar jonno homepage banaw", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "homepage"}),
    ("html css diye dao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("react component banaw", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "react component"}),
    ("login form code dao", "llm_code_generation", "llm_code_generation", 0.85, {"artifact": "code"}),
    ("youtube e bangla gan chalao", "youtube_search", "youtube_search_url", 0.9, {"query": "bangla song"}),
    ("ইউটিউব খুলে একটা বাংলা গান চালাও", "youtube_search", "youtube_search_url", 0.9, {"query": "bangla"}),
    ("youtube open koro", "youtube_open", "youtube_open_url", 0.9, {"target": "youtube"}),
    ("yutub open koro", "youtube_open", "youtube_open_url", 0.9, {"target": "youtube"}),
    ("yt te python tutorial search dao", "youtube_search", "youtube_search_url", 0.9, {"query": "python tutorial"}),
    ("youtube e python tutorial search koro", "youtube_search", "youtube_search_url", 0.9, {"query": "python tutorial"}),
    ("youtube e song search koro", "youtube_search", "youtube_search_url", 0.9, {"query": "song"}),
    ("youtube e video search dao", "youtube_search", "youtube_search_url", 0.9, {"query": "video"}),
    ("open youtube and search calculator tutorial", "youtube_search", "youtube_search_url", 0.9, {"query": "and calculator tutorial"}),
    ("youtube te bangla song search dao", "youtube_search", "youtube_search_url", 0.9, {"query": "bangla song"}),
    ("youtube e music video search dao", "youtube_search", "youtube_search_url", 0.9, {"query": "music video"}),
    ("yt te bangla gan chalao", "youtube_search", "youtube_search_url", 0.9, {"query": "bangla song"}),
    ("ইউটিউব open koro", "youtube_open", "youtube_open_url", 0.9, {"target": "youtube"}),
    ("ইউটিউব ওপেন কর", "youtube_open", "youtube_open_url", 0.9, {"target": "youtube"}),
    ("youtube e excel tutorial search koro", "youtube_search", "youtube_search_url", 0.9, {"query": "excel tutorial"}),
    ("youtube e programming video search dao", "youtube_search", "youtube_search_url", 0.9, {"query": "programming video"}),
    ("whatsapp e Rahim ke bolo ami pore call korbo", "whatsapp_draft", "whatsapp_draft_tool", 0.9, {"recipient": "rahim", "message": "ami pore call korbo"}),
    ("whatsapp e amar boss ke sms dao kalke ami office e aste parbo na", "whatsapp_draft", "whatsapp_draft_tool", 0.9, {"recipient": "amar boss", "message": "kalke ami office e aste parbo na"}),
    ("Rahim ke WhatsApp e likho meeting ta 5tay", "whatsapp_draft", "whatsapp_draft_tool", 0.9, {"recipient": "rahim", "message": "meeting ta 5tay"}),
    ("whatsapp open koro", "whatsapp_open", "whatsapp_open_url", 0.9, {}),
    ("whats app open koro", "whatsapp_open", "whatsapp_open_url", 0.9, {}),
    ("হোয়াটসঅ্যাপ open koro", "whatsapp_open", "whatsapp_open_url", 0.9, {}),
    ("milon k bolo ami kal asbo na", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "milon", "message": "ami kal asbo na"}),
    ("milon ke bolo ami kal asbo na", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "milon", "message": "ami kal asbo na"}),
    ("Amit ke message dao ami busy", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "amit", "message": "ami busy"}),
    ("Karim ke likho meeting cancel", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "karim", "message": "meeting cancel"}),
    ("boss ke sms dao kalke office e aste parbo na", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "boss", "message": "kalke office e aste parbo na"}),
    ("Rahim ke draft hello", "contact_message_intent", "confirm_whatsapp_or_contact_message", 0.8, {"recipient": "rahim", "message": "hello"}),
    ("whatsapp e Rafi ke message dao hi", "whatsapp_draft", "whatsapp_draft_tool", 0.9, {"recipient": "rafi", "message": "hi"}),
    ("whatsapp e Ma ke likho ami aschi", "whatsapp_draft", "whatsapp_draft_tool", 0.9, {"recipient": "ma", "message": "ami aschi"}),
    ("calculator open koro", "app_open_request", "safe_app_launcher", 0.9, {"app": "calculator"}),
    ("ক্যালকুলেটর ওপেন কর", "app_open_request", "safe_app_launcher", 0.9, {"app": "calculator"}),
    ("notepad open koro", "app_open_request", "safe_app_launcher", 0.9, {"app": "notepad"}),
    ("paint open koro", "app_open_request", "safe_app_launcher", 0.9, {"app": "paint"}),
    ("chrome open koro", "app_open_request", "safe_app_launcher", 0.9, {"app": "chrome"}),
    ("file explorer open koro", "app_open_request", "safe_app_launcher", 0.9, {"app": "file explorer"}),
    ("vscode launch", "app_open_request", "safe_app_launcher", 0.9, {"app": "vscode"}),
    ("word start", "app_open_request", "safe_app_launcher", 0.9, {"app": "word"}),
    ("excel khulo", "app_open_request", "safe_app_launcher", 0.9, {"app": "excel"}),
    ("delete system32", "dangerous_block", "blocked", 0.95, {}),
    ("delete all files", "dangerous_block", "blocked", 0.95, {}),
    ("format drive", "dangerous_block", "blocked", 0.95, {}),
    ("format C drive", "dangerous_block", "blocked", 0.95, {}),
    ("run powershell command", "dangerous_block", "blocked", 0.95, {}),
    ("open cmd", "dangerous_block", "blocked", 0.95, {}),
    ("regedit open koro", "dangerous_block", "blocked", 0.95, {}),
    ("rm -rf everything", "dangerous_block", "blocked", 0.95, {}),
    ("shutdown pc now", "dangerous_block", "blocked", 0.95, {}),
    ("hi", "casual_chat", "local_persona", 0.8, {}),
    ("hello", "casual_chat", "local_persona", 0.8, {}),
    ("how are u", "casual_chat", "local_persona", 0.8, {}),
    ("how r u", "casual_chat", "local_persona", 0.8, {}),
    ("hw r u", "casual_chat", "local_persona", 0.8, {}),
    ("ki koro", "casual_chat", "local_persona", 0.8, {}),
    ("ki korteso", "casual_chat", "local_persona", 0.8, {}),
    ("what are you doing", "casual_chat", "local_persona", 0.8, {}),
    ("kemon aso", "casual_chat", "local_persona", 0.8, {}),
    ("kmn aso", "casual_chat", "local_persona", 0.8, {}),
    ("kemon acho", "casual_chat", "local_persona", 0.8, {}),
    ("তুমি কেমন আছো", "casual_chat", "local_persona", 0.8, {}),
    ("ami tension e achi", "casual_chat", "local_persona", 0.8, {}),
    ("my location", "location_permission", "location_permission_prompt", 0.85, {}),
    ("may location", "location_permission", "location_permission_prompt", 0.85, {}),
    ("where am I", "location_permission", "location_permission_prompt", 0.85, {}),
    ("ami ekhon kothai achi", "location_permission", "location_permission_prompt", 0.85, {}),
    ("ajker weather ki", "weather", "weather_api", 0.85, {}),
    ("today weather in Dhaka", "weather", "weather_api", 0.85, {}),
    ("current time in India", "current_time", "time_tool", 0.85, {}),
    ("india te koita baje", "current_time", "time_tool", 0.85, {}),
    ("ei sentence er Bangla ki: I am working", "translation", "translation_or_llm", 0.85, {}),
    ("translate this to Bangla: I am working", "translation", "translation_or_llm", 0.85, {}),
]


def _assert_entities(result: NLUClassification, expected: dict[str, str]) -> None:
    for key, value in expected.items():
        assert key in result.entities
        assert value.lower() in result.entities[key].lower()


def test_nlu_case_inventory_is_deep_enough() -> None:
    assert len(CASES) >= 100


@pytest.mark.parametrize(
    ("prompt", "expected_intent", "expected_route", "min_confidence", "expected_entities"),
    CASES,
)
def test_deep_nlu_routes_real_bangla_banglish_english_prompts(
    prompt: str,
    expected_intent: str,
    expected_route: str,
    min_confidence: float,
    expected_entities: dict[str, str],
) -> None:
    result = classify(prompt)

    assert result.raw_text == prompt
    assert result.normalized_text
    assert result.language_style in {"bangla", "banglish", "english", "mixed"}
    assert result.intent == expected_intent
    assert result.route == expected_route
    assert result.confidence >= min_confidence
    _assert_entities(result, expected_entities)


@pytest.mark.parametrize("prompt, expected_intent, expected_route, _min, _entities", CASES[:20])
def test_task_router_facade_uses_same_nlu_brain(
    prompt: str,
    expected_intent: str,
    expected_route: str,
    _min: float,
    _entities: dict[str, str],
) -> None:
    result = route_task(prompt)
    assert result.intent == expected_intent
    assert result.route == expected_route

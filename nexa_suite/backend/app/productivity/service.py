"""Deterministic local chat skills for personal productivity."""

from __future__ import annotations

import re

from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.productivity.registry import skill_registry
from app.productivity.store import (
    add_calendar_event, add_draft, add_memory, add_note, create_voice_profile,
    list_calendar_events, list_drafts, list_memories, list_notes, list_voice_profiles,
)
from app.reminders.store import parse_natural_reminder
from app.reminders.store import create_reminder, list_reminders
from app.schemas.system_controls import SystemControlRequest
from app.api.routes.system_controls import execute_system_control
from app.files.search import search_files_read_only
from app.schemas.file_search import FileSearchRequest


def _response(request: ChatMessageRequest, intent: str, answer: str, *chips: str) -> ChatMessageResponse:
    return ChatMessageResponse(
        status="completed", intent=intent, message=request.message, answer=answer,
        provider="Nexa local productivity", source="Local encrypted-by-OS storage",
        chips=list(chips) or ["Local skill"], source_type="local",
    )


def _strip_prefix(text: str, patterns: list[str]) -> str:
    value = text.strip()
    for pattern in patterns:
        value = re.sub(pattern, "", value, count=1, flags=re.IGNORECASE).strip(" ,:.-")
    return value


def _screen_answer(source: str) -> str:
    page = (source.split(":", 1)[1] if ":" in source else "dashboard").replace("_", " ")
    descriptions = {
        "dashboard": "Dashboard-এ voice/text command, assistant reply, YouTube, image, system control এবং recent activity আছে।",
        "voice": "Voice page-এ always-listening status, transcript, neural TTS এবং microphone diagnostics আছে।",
        "files": "File Organizer safe folders-এ file খোঁজে এবং supported document preview করে।",
        "settings": "Settings-এ voice, AI providers, permissions এবং personal preferences নিয়ন্ত্রণ করা যায়।",
        "automations": "Automations page-এ reminders, timers এবং recurring tasks দেখা যায়।",
        "skills": "Skills Hub-এ Nexa-র ২০টি capability, local data এবং diagnostics দেখা যায়।",
    }
    return descriptions.get(page, f"আপনি Nexa-এর {page} page-এ আছেন। এখানে page-সংশ্লিষ্ট controls ব্যবহার করতে পারেন।")


def productivity_chat_response(request: ChatMessageRequest) -> ChatMessageResponse | None:
    raw = request.message.strip()
    text = " ".join(raw.lower().split())

    if any(marker in text for marker in ("এই স্ক্রিন", "এই পেজ", "this screen", "this page", "what is on screen")):
        return _response(request, "screen_context", _screen_answer(request.source or "dashboard"), "Screen context", "Local UI")

    if any(marker in text for marker in ("skill list", "সব feature", "সব ফিচার", "capability list", "feature list")):
        ready = skill_registry()
        names = ", ".join(item["name"] for item in ready)
        return _response(request, "skill_registry", f"আমার {len(ready)}টি registered capability ready: {names}।", "20 skills", "Registry")

    remember_match = re.search(r"(?:মনে রাখো(?: যে)?|remember(?: that)?|mone rakho(?: je)?)\s+(.+)", raw, re.IGNORECASE)
    if remember_match:
        fact = remember_match.group(1).strip()
        add_memory(fact)
        return _response(request, "memory_save", f"মনে রেখেছি: {fact}", "Memory", "Saved locally")
    if any(marker in text for marker in ("কি মনে রেখেছ", "আমার কথা কি জানো", "what do you remember", "memory list")):
        items = list_memories(limit=12)
        answer = "এখনও কোনো স্থায়ী তথ্য মনে রাখিনি।" if not items else "আমি মনে রেখেছি: " + "; ".join(item["fact"] for item in items)
        return _response(request, "memory_list", answer, "Memory", f"{len(items)} facts")

    list_kind = None
    listing_request = not any(marker in text for marker in (" add ", "যোগ করো", "যোগ কর", "লিখো"))
    if listing_request and any(marker in text for marker in ("task list", "কাজের তালিকা", "todo list")): list_kind = "task"
    elif listing_request and any(marker in text for marker in ("shopping list", "বাজারের তালিকা")): list_kind = "shopping"
    elif listing_request and any(marker in text for marker in ("note list", "নোট দেখাও", "আমার নোট")): list_kind = "note"
    if list_kind:
        items = list_notes(kind=list_kind, limit=30)
        answer = f"কোনো {list_kind} নেই।" if not items else f"আপনার {list_kind}: " + "; ".join(item["text"] for item in items if item["status"] == "pending")
        return _response(request, f"{list_kind}_list", answer, "Notes & tasks", f"{len(items)} items")

    note_patterns = [
        ("shopping", r"^(?:shopping list(?: এ)?|বাজারের তালিকায়|বাজারের তালিকায়)\s*(?:add|যোগ করো)?\s*"),
        ("task", r"^(?:task|todo|কাজের তালিকায়|কাজের তালিকায়)\s*(?:add|যোগ করো)?\s*"),
        ("note", r"^(?:note|নোট)\s*(?:করো|লিখো|add)?\s*"),
    ]
    for kind, pattern in note_patterns:
        if re.search(pattern, raw, re.IGNORECASE):
            content = _strip_prefix(raw, [pattern])
            if content:
                add_note(content, kind)
                return _response(request, f"{kind}_save", f"{kind.title()}-এ যোগ করেছি: {content}", "Notes & tasks", "Saved locally")

    if any(marker in text for marker in ("reminder list", "reminders দেখাও", "রিমাইন্ডার দেখাও", "alarm list")):
        items = list_reminders(include_done=False, limit=30)
        answer = "কোনো pending reminder নেই।" if not items else "Pending reminders: " + "; ".join(f'{item["title"]} ({item["due_at"] or "সময় দেওয়া নেই"})' for item in items)
        return _response(request, "reminder_list", answer, "Reminders", f"{len(items)} pending")
    if any(marker in text for marker in ("remind me", "set reminder", "set a timer", "timer", "alarm", "মনে করিয়ে", "মনে করিয়ে", "রিমাইন্ডার", "অ্যালার্ম", "টাইমার")):
        parsed = parse_natural_reminder(raw)
        if parsed.get("ok"):
            result = create_reminder(parsed["title"], "", parsed.get("due_at"), parsed.get("recurrence", ""))
            if result.get("ok"):
                item = result["reminder"]
                return _response(request, "reminder_create", f'রিমাইন্ডার তৈরি করেছি: {item["title"]}।', "Reminder", item["due_at"] or "No time specified")

    media_actions = [
        (("volume up", "ভলিউম বাড়াও", "ভলিউম বাড়াও"), "volume_up"),
        (("volume down", "ভলিউম কমাও"), "volume_down"),
        (("mute", "মিউট করো"), "mute"),
        (("play pause", "pause music", "resume music", "গান থামাও", "গান চালাও"), "play_pause"),
        (("next track", "next song", "পরের গান"), "next_track"),
        (("previous track", "previous song", "আগের গান"), "previous_track"),
    ]
    for markers, action in media_actions:
        if any(marker in text for marker in markers) and not any(marker in text for marker in ("youtube", "yutub", "ইউটিউব")):
            result = execute_system_control(SystemControlRequest(action=action, user_confirmed=True))
            return _response(request, "media_control", result.message, "Media control", result.status)

    close_match = re.search(r"(?:close|বন্ধ করো|বন্ধ করে দাও)\s+(notepad|calculator|paint|chrome|vscode|word|excel|spotify|discord|telegram)", text)
    if close_match:
        result = execute_system_control(SystemControlRequest(action="close_app", target=close_match.group(1), user_confirmed=True))
        return _response(request, "app_close", result.message, "Application control", result.status)

    file_match = re.search(r"(?:find|search|খুঁজে দাও|খোঁজো)\s+(?:file\s+)?(.+?)(?:\s+(?:in|থেকে)\s+(desktop|downloads?|documents?))?$", raw, re.IGNORECASE)
    if file_match and any(marker in text for marker in ("file", "ফাইল", "desktop", "download", "document", "খুঁজে", "খোঁজো")):
        query = file_match.group(1).strip()
        scope = (file_match.group(2) or "all_safe").lower().rstrip("s")
        if scope == "download": scope = "downloads"
        result = search_files_read_only(FileSearchRequest(query=query, scope=scope, original_text=query, max_results=10))
        names = ", ".join(item.name for item in result.results[:10])
        answer = f"{result.result_count}টি file পেয়েছি: {names}" if result.result_count else "Safe folders-এ matching file পাইনি।"
        return _response(request, "file_search", answer, "Read-only file search", result.scope)

    if any(marker in text for marker in ("calendar দেখাও", "calendar list", "আমার schedule", "আজকের schedule", "ক্যালেন্ডার দেখাও")):
        items = list_calendar_events(limit=20)
        answer = "Calendar-এ কোনো event নেই।" if not items else "আপনার calendar: " + "; ".join(f'{item["title"]} ({item["start_at"] or "সময় দেওয়া নেই"})' for item in items)
        return _response(request, "calendar_list", answer, "Calendar", f"{len(items)} events")
    if "calendar" in text or "ক্যালেন্ডার" in text:
        content = _strip_prefix(raw, [r"^(?:calendar|ক্যালেন্ডার)(?: এ|ে)?\s*", r"^(?:add|যোগ করো)\s*", r"(?:add|যোগ করো)$"])
        parsed = parse_natural_reminder(content)
        if content and any(marker in text for marker in ("add", "যোগ", "schedule", "event")):
            event = add_calendar_event(parsed.get("title") or content, parsed.get("due_at"))
            return _response(request, "calendar_add", f'Calendar event তৈরি করেছি: {event["title"]}।', "Calendar", "Local event")

    if any(marker in text for marker in ("email draft", "ইমেইল ড্রাফট", "mail draft")):
        recipient_match = re.search(r"(?:to|কে)\s+([^,\s:]+)", raw, re.IGNORECASE)
        recipient = recipient_match.group(1).strip() if recipient_match else "recipient not set"
        body = _strip_prefix(raw, [r"^(?:email|mail|ইমেইল)\s*(?:draft|ড্রাফট)?", r"(?:to|কে)\s+[^,:]+[:,]?\s*"])
        draft = add_draft("email", recipient, body or raw)
        return _response(request, "email_draft", f'Email draft তৈরি হয়েছে—প্রাপক: {draft["recipient"]}। আমি এটি send করিনি।', "Email draft", "Not sent")
    if any(marker in text for marker in ("draft list", "ড্রাফট দেখাও", "email drafts")):
        items = list_drafts(limit=20)
        answer = "কোনো draft নেই।" if not items else "Drafts: " + "; ".join(f'{item["channel"]} → {item["recipient"]}: {item["body"]}' for item in items)
        return _response(request, "draft_list", answer, "Drafts", "Local only")

    profile_match = re.search(r"(?:voice profile|ভয়েস প্রোফাইল|ভয়েস প্রোফাইল)\s*(?:create|বানাও|add)?\s+(.+)", raw, re.IGNORECASE)
    if profile_match:
        name = profile_match.group(1).strip()
        profile = create_voice_profile(name)
        return _response(request, "voice_profile_create", f'Voice profile তৈরি হয়েছে: {profile["name"]}। Wake word: {profile["wake_word"]}।', "Voice profile", "No biometric storage")
    if any(marker in text for marker in ("voice profiles", "ভয়েস প্রোফাইল দেখাও", "ভয়েস প্রোফাইল দেখাও")):
        items = list_voice_profiles()
        answer = "কোনো voice profile নেই।" if not items else "Voice profiles: " + ", ".join(item["name"] for item in items)
        return _response(request, "voice_profile_list", answer, "Voice profiles")

    return None

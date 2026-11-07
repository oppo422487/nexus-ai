"""Nexa's extra tools through the upstream plugin and UI confirmation contracts."""
import json

PLUGIN = {
    "name": "nexa_productivity",
    "description": (
        "Nexa AI extra features: notes, tasks, shopping lists, local calendar, "
        "voice profiles, SMTP email, Markdown/TXT content export, Hugging Face "
        "image generation, image gallery, audit analytics, permissions and diagnostics. "
        "Understand Bengali/Banglish requests. Every write requires a physical HUD "
        "confirmation; never claim success while it is pending. Use original tools "
        "for existing desktop, vision, reminders, browser and voice functionality."
    ),
    "tier": "core",
    "brief": "Nexa notes/tasks/calendar/email/images/content/analytics; writes require HUD confirmation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": [
                "open_panel", "dashboard", "diagnostics", "audit", "analytics", "images",
                "image_status", "email_status", "permissions",
                "note", "task", "shopping", "calendar", "voice_profile",
                "email", "content", "image"
            ]},
            "text": {"type": "STRING", "description": "Note/task text, email body, document content or image prompt."},
            "title": {"type": "STRING", "description": "Document title or email subject."},
            "recipient": {"type": "STRING", "description": "Email recipient address."},
            "start_at": {"type": "STRING", "description": "Calendar ISO timestamp, with timezone when known."},
        },
        "required": ["operation"],
    },
}


def run(parameters, player=None, session_memory=None):
    from core import confirm
    from core import nexa_suite as suite
    try:
        operation = parameters.get("operation", "")
        if operation == "open_panel":
            return suite.open_panel()
        if operation in suite.READ_ROUTES:
            return json.dumps(suite.read(operation), ensure_ascii=False)
        text = str(parameters.get("text", "")).strip()
        title = str(parameters.get("title", "")).strip()
        if not text:
            return "কী লিখতে বা তৈরি করতে হবে তা বলুন। কোনো পরিবর্তন করা হয়নি।"
        if operation in {"note", "task", "shopping", "calendar", "voice_profile"}:
            route = "item"
            payload = {"kind": operation, "text": text, "language": "bn-BD"}
            if operation == "calendar":
                payload["start_at"] = parameters.get("start_at")
        elif operation == "email":
            route = "email"
            payload = {"recipient": str(parameters.get("recipient", "")).strip(), "subject": title, "body": text}
            if not payload["recipient"] or not title:
                return "ইমেইলের প্রাপক ও বিষয় প্রয়োজন। ইমেইল পাঠানো হয়নি।"
        elif operation == "content":
            route = "content"
            payload = {"title": title or "নেক্সা ডকুমেন্ট", "content": text, "format": "md"}
        elif operation == "image":
            route = "image"
            payload = {"prompt": text}
        else:
            return "এই Nexa operation সমর্থিত নয়।"
        # Freeze the reviewed payload; no model-supplied confirmation flag exists.
        reviewed = json.loads(json.dumps(payload))
        detail = json.dumps(reviewed, ensure_ascii=False, indent=2)
        return confirm.request(
            "nexa_" + operation,
            "নেক্সা আই — " + operation,
            detail,
            lambda: json.dumps(suite.write(route, reviewed), ensure_ascii=False),
        )
    except Exception as exc:
        return f"নেক্সা টুলটি কাজ শেষ করতে পারেনি: {exc}"

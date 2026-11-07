"""Permission center storage for Nexa AI.

Permissions are stored in a local JSON file. Dangerous capabilities are
hard-locked and can never be enabled through the API.
"""

from __future__ import annotations

import json
import threading
from app.core.runtime_paths import data_dir

PERMISSIONS_FILE = data_dir() / "permissions.json"

_lock = threading.Lock()

TOGGLEABLE_PERMISSIONS: dict[str, dict] = {
    "actions_website": {
        "default": True,
        "label": "Safe Website Opening",
        "description": "Open whitelisted websites after explicit confirmation.",
    },
    "actions_app": {
        "default": True,
        "label": "Safe App Opening",
        "description": "Open whitelisted desktop apps after explicit confirmation.",
    },
    "trusted_quick_launch": {
        "default": False,
        "label": "Trusted Quick Launch Mode",
        "description": (
            "Open recognized safe installed apps without asking every time. "
            "Dangerous/system commands remain blocked."
        ),
    },
    "file_search": {
        "default": True,
        "label": "Read-only File Search",
        "description": "Search file names in Desktop, Downloads, and Documents. Metadata only.",
    },
    "voice_stt": {
        "default": True,
        "label": "Voice Transcription",
        "description": "Transcribe Bangla/English speech through the online Web Speech service.",
    },
    "always_on_microphone": {
        "default": True,
        "label": "Always-listening Microphone",
        "description": (
            "Keep the microphone active while Nexa is open. Silence is discarded locally; "
            "only detected utterances are sent to online STT. The user can turn it off anytime."
        ),
    },
    "voice_tts": {
        "default": True,
        "label": "Voice Reply (TTS)",
        "description": "Speak assistant replies with online Edge neural voices.",
    },
    "web_answers": {
        "default": True,
        "label": "Web Answers",
        "description": "Answer questions using DuckDuckGo/Wikipedia public APIs only.",
    },
    "youtube_skill": {
        "default": True,
        "label": "YouTube Skill Enabled",
        "description": "Open YouTube and YouTube search pages through safe whitelisted URLs.",
    },
    "youtube_control": {
        "default": True,
        "label": "Advanced YouTube Controls",
        "description": (
            "Control playback in a dedicated Chrome window. Every command comes "
            "from an explicit chat confirmation or control-panel click."
        ),
    },
    "trusted_youtube_auto_open": {
        "default": True,
        "label": "Trusted YouTube Auto Open",
        "description": "Open safe YouTube home/search URLs without an extra confirmation card.",
    },
    "whatsapp_draft_skill": {
        "default": True,
        "label": "WhatsApp Draft Skill Enabled",
        "description": "Create WhatsApp message drafts only after explicit confirmation. Auto-send stays locked off.",
    },
    "trusted_whatsapp_draft_auto_open": {
        "default": True,
        "label": "Trusted WhatsApp Draft Auto Open",
        "description": "Open WhatsApp Web/draft URLs without confirmation. Nexa never clicks Send.",
    },
    "documents": {
        "default": True,
        "label": "Document Preview (Read-only)",
        "description": "Read-only text preview of PDF/TXT/MD files in safe folders.",
    },
    "reminders": {
        "default": True,
        "label": "Reminders",
        "description": "Local reminder records. Created only after confirmation.",
    },
    "image_generation": {
        "default": False,
        "label": "AI Image Generation",
        "description": (
            "Send a confirmed prompt to the configured Hugging Face image provider "
            "and save the result only in Nexa's generated-images folder."
        ),
    },
    "system_media_controls": {
        "default": True,
        "label": "System Media & App Controls",
        "description": (
            "Use Windows volume keys or close one explicitly whitelisted app after confirmation. "
            "Shells, arbitrary processes, force-close, shutdown, and restart stay blocked."
        ),
    },
    "content_export": {
        "default": False,
        "label": "Content Writer Export",
        "description": "Save confirmed TXT/Markdown documents only inside Nexa's generated-content folder.",
    },
    "edge_tts": {
        "default": True,
        "label": "Online Edge TTS",
        "description": "Use Microsoft Edge online neural voices, including Bangla voices.",
    },
}

# These can never be enabled. They exist so the security center can show
# the user exactly what Nexa AI refuses to do.
LOCKED_PERMISSIONS: dict[str, dict] = {
    "file_write_operations": {
        "label": "File Delete/Move/Rename/Edit",
        "description": "Nexa AI never deletes, moves, renames, or edits user files.",
    },
    "auto_send_messaging": {
        "label": "Auto-send WhatsApp/Email",
        "description": "Messages are never sent automatically. Locked off.",
    },
    "shell_command_execution": {
        "label": "Shell Command Execution",
        "description": "cmd/powershell/registry access is permanently blocked.",
    },
    "arbitrary_app_execution": {
        "label": "Unknown App/Website Execution",
        "description": "Only whitelisted apps and websites can ever open.",
    },
}


def _read_file() -> dict:
    try:
        if PERMISSIONS_FILE.exists():
            raw = json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
    except Exception:
        pass
    return {}


def load_permissions() -> dict[str, bool]:
    """Return the effective toggleable permission map (defaults merged)."""
    stored = _read_file()
    result: dict[str, bool] = {}
    for key, meta in TOGGLEABLE_PERMISSIONS.items():
        value = stored.get(key)
        result[key] = bool(value) if isinstance(value, bool) else bool(meta["default"])
    return result


def is_permission_enabled(key: str) -> bool:
    if key in LOCKED_PERMISSIONS:
        return False
    return load_permissions().get(key, False)


def set_permission(key: str, enabled: bool) -> tuple[bool, str]:
    """Update one toggleable permission. Locked permissions are rejected."""
    if key in LOCKED_PERMISSIONS:
        return False, "This capability is locked off by safety policy and cannot be enabled."
    if key not in TOGGLEABLE_PERMISSIONS:
        return False, "Unknown permission key."
    with _lock:
        current = load_permissions()
        current[key] = bool(enabled)
        PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PERMISSIONS_FILE.write_text(
            json.dumps(current, indent=2), encoding="utf-8"
        )
    return True, "Permission updated."


def permission_denied_message(key: str) -> str:
    meta = TOGGLEABLE_PERMISSIONS.get(key)
    label = meta["label"] if meta else key
    return f"{label} is disabled in the Security Center. Enable it to use this feature."

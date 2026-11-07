"""Built-in Nexa skill registry exposed to diagnostics and the UI."""

SKILLS = [
    ("wake_word", "Wake Word", "ready", "Say Nexa/নেক্সা; follow-up window stays active."),
    ("conversation_memory", "Conversation Memory", "ready", "Short-term context plus persistent user facts."),
    ("multilingual_nlu", "Bangla/Banglish/English NLU", "ready", "Mixed-language commands use the unified router."),
    ("follow_up_voice", "Follow-up Voice", "ready", "Voice resumes after each neural reply."),
    ("application_control", "Application Control", "ready", "Allowlisted apps and safe Windows media controls."),
    ("advanced_youtube", "YouTube Skill", "ready", "Bangla/Banglish/English search, play, seek, volume, captions, speed, timers and more."),
    ("media_control", "Music & Media", "ready", "YouTube plus safe system media commands."),
    ("reminders", "Reminders, Alarms & Timers", "ready", "Local recurring reminders and due alerts."),
    ("calendar", "Calendar", "ready", "Local calendar works now; cloud sync is optional."),
    ("email", "Email Send", "ready", "Preview and explicitly confirm delivery through configured Gmail, Outlook or SMTP."),
    ("whatsapp", "WhatsApp Assistant", "ready", "Confirmed drafts; auto-send remains blocked."),
    ("files", "File Assistant", "ready", "Safe-folder search and document/PDF preview."),
    ("screen_context", "Screen Understanding", "ready", "Answers about the active Nexa page supplied by the UI."),
    ("live_information", "News & Live Information", "ready", "Weather and safe web/search providers."),
    ("translation_dictation", "Translation & Dictation", "ready", "Bangla/English translation and STT notes."),
    ("notes_tasks", "Notes & Tasks", "ready", "Persistent notes, tasks and shopping items."),
    ("voice_profiles", "Voice Profiles", "ready", "Named preferences; biometric voiceprints are not stored."),
    ("offline_fallback", "Offline Fallback", "ready", "Calculator, time, memory, notes and safe local tools."),
    ("skill_registry", "Plugin/Skill Registry", "ready", "Discoverable built-in capability catalog."),
    ("diagnostics", "Diagnostics", "ready", "Backend, permissions, STT/TTS and dependency status."),
]


def skill_registry() -> list[dict[str, str]]:
    return [{"id": key, "name": name, "status": status, "description": description} for key, name, status, description in SKILLS]

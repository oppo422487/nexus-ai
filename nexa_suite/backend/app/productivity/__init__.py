"""Local productivity capabilities used by voice and typed chat."""

from .service import productivity_chat_response
from .store import (
    add_calendar_event,
    add_draft,
    add_memory,
    add_note,
    create_voice_profile,
    dashboard_snapshot,
    list_calendar_events,
    list_drafts,
    list_memories,
    list_notes,
    list_voice_profiles,
    set_note_status,
)

__all__ = [
    "productivity_chat_response", "add_calendar_event", "add_draft", "add_memory",
    "add_note", "create_voice_profile", "dashboard_snapshot", "list_calendar_events",
    "list_drafts", "list_memories", "list_notes", "list_voice_profiles", "set_note_status",
]

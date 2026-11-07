"""Unified APIs for Nexa's personal productivity and diagnostics features."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.permissions import load_permissions
from app.productivity.registry import skill_registry
from app.productivity.store import (
    add_calendar_event, add_draft, add_memory, add_note, create_voice_profile,
    dashboard_snapshot, set_note_status,
)
from app.voice.stt_engines import get_stt_engines_overview
from app.voice.cartesia import status as cartesia_status

router = APIRouter(prefix="/productivity", tags=["productivity"])


class LocalItemRequest(BaseModel):
    kind: str = Field(default="note", max_length=40)
    text: str = Field(..., min_length=1, max_length=3000)
    recipient: str = Field(default="", max_length=300)
    subject: str = Field(default="", max_length=300)
    start_at: str | None = Field(default=None, max_length=80)
    wake_word: str = Field(default="Nexa", max_length=80)
    language: str = Field(default="bn-BD", max_length=20)
    user_confirmed: bool = False


@router.get("/dashboard")
def productivity_dashboard() -> dict:
    return {"status": "ok", "skills": skill_registry(), **dashboard_snapshot()}


@router.get("/diagnostics")
def productivity_diagnostics() -> dict:
    permissions = load_permissions()
    stt = get_stt_engines_overview()
    return {
        "status": "ok",
        "backend": "connected",
        "stt": stt,
        "permissions": {
            key: permissions.get(key, False)
            for key in ("always_on_microphone", "voice_stt", "voice_tts", "edge_tts", "web_answers", "reminders")
        },
        "checks": [
            {"name": "Online Bangla STT", "ok": bool(stt["engines"][0]["ready"] and permissions.get("voice_stt"))},
            {"name": "Always-listening", "ok": bool(permissions.get("always_on_microphone"))},
            {"name": "Voice replies", "ok": bool(permissions.get("voice_tts") and (cartesia_status()["configured"] or permissions.get("edge_tts")))},
            {"name": "Offline local skills", "ok": True},
        ],
    }


@router.post("/items")
def create_productivity_item(request: LocalItemRequest) -> dict:
    if not request.user_confirmed:
        return {"status": "confirmation_required", "created": False, "message": "Creating a local item requires confirmation."}
    kind = request.kind.strip().lower()
    if kind in {"note", "task", "shopping"}:
        item = add_note(request.text, kind)
    elif kind == "memory":
        item = add_memory(request.text)
    elif kind == "calendar":
        item = add_calendar_event(request.text, request.start_at)
    elif kind in {"email", "draft"}:
        item = add_draft("email", request.recipient, request.text, request.subject)
    elif kind == "voice_profile":
        item = create_voice_profile(request.text, request.wake_word, request.language)
    else:
        return {"status": "blocked", "created": False, "message": "Unsupported productivity item kind."}
    return {"status": "completed", "created": True, "item": item, "message": f"{kind} created locally."}


@router.post("/notes/{note_id}/status")
def update_productivity_note(note_id: str, status: str = "done") -> dict:
    updated = set_note_status(note_id, status)
    return {"status": "completed" if updated else "not_found", "updated": updated}

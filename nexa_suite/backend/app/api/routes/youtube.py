"""Advanced, audited YouTube controller API."""

from __future__ import annotations

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.youtube import (
    YouTubeCapabilitiesResponse,
    YouTubeCommandRequest,
    YouTubeCommandResponse,
    YouTubePlayerState,
)
from app.youtube import YouTubeControllerError, get_youtube_controller, parse_youtube_command
from app.youtube.controller import ParsedYouTubeCommand

router = APIRouter(prefix="/youtube", tags=["youtube"])

_ACTIONS = [
    "launch", "search", "play", "pause", "resume", "toggle_play", "skip",
    "set_volume", "mute", "unmute", "fullscreen", "captions", "theater", "ambient",
    "autoplay", "set_speed", "sleep_timer", "cancel_timer", "next", "previous",
    "status", "close", "duck", "restore",
]


def _response(status: str, action: str, message: str, *, executed: bool = False, error: str | None = None) -> YouTubeCommandResponse:
    controller = get_youtube_controller()
    return YouTubeCommandResponse(
        status=status,
        action=action,
        executed=executed,
        message=message,
        error=error,
        state=YouTubePlayerState(**controller.state()),
    )


@router.get("/capabilities", response_model=YouTubeCapabilitiesResponse)
def youtube_capabilities() -> YouTubeCapabilitiesResponse:
    controller = get_youtube_controller()
    enabled = is_permission_enabled("youtube_skill") and is_permission_enabled("youtube_control")
    return YouTubeCapabilitiesResponse(
        available=controller.available,
        enabled=enabled,
        actions=_ACTIONS,
        message=(
            "Advanced YouTube control is ready."
            if controller.available and enabled
            else "Install selenium and enable YouTube permissions to use advanced controls."
        ),
    )


@router.get("/status", response_model=YouTubeCommandResponse)
def youtube_status() -> YouTubeCommandResponse:
    controller = get_youtube_controller()
    return YouTubeCommandResponse(
        status="ok",
        action="status",
        executed=False,
        message=controller.execute(ParsedYouTubeCommand("status")),
        state=YouTubePlayerState(**controller.state()),
    )


@router.post("/command", response_model=YouTubeCommandResponse)
def youtube_command(request: YouTubeCommandRequest) -> YouTubeCommandResponse:
    if not is_permission_enabled("youtube_skill") or not is_permission_enabled("youtube_control"):
        message = permission_denied_message(
            "youtube_control" if is_permission_enabled("youtube_skill") else "youtube_skill"
        )
        record_audit_event("youtube", "youtube_control", "blocked", "permission", request.command or request.action, message)
        return _response("blocked", request.action, message, error=message)

    parsed = parse_youtube_command(request.command) if request.action == "auto" else ParsedYouTubeCommand(
        action=request.action,
        query=request.query,
        value=request.value,
        enabled=request.enabled,
    )
    if parsed.action != "status" and not request.user_confirmed:
        message = "YouTube player commands require an explicit user confirmation or control-panel click."
        return YouTubeCommandResponse(
            status="confirmation_required",
            action=parsed.action,
            executed=False,
            requires_confirmation=True,
            message=message,
            state=YouTubePlayerState(**get_youtube_controller().state()),
            error=message,
        )

    try:
        message = get_youtube_controller().execute(parsed)
        record_audit_event("youtube", f"youtube_{parsed.action}", "executed", "controlled", parsed.query or str(parsed.value or ""), message)
        return _response("executed", parsed.action, message, executed=parsed.action != "status")
    except YouTubeControllerError as exc:
        message = str(exc)
        record_audit_event("youtube", f"youtube_{parsed.action}", "failed", "controlled", parsed.query or "", message)
        return _response("failed", parsed.action, message, error=message)

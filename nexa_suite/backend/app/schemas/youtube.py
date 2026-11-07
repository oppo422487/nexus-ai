"""Schemas for the permission-gated YouTube player controller."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


YouTubeAction = Literal[
    "auto",
    "launch",
    "search",
    "play",
    "pause",
    "resume",
    "toggle_play",
    "skip",
    "set_volume",
    "mute",
    "unmute",
    "fullscreen",
    "captions",
    "theater",
    "ambient",
    "autoplay",
    "set_speed",
    "sleep_timer",
    "cancel_timer",
    "next",
    "previous",
    "status",
    "close",
    "duck",
    "restore",
]


class YouTubeCommandRequest(BaseModel):
    action: YouTubeAction = "auto"
    command: str = Field(default="", max_length=300)
    query: str | None = Field(default=None, max_length=200)
    value: float | None = None
    enabled: bool | None = None
    user_confirmed: bool = False
    source: str = Field(default="youtube_panel", max_length=64)


class YouTubePlayerState(BaseModel):
    available: bool = False
    launched: bool = False
    playing: bool = False
    muted: bool = False
    title: str = ""
    current_time: float = 0
    duration: float = 0
    volume: int = 100
    playback_rate: float = 1
    timer_remaining_seconds: int | None = None
    current_url: str = ""


class YouTubeCommandResponse(BaseModel):
    status: str
    module: str = "youtube_controller"
    action: str
    executed: bool = False
    requires_confirmation: bool = False
    message: str
    state: YouTubePlayerState | None = None
    error: str | None = None


class YouTubeCapabilitiesResponse(BaseModel):
    status: str = "ok"
    module: str = "youtube_controller"
    available: bool = False
    enabled: bool = False
    actions: list[str] = []
    message: str = ""

"""Schemas for whitelisted Windows media/app controls."""

from typing import Literal

from pydantic import BaseModel, Field


class SystemControlRequest(BaseModel):
    action: Literal["volume_up", "volume_down", "mute", "play_pause", "next_track", "previous_track", "close_app"]
    target: str | None = Field(default=None, max_length=80)
    user_confirmed: bool = False


class SystemControlResponse(BaseModel):
    status: str
    module: str = "system_controls"
    action: str
    executed: bool = False
    message: str
    error: str | None = None

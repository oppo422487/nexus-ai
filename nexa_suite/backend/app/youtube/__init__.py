"""Advanced YouTube playback integration."""

from .controller import (
    YouTubeController,
    YouTubeControllerError,
    get_youtube_controller,
    parse_youtube_command,
    selenium_available,
)

__all__ = [
    "YouTubeController",
    "YouTubeControllerError",
    "get_youtube_controller",
    "parse_youtube_command",
    "selenium_available",
]

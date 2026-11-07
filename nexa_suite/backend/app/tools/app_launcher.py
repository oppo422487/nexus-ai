"""Safe app launcher facade."""

from __future__ import annotations

from app.actions import execute_open_app, get_allowed_app, normalize_app_key

__all__ = ["execute_open_app", "get_allowed_app", "normalize_app_key"]


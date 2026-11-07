"""Shared error and response helpers for the Nexa AI backend."""

from typing import Any


class NexaAIError(Exception):
    """Application error that can be returned safely to API clients."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a standard backend error payload."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def success_response(
    data: Any = None,
    message: str = "OK",
) -> dict[str, Any]:
    """Return a standard backend success payload."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }

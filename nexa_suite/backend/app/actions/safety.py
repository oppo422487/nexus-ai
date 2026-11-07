"""Safety classification helpers for action execution."""

from __future__ import annotations

from app.schemas import ActionExecutionRequest
from app.schemas.action_execution import ActionIntent
from app.schemas.action_execution import ActionSafetyLevel

SAFE_INTENTS: set[str] = {
    "file_search",
}

CONFIRMATION_REQUIRED_INTENTS: set[str] = {
    "open_website",
    "open_app",
}

BLOCKED_INTENTS: set[str] = {
    "blocked",
}

DANGEROUS_KEYWORDS: list[str] = [
    "delete",
    "remove",
    "wipe",
    "format",
    "shutdown",
    "restart",
    "power off",
    "system32",
    "registry",
    "permanently delete",
    "ডিলিট",
    "মুছে ফেল",
    "ফরম্যাট",
    "শাটডাউন",
    "রিস্টার্ট",
]


def normalize_safety_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def contains_dangerous_keyword(text: str) -> bool:
    normalized = normalize_safety_text(text)
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def classify_action_safety(
    request: ActionExecutionRequest,
) -> tuple[ActionSafetyLevel, str]:
    parts = [
        request.original_text,
        request.normalized_text or "",
        request.intent,
        request.target.value if request.target else "",
    ]
    combined = " ".join(p for p in parts if p)

    if contains_dangerous_keyword(combined):
        return ("blocked", "Action contains dangerous or destructive keywords.")

    if request.intent == "blocked":
        return ("blocked", "Action intent is blocked.")

    if request.intent in SAFE_INTENTS:
        return ("safe", "Action is read-only or preview-safe.")

    if request.intent in CONFIRMATION_REQUIRED_INTENTS:
        return (
            "confirmation_required",
            "Action requires explicit user confirmation before execution.",
        )

    return ("blocked", "Unknown action intent is blocked by default.")


def is_action_allowed_after_confirmation(
    request: ActionExecutionRequest,
) -> bool:
    level, _ = classify_action_safety(request)
    if level in ("safe", "confirmation_required"):
        return request.user_confirmed and not request.dry_run
    return False


def build_safety_preview_steps(level: ActionSafetyLevel) -> list[str]:
    if level == "blocked":
        return [
            "Detect action safety level.",
            "Block unsafe or unknown action.",
            "Do not execute anything.",
        ]
    if level == "confirmation_required":
        return [
            "Detect action safety level.",
            "Require explicit user confirmation.",
            "Keep execution disabled until executor phase.",
        ]
    return [
        "Detect action safety level.",
        "Confirm action is read-only or low risk.",
        "Keep execution controlled by executor phase.",
    ]

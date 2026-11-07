"""Command preview request/response schemas for the Nexa AI backend."""

from pydantic import BaseModel


class CommandPreviewRequest(BaseModel):
    """Incoming command preview request from the frontend."""

    original_text: str
    normalized_text: str | None = None
    intent: str = "unknown"
    language: str = "Unknown"
    confidence: int = 0
    risk_level: str = "safe"
    entities: dict[str, str] = {}
    confirmation_reason: str | None = None


class CommandPreviewResponse(BaseModel):
    """Safe preview-only response for a command understanding result."""

    status: str
    can_execute: bool
    execution_mode: str
    message: str
    intent: str
    risk_level: str
    preview_steps: list[str]
    warning: str | None = None
    blocked_reason: str | None = None


class CommandRouteHealth(BaseModel):
    """Health status for the command route module."""

    status: str
    module: str
    phase: str
    execution_enabled: bool


def create_preview_response(
    request: CommandPreviewRequest,
) -> CommandPreviewResponse:
    """Build a preview-only response from a command preview request.

    This function never produces a response that allows real execution.
    All responses mark can_execute as False and execution_mode as 'preview_only'.
    """
    if request.risk_level == "blocked":
        status = "blocked"
    elif request.risk_level == "sensitive":
        status = "warning"
    elif request.risk_level == "confirmation_required":
        status = "confirmation_required"
    else:
        status = "preview"

    preview_steps = [
        "Receive command understanding result.",
        "Validate intent and risk level.",
        "Return preview-only response.",
        "Do not execute OS, file, browser, email, message, or smart home actions.",
    ]

    warning: str | None = None
    blocked_reason: str | None = None

    if request.risk_level == "blocked":
        blocked_reason = (
            request.confirmation_reason
            or "This command is blocked due to safety policy."
        )
    elif request.risk_level == "sensitive":
        warning = (
            request.confirmation_reason
            or "This action may affect files, devices, messages, or external apps."
        )

    message = (
        "Command execution is not enabled. "
        "This is a preview-only response. "
        "No real OS, file, browser, email, message, or smart home action was executed."
    )

    return CommandPreviewResponse(
        status=status,
        can_execute=False,
        execution_mode="preview_only",
        message=message,
        intent=request.intent,
        risk_level=request.risk_level,
        preview_steps=preview_steps,
        warning=warning,
        blocked_reason=blocked_reason,
    )

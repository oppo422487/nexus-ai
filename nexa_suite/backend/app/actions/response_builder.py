"""Response builder helpers for safe action execution."""

from __future__ import annotations

from app.schemas import ActionExecutionRequest
from app.schemas import ActionExecutionResponse
from app.schemas import create_execution_preview_response
from app.schemas import create_confirmation_required_response
from app.schemas import create_execution_blocked_response
from app.actions.safety import classify_action_safety
from app.actions.safety import build_safety_preview_steps


def build_action_preview_response(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    level, reason = classify_action_safety(request)

    if level == "blocked":
        response = create_execution_blocked_response(request, reason)
        response.preview_steps = build_safety_preview_steps("blocked")
        return response

    if level == "sensitive":
        response = ActionExecutionResponse(
            status="pending_confirmation",
            intent=request.intent,
            target=request.target,
            safety_level="sensitive",
            can_execute=False,
            executed=False,
            dry_run=True,
            user_confirmed=request.user_confirmed,
            message="Sensitive action requires explicit confirmation and remains disabled in this phase.",
            preview_steps=build_safety_preview_steps("confirmation_required"),
        )
        return response

    if level == "confirmation_required":
        response = create_confirmation_required_response(request)
        response.preview_steps = build_safety_preview_steps("confirmation_required")
        return response

    response = create_execution_preview_response(
        request,
        "Safe action preview generated. Execution remains disabled in this phase.",
    )
    response.safety_level = "safe"
    response.preview_steps = build_safety_preview_steps("safe")
    return response


def build_dry_run_response(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    level, reason = classify_action_safety(request)

    if level == "blocked":
        response = create_execution_blocked_response(request, reason)
        response.preview_steps = build_safety_preview_steps("blocked")
        return response

    response = create_execution_preview_response(
        request,
        "Dry run completed. No action was executed.",
    )
    response.preview_steps = build_safety_preview_steps(level)
    return response


def build_unconfirmed_response(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    if not request.user_confirmed:
        return create_confirmation_required_response(request)

    return build_dry_run_response(request)

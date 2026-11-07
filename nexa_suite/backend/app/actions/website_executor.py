"""Safe backend website executor for open_website action."""

from __future__ import annotations

import webbrowser

from app.schemas import ActionExecutionRequest
from app.schemas import ActionExecutionResponse
from app.schemas import ActionTarget
from app.schemas import create_execution_blocked_response
from app.schemas import create_confirmation_required_response
from app.schemas import create_execution_preview_response
from app.actions.website import get_allowed_website_url
from app.actions.safety import classify_action_safety


def execute_open_website(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    if request.intent != "open_website":
        return create_execution_blocked_response(
            request,
            "Only open_website intent is supported by this executor.",
        )

    target_text = (
        request.target.value if request.target else request.original_text
    )

    allowed, url, reason = get_allowed_website_url(target_text)
    if not allowed:
        return create_execution_blocked_response(request, reason)

    safety_level, _ = classify_action_safety(request)
    if safety_level == "blocked":
        return create_execution_blocked_response(
            request,
            "Action safety classification blocked this request.",
        )

    if not request.user_confirmed:
        return create_confirmation_required_response(request)

    if request.dry_run:
        response = create_execution_preview_response(
            request,
            "Website action is valid, but dry_run is enabled. No browser was opened.",
        )
        response.safety_level = "confirmation_required"
        return response

    try:
        opened = webbrowser.open(url)
    except Exception as exc:
        return ActionExecutionResponse(
            status="failed",
            intent="open_website",
            target=ActionTarget(kind="url", value=url, label=target_text),
            safety_level="confirmation_required",
            can_execute=True,
            executed=False,
            dry_run=False,
            user_confirmed=True,
            message="Browser could not open the website.",
            error=str(exc),
        )

    if opened:
        return ActionExecutionResponse(
            status="executed",
            intent="open_website",
            target=ActionTarget(kind="url", value=url, label=target_text),
            safety_level="confirmation_required",
            can_execute=True,
            executed=True,
            dry_run=False,
            user_confirmed=True,
            message="Opened website safely.",
        )

    return ActionExecutionResponse(
        status="failed",
        intent="open_website",
        target=ActionTarget(kind="url", value=url, label=target_text),
        safety_level="confirmation_required",
        can_execute=True,
        executed=False,
        dry_run=False,
        user_confirmed=True,
        message="Browser could not open the website.",
        error="webbrowser.open returned False.",
    )

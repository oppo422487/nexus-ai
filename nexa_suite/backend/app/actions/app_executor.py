"""Safe backend app executor for open_app action."""

from __future__ import annotations

import subprocess

from app.schemas import ActionExecutionRequest
from app.schemas import ActionExecutionResponse
from app.schemas import ActionTarget
from app.schemas import create_execution_blocked_response
from app.schemas import create_confirmation_required_response
from app.schemas import create_execution_preview_response
from app.actions.app_whitelist import get_allowed_app
from app.actions.safety import classify_action_safety


def execute_open_app(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    if request.intent != "open_app":
        return create_execution_blocked_response(
            request,
            "Only open_app intent is supported by this executor.",
        )

    target_text = (
        request.target.value if request.target else request.original_text
    )

    allowed, meta, reason = get_allowed_app(target_text)
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
            "App action is valid, but dry_run is enabled. No app was opened.",
        )
        response.safety_level = "confirmation_required"
        return response

    command = meta["command"]
    label = meta["label"]

    if command in ("cmd", "powershell"):
        return ActionExecutionResponse(
            status="blocked",
            intent="open_app",
            target=ActionTarget(kind="app", value=command, label=label),
            safety_level="blocked",
            can_execute=False,
            executed=False,
            dry_run=False,
            user_confirmed=True,
            message="Blocked system shell is not allowed.",
            error="System shell blocked by app whitelist.",
        )

    try:
        subprocess.Popen([command], shell=False)
    except FileNotFoundError:
        return ActionExecutionResponse(
            status="failed",
            intent="open_app",
            target=ActionTarget(kind="app", value=command, label=label),
            safety_level="confirmation_required",
            can_execute=False,
            executed=False,
            dry_run=False,
            user_confirmed=True,
            message="Whitelisted app command was not found on this system.",
            error="Whitelisted app command was not found on this system.",
        )
    except Exception as exc:
        return ActionExecutionResponse(
            status="failed",
            intent="open_app",
            target=ActionTarget(kind="app", value=command, label=label),
            safety_level="confirmation_required",
            can_execute=False,
            executed=False,
            dry_run=False,
            user_confirmed=True,
            message="App could not be opened safely.",
            error=str(exc),
        )

    return ActionExecutionResponse(
        status="executed",
        intent="open_app",
        target=ActionTarget(kind="app", value=command, label=label),
        safety_level="confirmation_required",
        can_execute=True,
        executed=True,
        dry_run=False,
        user_confirmed=True,
        message="Opened app safely.",
    )

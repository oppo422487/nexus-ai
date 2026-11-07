"""Pydantic schemas for safe action execution preview."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ActionIntent = Literal[
    "open_website",
    "open_app",
    "file_search",
    "noop",
    "blocked",
]

ActionExecutionStatus = Literal[
    "pending_confirmation",
    "executed",
    "blocked",
    "failed",
    "preview_only",
]

ActionSafetyLevel = Literal[
    "safe",
    "confirmation_required",
    "sensitive",
    "blocked",
]

ActionExecutionMode = Literal[
    "preview_only",
    "confirmed_execution",
]


class ActionTarget(BaseModel):
    kind: str
    value: str
    label: str | None = None


class SafeActionPlan(BaseModel):
    intent: ActionIntent
    target: ActionTarget | None = None
    safety_level: ActionSafetyLevel = "confirmation_required"
    execution_mode: ActionExecutionMode = "preview_only"
    requires_confirmation: bool = True
    can_execute: bool = False
    reason: str
    preview_steps: list[str] = []


class ActionExecutionResult(BaseModel):
    status: ActionExecutionStatus
    intent: ActionIntent
    target: ActionTarget | None = None
    safety_level: ActionSafetyLevel
    can_execute: bool = False
    executed: bool = False
    message: str
    error: str | None = None


def create_preview_action_plan(
    intent: ActionIntent,
    target: ActionTarget | None = None,
    reason: str = "Action execution is preview-only in this phase.",
) -> SafeActionPlan:
    return SafeActionPlan(
        intent=intent,
        target=target,
        safety_level="confirmation_required",
        execution_mode="preview_only",
        requires_confirmation=True,
        can_execute=False,
        reason=reason,
        preview_steps=[
            "Detect safe action intent.",
            "Show action preview.",
            "Wait for explicit user confirmation in a later phase.",
            "Do not execute anything in Phase 27.1.",
        ],
    )


def create_blocked_action_result(
    intent: ActionIntent,
    message: str,
    target: ActionTarget | None = None,
) -> ActionExecutionResult:
    return ActionExecutionResult(
        status="blocked",
        intent=intent,
        target=target,
        safety_level="blocked",
        can_execute=False,
        executed=False,
        message=message,
        error=message,
    )


def create_preview_only_result(
    intent: ActionIntent,
    message: str,
    target: ActionTarget | None = None,
) -> ActionExecutionResult:
    return ActionExecutionResult(
        status="preview_only",
        intent=intent,
        target=target,
        safety_level="confirmation_required",
        can_execute=False,
        executed=False,
        message=message,
    )


class ActionExecutionRequest(BaseModel):
    request_id: str | None = None
    intent: ActionIntent
    target: ActionTarget | None = None
    original_text: str
    normalized_text: str | None = None
    confidence: int = 0
    safety_level: ActionSafetyLevel = "confirmation_required"
    user_confirmed: bool = False
    dry_run: bool = True
    source: str = "commands_page"


class ActionExecutionResponse(BaseModel):
    request_id: str | None = None
    status: ActionExecutionStatus
    intent: ActionIntent
    target: ActionTarget | None = None
    safety_level: ActionSafetyLevel
    can_execute: bool = False
    executed: bool = False
    dry_run: bool = True
    user_confirmed: bool = False
    message: str
    error: str | None = None
    preview_steps: list[str] = []


def create_execution_preview_response(
    request: ActionExecutionRequest,
    message: str = "Execution request received as preview only.",
) -> ActionExecutionResponse:
    return ActionExecutionResponse(
        status="preview_only",
        intent=request.intent,
        target=request.target,
        safety_level=request.safety_level,
        can_execute=False,
        executed=False,
        dry_run=True,
        user_confirmed=request.user_confirmed,
        message=message,
        preview_steps=[
            "Receive action execution request.",
            "Validate user confirmation.",
            "Validate safety level.",
            "Keep execution disabled in Phase 27.2.",
        ],
    )


def create_confirmation_required_response(
    request: ActionExecutionRequest,
) -> ActionExecutionResponse:
    return ActionExecutionResponse(
        status="pending_confirmation",
        intent=request.intent,
        target=request.target,
        safety_level=request.safety_level,
        can_execute=False,
        executed=False,
        dry_run=True,
        user_confirmed=request.user_confirmed,
        message="User confirmation is required before this action can execute in a future phase.",
    )


def create_execution_blocked_response(
    request: ActionExecutionRequest,
    reason: str,
) -> ActionExecutionResponse:
    return ActionExecutionResponse(
        status="blocked",
        intent=request.intent,
        target=request.target,
        safety_level="blocked",
        can_execute=False,
        executed=False,
        dry_run=True,
        user_confirmed=request.user_confirmed,
        message=reason,
        error=reason,
    )

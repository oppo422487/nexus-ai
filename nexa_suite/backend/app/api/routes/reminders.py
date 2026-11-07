"""API routes for the local reminder/scheduler foundation."""

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.reminders import (
    create_reminder,
    list_reminders,
    list_due_reminders,
    set_reminder_status,
    delete_reminder,
    snooze_reminder,
    parse_natural_reminder,
    update_reminder,
)
from app.schemas.reminders import (
    ReminderCreateRequest,
    ReminderItem,
    ReminderListResponse,
    ReminderMutationResponse,
    NaturalLanguageReminderRequest,
    ReminderSnoozeRequest,
    ReminderUpdateRequest,
)

router = APIRouter(prefix="/reminders", tags=["reminders"])


def _denied() -> ReminderMutationResponse:
    message = permission_denied_message("reminders")
    return ReminderMutationResponse(
        status="blocked", ok=False, message=message, error=message
    )


@router.get("", response_model=ReminderListResponse)
def get_reminders(include_done: bool = True) -> ReminderListResponse:
    if not is_permission_enabled("reminders"):
        return ReminderListResponse(
            status="blocked",
            message=permission_denied_message("reminders"),
        )
    items = [ReminderItem(**r) for r in list_reminders(include_done=include_done)]
    due = [ReminderItem(**r) for r in list_due_reminders()]
    return ReminderListResponse(
        reminders=items,
        due_now=due,
        message=f"{len(items)} reminder(s) loaded.",
    )


@router.post("", response_model=ReminderMutationResponse)
def add_reminder(request: ReminderCreateRequest) -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"):
        return _denied()
    if not request.user_confirmed:
        return ReminderMutationResponse(
            status="confirmation_required",
            ok=False,
            message="Reminder creation requires explicit confirmation.",
            error="user_confirmed must be true to create a reminder.",
        )
    result = create_reminder(request.title, request.note, request.due_at, request.recurrence)
    record_audit_event(
        source="reminders",
        intent="reminder_create",
        status="completed" if result["ok"] else "failed",
        target=(request.title or "")[:120],
        message=result.get("error") or "Reminder created.",
    )
    if not result["ok"]:
        return ReminderMutationResponse(
            status="failed", ok=False, message=result["error"] or "", error=result["error"]
        )
    return ReminderMutationResponse(
        status="completed",
        ok=True,
        reminder=ReminderItem(**result["reminder"]),
        message="Reminder created.",
    )


@router.post("/{reminder_id}/status", response_model=ReminderMutationResponse)
def update_reminder_status(reminder_id: str, status: str = "done") -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"):
        return _denied()
    result = set_reminder_status(reminder_id, status)
    if not result["ok"]:
        return ReminderMutationResponse(
            status="failed", ok=False, message=result["error"] or "", error=result["error"]
        )
    return ReminderMutationResponse(
        status="completed", ok=True, message=f"Reminder marked {status}."
    )


@router.delete("/{reminder_id}", response_model=ReminderMutationResponse)
def remove_reminder(reminder_id: str) -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"):
        return _denied()
    result = delete_reminder(reminder_id)
    if not result["ok"]:
        return ReminderMutationResponse(
            status="failed", ok=False, message=result["error"] or "", error=result["error"]
        )
    record_audit_event(
        source="reminders",
        intent="reminder_delete",
        status="completed",
        target=reminder_id,
        message="Reminder record deleted (local database row only).",
    )
    return ReminderMutationResponse(
        status="completed", ok=True, message="Reminder deleted."
    )


@router.post("/natural", response_model=ReminderMutationResponse)
def add_natural_reminder(request: NaturalLanguageReminderRequest) -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"):
        return _denied()
    if not request.user_confirmed:
        return ReminderMutationResponse(status="confirmation_required", ok=False, message="Natural-language reminder creation requires confirmation.")
    parsed = parse_natural_reminder(request.text)
    if not parsed["ok"]:
        return ReminderMutationResponse(status="failed", ok=False, message=parsed["error"], error=parsed["error"])
    result = create_reminder(parsed["title"], "", parsed["due_at"], parsed["recurrence"])
    if not result["ok"]:
        return ReminderMutationResponse(status="failed", ok=False, message=result["error"], error=result["error"])
    record_audit_event("reminders", "reminder_natural_create", "completed", target=parsed["title"], message=request.text)
    return ReminderMutationResponse(status="completed", ok=True, reminder=ReminderItem(**result["reminder"]), message="Smart reminder created.")


@router.post("/{reminder_id}/snooze", response_model=ReminderMutationResponse)
def snooze_existing_reminder(reminder_id: str, request: ReminderSnoozeRequest) -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"):
        return _denied()
    if not request.user_confirmed:
        return ReminderMutationResponse(status="confirmation_required", ok=False, message="Snoozing requires confirmation.")
    result = snooze_reminder(reminder_id, request.minutes)
    if not result["ok"]:
        return ReminderMutationResponse(status="failed", ok=False, message=result["error"], error=result["error"])
    record_audit_event("reminders", "reminder_snooze", "completed", target=reminder_id, message=f"Snoozed {request.minutes} minutes.")
    return ReminderMutationResponse(status="completed", ok=True, message=f"Reminder snoozed for {request.minutes} minutes.")


@router.put("/{reminder_id}", response_model=ReminderMutationResponse)
def edit_reminder(reminder_id: str, request: ReminderUpdateRequest) -> ReminderMutationResponse:
    if not is_permission_enabled("reminders"): return _denied()
    if not request.user_confirmed:
        return ReminderMutationResponse(status="confirmation_required", ok=False, message="Reminder editing requires confirmation.")
    result = update_reminder(reminder_id, title=request.title, note=request.note, due_at=request.due_at, recurrence=request.recurrence)
    if not result["ok"]:
        return ReminderMutationResponse(status="failed", ok=False, message=result["error"], error=result["error"])
    record_audit_event("reminders", "reminder_edit", "completed", target=reminder_id, message="Reminder updated.")
    return ReminderMutationResponse(status="completed", ok=True, message="Reminder updated.")

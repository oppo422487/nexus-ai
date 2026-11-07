"""Schemas for the local reminder/scheduler foundation."""

from pydantic import BaseModel


class ReminderItem(BaseModel):
    id: str
    title: str
    note: str = ""
    due_at: str | None = None
    status: str = "pending"
    created_at: str
    recurrence: str = ""
    last_triggered_at: str | None = None


class ReminderCreateRequest(BaseModel):
    title: str
    note: str = ""
    due_at: str | None = None
    user_confirmed: bool = False
    recurrence: str = ""


class NaturalLanguageReminderRequest(BaseModel):
    text: str
    user_confirmed: bool = False


class ReminderSnoozeRequest(BaseModel):
    minutes: int = 10
    user_confirmed: bool = False


class ReminderUpdateRequest(BaseModel):
    title: str | None = None
    note: str | None = None
    due_at: str | None = None
    recurrence: str | None = None
    user_confirmed: bool = False


class ReminderListResponse(BaseModel):
    status: str = "ok"
    module: str = "reminders"
    reminders: list[ReminderItem] = []
    due_now: list[ReminderItem] = []
    message: str = ""


class ReminderMutationResponse(BaseModel):
    status: str
    module: str = "reminders"
    ok: bool
    reminder: ReminderItem | None = None
    message: str = ""
    error: str | None = None

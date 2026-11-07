"""Schemas for local-only WhatsApp contact mapping."""

from pydantic import BaseModel, Field


class ContactItem(BaseModel):
    name: str
    phone_number: str
    email_address: str | None = None
    nickname: str | None = None
    aliases: list[str] = Field(default_factory=list)
    relationship: str = "unknown"
    default_tone: str = "normal"
    created_at: str
    updated_at: str


class ContactCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    phone_number: str = Field(..., min_length=6, max_length=32)
    email_address: str | None = Field(default=None, max_length=320)
    nickname: str | None = Field(default=None, max_length=80)
    aliases: list[str] = Field(default_factory=list)
    relationship: str | None = Field(default=None, max_length=40)
    default_tone: str | None = Field(default=None, max_length=40)


class ContactListResponse(BaseModel):
    status: str = "ok"
    contacts: list[ContactItem]
    storage: str = "local_json"
    message: str


class ContactMutationResponse(BaseModel):
    status: str
    ok: bool
    contact: ContactItem | None = None
    message: str
    error: str | None = None

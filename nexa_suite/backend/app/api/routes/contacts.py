"""Local-only WhatsApp contact mapping routes."""

from fastapi import APIRouter

from app.contacts import delete_contact, list_contacts, save_contact
from app.schemas.contacts import ContactCreateRequest, ContactItem, ContactListResponse, ContactMutationResponse

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _item(record) -> ContactItem:
    return ContactItem(
        name=record.name,
        phone_number=record.phone_number,
        email_address=record.email_address,
        nickname=record.nickname,
        aliases=record.aliases or [],
        relationship=record.relationship,
        default_tone=record.default_tone,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=ContactListResponse)
def get_contacts() -> ContactListResponse:
    contacts = [_item(record) for record in list_contacts()]
    return ContactListResponse(
        contacts=contacts,
        message=f"{len(contacts)} local WhatsApp contact(s).",
    )


@router.post("", response_model=ContactMutationResponse)
def upsert_contact(request: ContactCreateRequest) -> ContactMutationResponse:
    try:
        record = save_contact(
            request.name,
            request.phone_number,
            request.nickname,
            request.aliases,
            request.relationship,
            request.default_tone,
            request.email_address,
        )
    except ValueError as exc:
        return ContactMutationResponse(
            status="blocked",
            ok=False,
            message=str(exc),
            error=str(exc),
        )
    return ContactMutationResponse(
        status="saved",
        ok=True,
        contact=_item(record),
        message=f"{record.name} saved locally for messaging and email.",
    )


@router.delete("/{name}", response_model=ContactMutationResponse)
def remove_contact(name: str) -> ContactMutationResponse:
    deleted = delete_contact(name)
    if not deleted:
        return ContactMutationResponse(
            status="not_found",
            ok=False,
            message="Contact was not found.",
            error="Contact was not found.",
        )
    return ContactMutationResponse(
        status="deleted",
        ok=True,
        message="Contact deleted from local WhatsApp contacts.",
    )

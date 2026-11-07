"""Local-only contact storage for safe WhatsApp drafts."""

from .store import CONTACTS_FILE
from .store import ContactRecord
from .store import add_contact_alias
from .store import delete_contact
from .store import find_contact_matches
from .store import get_contact
from .store import list_contacts
from .store import normalize_contact_name
from .store import normalize_phone_number
from .store import save_contact

__all__ = [
    "CONTACTS_FILE",
    "ContactRecord",
    "add_contact_alias",
    "delete_contact",
    "find_contact_matches",
    "get_contact",
    "list_contacts",
    "normalize_contact_name",
    "normalize_phone_number",
    "save_contact",
]

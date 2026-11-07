"""Local JSON contact store for WhatsApp draft-only messaging."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import re
import threading
from app.core.runtime_paths import data_dir

CONTACTS_FILE = data_dir() / "whatsapp_contacts.json"

_lock = threading.Lock()
EMAIL_ADDRESS_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


@dataclass
class ContactRecord:
    name: str
    phone_number: str
    email_address: str | None = None
    nickname: str | None = None
    aliases: list[str] | None = None
    relationship: str = "unknown"
    default_tone: str = "normal"
    created_at: str = ""
    updated_at: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_contact_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _name_candidates(record: dict) -> set[str]:
    candidates = {normalize_contact_name(record.get("name"))}
    nickname = normalize_contact_name(record.get("nickname"))
    if nickname:
        candidates.add(nickname)
    aliases = record.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            clean_alias = normalize_contact_name(str(alias))
            if clean_alias:
                candidates.add(clean_alias)
    return {item for item in candidates if item}


def _record_from_dict(value: dict) -> ContactRecord | None:
    try:
        row = dict(value)
        row.setdefault("aliases", [])
        row.setdefault("email_address", None)
        row.setdefault("relationship", "unknown")
        row.setdefault("default_tone", "normal")
        return ContactRecord(**row)
    except TypeError:
        return None


def _fuzzy_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def normalize_phone_number(value: str | None) -> str:
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "88" + digits
    if digits.startswith("880") and len(digits) == 13:
        return digits
    if digits.startswith("1") and len(digits) == 10:
        return "880" + digits
    raise ValueError("Malformed phone number. Use a valid Bangladesh mobile number such as 017xxxxxxxx.")


def _read_contacts() -> dict[str, dict]:
    try:
        if CONTACTS_FILE.exists():
            raw = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw
    except Exception:
        pass
    return {}


def _write_contacts(data: dict[str, dict]) -> None:
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_contacts() -> list[ContactRecord]:
    data = _read_contacts()
    contacts: list[ContactRecord] = []
    for value in data.values():
        if not isinstance(value, dict):
            continue
        try:
            contacts.append(ContactRecord(**value))
        except TypeError:
            continue
    return sorted(contacts, key=lambda item: item.name.lower())


def get_contact(name: str | None) -> ContactRecord | None:
    key = normalize_contact_name(name)
    if not key:
        return None
    data = _read_contacts()
    row = data.get(key)
    if isinstance(row, dict):
        return _record_from_dict(row)
    for item in data.values():
        if not isinstance(item, dict):
            continue
        if key in _name_candidates(item):
            return _record_from_dict(item)
    fuzzy_matches: list[ContactRecord] = []
    for item in data.values():
        if not isinstance(item, dict):
            continue
        candidates = _name_candidates(item)
        if any(_fuzzy_ratio(key, candidate) >= 0.75 for candidate in candidates):
            record = _record_from_dict(item)
            if record:
                fuzzy_matches.append(record)
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]
    return None


def find_contact_matches(name: str | None) -> list[ContactRecord]:
    key = normalize_contact_name(name)
    if not key:
        return []
    data = _read_contacts()
    exact: list[ContactRecord] = []
    fuzzy: list[ContactRecord] = []
    for item in data.values():
        if not isinstance(item, dict):
            continue
        record = _record_from_dict(item)
        if not record:
            continue
        candidates = _name_candidates(item)
        if key in candidates:
            exact.append(record)
        elif any(_fuzzy_ratio(key, candidate) >= 0.75 for candidate in candidates):
            fuzzy.append(record)
    return exact or fuzzy


def _normalize_aliases(aliases: list[str] | str | None, nickname: str | None = None) -> list[str]:
    values: list[str] = []
    if isinstance(aliases, str):
        values.extend(part.strip() for part in aliases.split(","))
    elif isinstance(aliases, list):
        values.extend(str(part).strip() for part in aliases)
    if nickname and nickname.strip():
        values.append(nickname.strip())
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = " ".join(value.split())
        key = normalize_contact_name(clean)
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _normalize_relationship(value: str | None) -> str:
    clean = normalize_contact_name(value)
    return clean if clean in {"boss", "client", "friend", "family", "unknown"} else "unknown"


def _normalize_tone(value: str | None, relationship: str = "unknown") -> str:
    clean = normalize_contact_name(value)
    if clean in {"formal", "friendly", "normal"}:
        return clean
    if relationship in {"boss", "client"}:
        return "formal"
    if relationship in {"friend", "family"}:
        return "friendly"
    return "normal"


def save_contact(
    name: str,
    phone_number: str,
    nickname: str | None = None,
    aliases: list[str] | str | None = None,
    relationship: str | None = None,
    default_tone: str | None = None,
    email_address: str | None = None,
) -> ContactRecord:
    clean_name = " ".join((name or "").strip().split())
    if not clean_name:
        raise ValueError("Contact name is required.")
    normalized_phone = normalize_phone_number(phone_number)
    clean_email = (email_address or "").strip()
    if clean_email and not EMAIL_ADDRESS_RE.fullmatch(clean_email):
        raise ValueError("Malformed email address.")
    key = normalize_contact_name(clean_name)
    timestamp = _now()
    with _lock:
        data = _read_contacts()
        existing = data.get(key) if isinstance(data.get(key), dict) else {}
        created_at = str(existing.get("created_at") or timestamp)
        merged_aliases = _normalize_aliases(existing.get("aliases") if isinstance(existing, dict) else None, existing.get("nickname") if isinstance(existing, dict) else None)
        for alias in _normalize_aliases(aliases, nickname):
            if normalize_contact_name(alias) not in {normalize_contact_name(item) for item in merged_aliases}:
                merged_aliases.append(alias)
        normalized_relationship = _normalize_relationship(relationship or existing.get("relationship") if isinstance(existing, dict) else relationship)
        normalized_tone = _normalize_tone(default_tone or existing.get("default_tone") if isinstance(existing, dict) else default_tone, normalized_relationship)
        record = ContactRecord(
            name=clean_name,
            phone_number=normalized_phone,
            email_address=(clean_email or existing.get("email_address") or "").strip() or None,
            nickname=(" ".join(nickname.strip().split()) if nickname and nickname.strip() else None),
            aliases=merged_aliases,
            relationship=normalized_relationship,
            default_tone=normalized_tone,
            created_at=created_at,
            updated_at=timestamp,
        )
        data[key] = asdict(record)
        _write_contacts(data)
    return record


def add_contact_alias(name: str | None, alias: str | None) -> ContactRecord | None:
    key = normalize_contact_name(name)
    clean_alias = " ".join((alias or "").strip().split())
    if not key or not clean_alias:
        return None
    with _lock:
        data = _read_contacts()
        matches = []
        for stored_key, item in data.items():
            if isinstance(item, dict) and key in _name_candidates(item):
                matches.append(stored_key)
        if len(matches) != 1:
            return None
        row = data[matches[0]]
        aliases = _normalize_aliases(row.get("aliases"), row.get("nickname"))
        if normalize_contact_name(clean_alias) not in {normalize_contact_name(item) for item in aliases}:
            aliases.append(clean_alias)
        row["aliases"] = aliases
        row.setdefault("relationship", "unknown")
        row.setdefault("default_tone", _normalize_tone(None, str(row.get("relationship") or "unknown")))
        row["updated_at"] = _now()
        data[matches[0]] = row
        _write_contacts(data)
        return _record_from_dict(row)


def delete_contact(name: str | None) -> bool:
    key = normalize_contact_name(name)
    if not key:
        return False
    with _lock:
        data = _read_contacts()
        if key in data:
            del data[key]
            _write_contacts(data)
            return True
        for stored_key, item in list(data.items()):
            if isinstance(item, dict) and key in _name_candidates(item):
                del data[stored_key]
                _write_contacts(data)
                return True
        matches: list[str] = []
        for stored_key, item in data.items():
            if isinstance(item, dict) and any(_fuzzy_ratio(key, candidate) >= 0.75 for candidate in _name_candidates(item)):
                matches.append(stored_key)
        if len(matches) == 1:
            del data[matches[0]]
            _write_contacts(data)
            return True
    return False

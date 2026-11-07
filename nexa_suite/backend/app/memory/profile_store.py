"""Local-only profile memory.

This module intentionally stores only small non-sensitive preferences. It does
not sync to cloud services and never invents facts about the user.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from threading import Lock
from typing import Any

from app.core.runtime_paths import data_dir

DATA_PATH = data_dir() / "profile_memory.json"
_LOCK = Lock()


@dataclass
class LocalProfile:
    display_preference: str | None = None
    address_style: str | None = "Boss"
    project_preferences: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _load_raw() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_profile() -> LocalProfile:
    with _LOCK:
        raw = _load_raw()
        return LocalProfile(
            display_preference=raw.get("display_preference"),
            address_style=raw.get("address_style") or "Boss",
            project_preferences=raw.get("project_preferences") or {},
            updated_at=raw.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )


def save_profile(profile: LocalProfile) -> LocalProfile:
    profile.updated_at = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
    return profile


def summarize_profile() -> str:
    profile = get_profile()
    facts: list[str] = []
    if profile.display_preference:
        facts.append(f"display preference: {profile.display_preference}")
    if profile.address_style:
        facts.append(f"address style: {profile.address_style}")
    if profile.project_preferences:
        facts.append(f"saved project preferences: {', '.join(profile.project_preferences.keys())}")
    if not facts:
        return "No personal profile facts are saved yet."
    return "; ".join(facts)

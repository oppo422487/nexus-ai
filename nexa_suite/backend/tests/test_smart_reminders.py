from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from app.reminders.store import parse_natural_reminder


def test_parse_relative_banglish_reminder() -> None:
    now = datetime.datetime(2026, 8, 28, 10, 0, tzinfo=ZoneInfo("Asia/Dhaka"))
    result = parse_natural_reminder("amake 15 minute por pani khete mone koriye dio", now)
    assert result["ok"] is True
    due = datetime.datetime.fromisoformat(result["due_at"])
    assert due == datetime.datetime(2026, 8, 28, 4, 15, tzinfo=datetime.timezone.utc)
    assert "pani" in result["title"]


def test_parse_recurring_reminder() -> None:
    now = datetime.datetime(2026, 8, 28, 10, 0, tzinfo=ZoneInfo("Asia/Dhaka"))
    result = parse_natural_reminder("remind me every day to exercise", now)
    assert result["recurrence"] == "daily"
    assert result["title"] == "exercise"

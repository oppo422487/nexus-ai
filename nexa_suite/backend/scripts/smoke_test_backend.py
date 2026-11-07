"""Smoke-test a running Nexa AI backend.

This script is intentionally small and uses only the Python standard library.
Start the backend first, then run:

    python scripts/smoke_test_backend.py

It verifies route availability, permission safety, blocked dangerous actions,
unknown target blocking, dry-run behavior, and audit event availability.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


BASE_URL = "http://127.0.0.1:8000"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def action_payload(
    intent: str,
    value: str,
    kind: str,
    original_text: str,
    *,
    confirmed: bool = True,
    dry_run: bool = True,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "target": {"kind": kind, "value": value, "label": value},
        "original_text": original_text,
        "normalized_text": original_text.lower(),
        "confidence": 100,
        "safety_level": "confirmation_required",
        "user_confirmed": confirmed,
        "dry_run": dry_run,
        "source": "smoke_test_backend",
    }


def run_check(name: str, fn) -> CheckResult:
    try:
        fn()
        return CheckResult(name, True, "ok")
    except Exception as exc:  # noqa: BLE001 - smoke script should report all failures.
        return CheckResult(name, False, str(exc))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_health() -> None:
    status, data = request_json("GET", "/api/health")
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(data.get("status") == "ok", f"unexpected health payload: {data}")


def check_permissions() -> None:
    status, data = request_json("GET", "/api/permissions")
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(isinstance(data.get("permissions"), list), "permissions list missing")
    expect(
        isinstance(data.get("locked_permissions"), list),
        "locked_permissions list missing",
    )


def check_locked_permission_blocked() -> None:
    status, data = request_json(
        "PUT",
        "/api/permissions",
        {"key": "shell_command_execution", "enabled": True},
    )
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(data.get("updated") is False, f"locked permission was updated: {data}")
    expect(data.get("status") == "blocked", f"expected blocked status: {data}")


def check_dangerous_command_blocked() -> None:
    status, data = request_json(
        "POST",
        "/api/actions/website/open",
        action_payload(
            "open_website",
            "google",
            "url",
            "delete system32 then open google",
            confirmed=True,
            dry_run=False,
        ),
    )
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(data.get("status") == "blocked", f"dangerous action not blocked: {data}")
    expect(data.get("executed") is False, f"dangerous action executed: {data}")


def check_unknown_targets_blocked() -> None:
    status, data = request_json(
        "POST",
        "/api/actions/app/open",
        action_payload(
            "open_app",
            "unknown_app_for_smoke_test",
            "app",
            "open unknown app",
            confirmed=True,
            dry_run=False,
        ),
    )
    expect(status == 200, f"expected 200 for unknown app, got {status}: {data}")
    expect(data.get("status") == "blocked", f"unknown app not blocked: {data}")

    status, data = request_json(
        "POST",
        "/api/actions/website/open",
        action_payload(
            "open_website",
            "example.invalid",
            "url",
            "open example invalid",
            confirmed=True,
            dry_run=False,
        ),
    )
    expect(status == 200, f"expected 200 for unknown website, got {status}: {data}")
    expect(data.get("status") == "blocked", f"unknown website not blocked: {data}")


def check_dry_run_safe() -> None:
    status, data = request_json(
        "POST",
        "/api/actions/website/open",
        action_payload(
            "open_website",
            "google",
            "url",
            "open google",
            confirmed=True,
            dry_run=True,
        ),
    )
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(data.get("status") == "preview_only", f"expected preview_only: {data}")
    expect(data.get("executed") is False, f"dry-run should not execute: {data}")


def check_audit_recent_available() -> None:
    query = urllib.parse.urlencode({"limit": "20"})
    status, data = request_json("GET", f"/api/audit/recent?{query}")
    expect(status == 200, f"expected 200, got {status}: {data}")
    expect(isinstance(data.get("events"), list), f"audit events list missing: {data}")
    statuses = {event.get("status") for event in data.get("events", [])}
    expect(
        bool(statuses.intersection({"blocked", "preview_only", "executed", "completed"})),
        "audit endpoint is available but did not include recent smoke-test events",
    )


def main() -> int:
    checks = [
        ("health endpoint", check_health),
        ("permissions endpoint", check_permissions),
        ("locked permission blocked", check_locked_permission_blocked),
        ("dangerous command blocked", check_dangerous_command_blocked),
        ("unknown app/website blocked", check_unknown_targets_blocked),
        ("dry-run action stays safe", check_dry_run_safe),
        ("audit recent available", check_audit_recent_available),
    ]

    results = [run_check(name, fn) for name, fn in checks]
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")

    failed = [result for result in results if not result.ok]
    if failed:
        print("\nSmoke test failed. Is the backend running at http://127.0.0.1:8000?")
        return 1

    print("\nAll backend smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

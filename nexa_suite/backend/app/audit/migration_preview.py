"""Migration preview utility for the Nexa AI audit SQLite schema.

Read-only preview of the SQL migration script.
No database connection, no SQL execution, no file writes.
"""

import os
from dataclasses import dataclass, field

from app.audit.sqlite_config import get_sqlite_audit_config


@dataclass
class AuditMigrationPreview:
    """Preview information for the audit log SQL migration script."""

    script_path: str
    exists: bool
    can_run: bool
    migrations_enabled: bool
    statement_count: int
    table_name: str
    preview_message: str
    safety_notes: list[str] = field(default_factory=list)


def get_audit_migration_preview() -> AuditMigrationPreview:
    """Read and preview the SQL migration script without executing it."""
    config = get_sqlite_audit_config()

    script_dir = os.path.join(os.path.dirname(__file__), "sql")
    script_path = os.path.join(script_dir, "create_audit_logs.sql")
    exists = os.path.isfile(script_path)

    statement_count = 0
    if exists:
        try:
            with open(script_path, encoding="utf-8") as f:
                content = f.read()
            statement_count = max(
                len([s.strip() for s in content.split(";") if s.strip()]), 0
            )
        except OSError:
            pass

    if not exists:
        preview_message = (
            "SQLite audit migration script not found. "
            "Expected at: create_audit_logs.sql"
        )
    else:
        preview_message = (
            "SQLite audit migration script is available for preview only. "
            "Migrations are disabled in this phase."
        )

    safety_notes = [
        "No database file will be created.",
        "No SQL will be executed.",
        "No audit records will be inserted.",
        "Migration execution is disabled until a future explicit phase.",
    ]

    return AuditMigrationPreview(
        script_path=script_path,
        exists=exists,
        can_run=False,
        migrations_enabled=config.migrations_enabled,
        statement_count=statement_count,
        table_name=config.table_name,
        preview_message=preview_message,
        safety_notes=safety_notes,
    )


def get_audit_migration_preview_dict() -> dict:
    """Return the migration preview as a plain dictionary."""
    return get_audit_migration_preview().__dict__

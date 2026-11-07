"""SQLite audit storage configuration for the Nexa AI backend.

Storage is disabled by default in the current phase.
No database file is created, no migrations are run, no writes occur.
"""

from dataclasses import dataclass


@dataclass
class SQLiteAuditConfig:
    """Configuration for SQLite-based audit log storage.

    All write and migration operations are disabled by default.
    """

    database_path: str = "data/nexa_audit.db"
    table_name: str = "audit_logs"
    migrations_enabled: bool = False
    writes_enabled: bool = False


def get_sqlite_audit_config() -> SQLiteAuditConfig:
    """Return the default SQLite audit configuration.

    migrations_enabled is False — no tables are created.
    writes_enabled is False — no records are persisted.
    """
    return SQLiteAuditConfig()

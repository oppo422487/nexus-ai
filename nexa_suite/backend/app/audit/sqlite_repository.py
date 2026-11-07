"""SQLite audit repository skeleton for the Nexa AI backend.

All database operations are disabled in this phase.
No database file is created, no connections are made, no SQL is executed.
"""

from app.audit.sqlite_config import get_sqlite_audit_config
from app.schemas import AuditLogRequest


class SQLiteAuditRepository:
    """Skeleton repository for SQLite-based audit storage.

    All read and write operations return disabled responses.
    """

    def __init__(self) -> None:
        self._config = get_sqlite_audit_config()

    def is_available(self) -> bool:
        """Return False — migrations and writes are disabled in this phase."""
        return False

    def get_storage_status(self) -> dict:
        """Return the current SQLite storage status."""
        return {
            "storage_backend": "sqlite",
            "database_path": self._config.database_path,
            "table_name": self._config.table_name,
            "migrations_enabled": False,
            "writes_enabled": False,
            "available": False,
            "reason": "SQLite audit writes and migrations are disabled in this phase.",
            "message": "SQLite audit storage skeleton is prepared but disabled.",
        }

    def insert_audit_log(self, request: AuditLogRequest) -> dict:
        """Attempt to insert an audit log record.

        No database connection or SQL execution occurs — writes are disabled.
        """
        return {
            "stored": False,
            "storage_backend": "sqlite",
            "reason": "SQLite audit writes are disabled in this phase.",
        }

    def list_audit_logs(self, limit: int = 20) -> dict:
        """Attempt to list audit log records.

        No database connection or SQL execution occurs — reads are disabled.
        """
        return {
            "items": [],
            "storage_backend": "sqlite",
            "available": False,
            "message": "SQLite audit reads are disabled in this phase.",
        }

    def clear_audit_logs(self) -> dict:
        """Attempt to clear all audit log records.

        No database connection or SQL execution occurs — clear is disabled.
        """
        return {
            "cleared": False,
            "storage_backend": "sqlite",
            "message": "SQLite audit clear operation is disabled in this phase.",
        }

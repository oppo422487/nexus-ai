"""Local database configuration skeleton for the Nexa AI backend.

Database is disabled by default in the current phase.
No database file, connection, SQL, or storage operations occur.
"""

from dataclasses import dataclass


@dataclass
class LocalDatabaseConfig:
    """Configuration for local SQLite-based database storage.

    All database operations are disabled by default.
    """

    database_enabled: bool = False
    database_mode: str = "disabled"
    database_path: str = "data/nexa_local.db"
    migrations_enabled: bool = False
    writes_enabled: bool = False
    reads_enabled: bool = False
    reason: str = "Local database is disabled in this phase."


def get_local_database_config() -> LocalDatabaseConfig:
    """Return the default local database configuration.

    All feature flags (database_enabled, migrations_enabled,
    writes_enabled, reads_enabled) are False.
    """
    return LocalDatabaseConfig()

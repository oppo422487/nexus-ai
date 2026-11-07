"""Database status schema for the Nexa AI backend."""

from pydantic import BaseModel


class DatabaseStatusResponse(BaseModel):
    """Status response for the local database module.

    All database operations are disabled in this phase.
    """

    status: str = "ok"
    module: str = "local_database"
    phase: str = "22.4"
    database_enabled: bool = False
    database_mode: str = "disabled"
    database_path: str = "data/nexa_local.db"
    migrations_enabled: bool = False
    reads_enabled: bool = False
    writes_enabled: bool = False
    reason: str = "Local database is disabled in this phase."
    execution_enabled: bool = False

"""Database status API routes for the Nexa AI backend."""

from fastapi import APIRouter

from app.database import get_local_database_config
from app.schemas import DatabaseStatusResponse

router = APIRouter(prefix="/database", tags=["database"])


@router.get("/status", response_model=DatabaseStatusResponse)
def database_status() -> DatabaseStatusResponse:
    """Return the local database module status.

    All database operations are disabled in this phase.
    """
    config = get_local_database_config()
    return DatabaseStatusResponse(
        status="ok",
        module="local_database",
        phase="22.4",
        database_enabled=config.database_enabled,
        database_mode=config.database_mode,
        database_path=config.database_path,
        migrations_enabled=config.migrations_enabled,
        reads_enabled=config.reads_enabled,
        writes_enabled=config.writes_enabled,
        reason=config.reason,
        execution_enabled=False,
    )

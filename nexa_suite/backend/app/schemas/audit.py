"""Audit log request/response schemas for the Nexa AI backend."""

from pydantic import BaseModel


class AuditLogRequest(BaseModel):
    """Incoming audit log request from command or voice interactions."""

    source: str
    original_text: str
    intent: str
    language: str
    confidence: int
    risk_level: str
    action_status: str | None = None
    backend_status: str | None = None
    can_execute: bool = False
    summary: str
    created_at: str | None = None


class AuditLogResponse(BaseModel):
    """Safe preview-only audit response. No database storage or execution."""

    status: str
    audit_id: str
    stored: bool
    execution_enabled: bool
    message: str
    source: str
    intent: str
    risk_level: str
    storage_backend: str | None = None
    storage_message: str | None = None


class AuditRouteHealth(BaseModel):
    """Health status for the audit route module."""

    status: str
    module: str
    phase: str
    storage_enabled: bool
    execution_enabled: bool
    storage_mode: str = "disabled"
    message: str = "Audit storage is prepared but disabled in this phase."
    sqlite_available: bool | None = None
    sqlite_writes_enabled: bool | None = None
    sqlite_database_path: str | None = None
    sqlite_table_name: str | None = None


class AuditMigrationPreviewResponse(BaseModel):
    """Preview-only response describing the SQLite audit migration script state.

    No database operation occurs. can_run and execution_enabled are always False.
    """

    status: str = "preview_only"
    script_path: str
    exists: bool
    can_run: bool = False
    migrations_enabled: bool = False
    statement_count: int
    table_name: str
    preview_message: str
    safety_notes: list[str]
    execution_enabled: bool = False


def create_audit_response(request: AuditLogRequest) -> AuditLogResponse:
    """Build a preview-only audit response.

    This function never stores data or allows execution.
    All responses mark stored as False and execution_enabled as False.
    """
    import secrets

    audit_id = f"aud-{request.source}-{request.confidence}-{int(__import__('time').time())}-{secrets.token_hex(4)}"

    message = (
        "Audit received as preview only. "
        "Storage is disabled and no command execution is enabled in this phase."
    )

    return AuditLogResponse(
        status="preview_logged",
        audit_id=audit_id,
        stored=False,
        execution_enabled=False,
        message=message,
        source=request.source,
        intent=request.intent,
        risk_level=request.risk_level,
    )

"""API routes for safe action execution."""

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas import ActionExecutionRequest
from app.schemas import ActionExecutionResponse
from app.schemas import FileSearchRequest
from app.schemas import FileSearchResponse
from app.schemas import create_execution_blocked_response
from app.schemas.file_search import create_file_search_blocked_response
from app.actions import execute_open_website
from app.actions import execute_open_app
from app.files import search_files_read_only

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/health")
def actions_health() -> dict:
    return {
        "status": "ok",
        "module": "safe_actions",
        "phase": "32.3",
        "website_execution_available": is_permission_enabled("actions_website"),
        "app_execution_available": is_permission_enabled("actions_app"),
        "file_search_available": is_permission_enabled("file_search"),
        "requires_confirmation": True,
    }


@router.post("/website/open")
def open_website_action(request: ActionExecutionRequest) -> ActionExecutionResponse:
    if not is_permission_enabled("actions_website"):
        return create_execution_blocked_response(
            request, permission_denied_message("actions_website")
        )
    response = execute_open_website(request)
    record_audit_event(
        source="actions",
        intent="open_website",
        status=response.status,
        risk_level=response.safety_level,
        target=response.target.value if response.target else "",
        message=response.message,
    )
    return response


@router.post("/app/open")
def open_app_action(request: ActionExecutionRequest) -> ActionExecutionResponse:
    if not is_permission_enabled("actions_app"):
        return create_execution_blocked_response(
            request, permission_denied_message("actions_app")
        )
    response = execute_open_app(request)
    record_audit_event(
        source="actions",
        intent="open_app",
        status=response.status,
        risk_level=response.safety_level,
        target=response.target.value if response.target else "",
        message=response.message,
    )
    return response


@router.post("/files/search")
def file_search_action(request: FileSearchRequest) -> FileSearchResponse:
    if not is_permission_enabled("file_search"):
        return create_file_search_blocked_response(
            request, permission_denied_message("file_search")
        )
    response = search_files_read_only(request)
    record_audit_event(
        source="actions",
        intent="file_search",
        status=response.status,
        risk_level=response.risk_level,
        target=response.query,
        message=f"{response.result_count} result(s), scope={response.scope}",
    )
    return response

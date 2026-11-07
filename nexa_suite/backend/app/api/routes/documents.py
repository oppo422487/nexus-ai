"""API routes for the read-only document assistant."""

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.documents import preview_document, ALLOWED_PREVIEW_SUFFIXES
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.documents import DocumentPreviewRequest, DocumentPreviewResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/health")
def documents_health() -> dict:
    return {
        "status": "ok",
        "module": "documents",
        "read_only": True,
        "allowed_extensions": sorted(s.lstrip(".") for s in ALLOWED_PREVIEW_SUFFIXES),
        "enabled": is_permission_enabled("documents"),
        "execution_enabled": False,
    }


@router.post("/preview", response_model=DocumentPreviewResponse)
def document_preview(request: DocumentPreviewRequest) -> DocumentPreviewResponse:
    if not is_permission_enabled("documents"):
        denied = permission_denied_message("documents")
        return DocumentPreviewResponse(
            status="blocked",
            previewed=False,
            path=request.path,
            message=denied,
            error=denied,
        )

    result = preview_document(request.path)
    record_audit_event(
        source="documents",
        intent="document_preview",
        status=result["status"],
        target=result.get("name", ""),
        message=result.get("message", ""),
    )
    return DocumentPreviewResponse(
        status=result["status"],
        previewed=result["previewed"],
        path=result["path"],
        name=result["name"],
        extension=result["extension"],
        size_bytes=result["size_bytes"],
        page_count=result["page_count"],
        preview_text=result["preview_text"],
        truncated=result["truncated"],
        message=result["message"],
        safety_notes=result["safety_notes"],
        error=result["error"],
    )

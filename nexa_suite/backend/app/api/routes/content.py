"""Safe content-writer exports confined to Nexa's generated-content folder."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.content import ContentExportRequest, ContentExportResponse
from app.core.runtime_paths import data_dir

router = APIRouter(prefix="/content", tags=["content"])
OUTPUT_DIR = data_dir() / "generated_content"


@router.get("/history")
def content_history() -> dict:
    if not is_permission_enabled("content_export"):
        return {"status": "blocked", "documents": [], "message": permission_denied_message("content_export")}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(OUTPUT_DIR.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
        if path.suffix not in {".md", ".txt"}:
            continue
        rows.append({"id": path.stem, "name": path.name, "size": path.stat().st_size, "download_url": f"/api/content/{path.name}"})
    return {"status": "ok", "documents": rows}


@router.post("/export", response_model=ContentExportResponse)
def export_content(request: ContentExportRequest) -> ContentExportResponse:
    if not is_permission_enabled("content_export"):
        message = permission_denied_message("content_export")
        return ContentExportResponse(status="blocked", message=message, error=message)
    if not request.user_confirmed:
        message = "Content export requires explicit confirmation."
        return ContentExportResponse(status="confirmation_required", message=message, error=message)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "-", request.title).strip("-")[:50] or "document"
    document_id = f"{safe_title}-{uuid.uuid4().hex[:10]}"
    path = OUTPUT_DIR / f"{document_id}.{request.format}"
    body = request.content.strip()
    if request.format == "md" and not body.startswith("#"):
        body = f"# {request.title.strip()}\n\n{body}"
    path.write_text(body + "\n", encoding="utf-8")
    record_audit_event("content", "content_export", "completed", "confirmed", path.name, f"chars={len(body)}")
    return ContentExportResponse(status="completed", exported=True, document_id=document_id, download_url=f"/api/content/{path.name}", message="Content exported to Nexa's local generated-content folder.")


@router.get("/{filename}")
def download_content(filename: str) -> FileResponse:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+\.(?:md|txt)", filename):
        raise HTTPException(status_code=404, detail="Document not found.")
    if not is_permission_enabled("content_export"):
        raise HTTPException(status_code=403, detail=permission_denied_message("content_export"))
    path = OUTPUT_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(path, media_type="text/markdown" if path.suffix == ".md" else "text/plain", filename=filename)

"""Schemas for the read-only document assistant."""

from pydantic import BaseModel


class DocumentPreviewRequest(BaseModel):
    path: str


class DocumentPreviewResponse(BaseModel):
    status: str
    module: str = "documents"
    previewed: bool = False
    path: str = ""
    name: str = ""
    extension: str | None = None
    size_bytes: int | None = None
    page_count: int | None = None
    preview_text: str = ""
    truncated: bool = False
    read_only: bool = True
    message: str = ""
    safety_notes: list[str] = []
    error: str | None = None

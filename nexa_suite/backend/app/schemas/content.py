"""Schemas for controlled content generation and export."""

from typing import Literal
from pydantic import BaseModel, Field


class ContentExportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=50000)
    format: Literal["txt", "md"] = "md"
    user_confirmed: bool = False


class ContentExportResponse(BaseModel):
    status: str
    module: str = "content_writer"
    exported: bool = False
    document_id: str | None = None
    download_url: str | None = None
    message: str
    error: str | None = None

"""Schemas for read-only file search requests and responses."""

from typing import Literal, Optional

from pydantic import BaseModel

FileSearchScope = Literal["desktop", "downloads", "documents", "all_safe"]

FileSearchStatus = Literal["preview_only", "completed", "blocked", "failed"]

FileSearchRiskLevel = Literal["safe", "blocked"]


class FileSearchRequest(BaseModel):
    request_id: Optional[str] = None
    query: str
    scope: FileSearchScope = "all_safe"
    extensions: list[str] = []
    max_results: int = 20
    original_text: Optional[str] = None
    source: str = "commands_page"
    dry_run: bool = True


class FileSearchResultItem(BaseModel):
    name: str
    path: str
    extension: Optional[str] = None
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None
    is_directory: bool = False


class FileSearchResponse(BaseModel):
    request_id: Optional[str] = None
    status: FileSearchStatus
    query: str
    scope: FileSearchScope
    risk_level: FileSearchRiskLevel = "safe"
    searched: bool = False
    result_count: int = 0
    results: list[FileSearchResultItem] = []
    message: str
    error: Optional[str] = None
    safety_notes: list[str] = []


def create_file_search_preview_response(
    request: FileSearchRequest,
    message: str = "File search request received as preview only.",
) -> FileSearchResponse:
    return FileSearchResponse(
        status="preview_only",
        query=request.query,
        scope=request.scope,
        searched=False,
        result_count=0,
        results=[],
        risk_level="safe",
        message=message,
        safety_notes=[
            "Only safe whitelisted folders will be searched in a future phase.",
            "File contents will not be read.",
            "Files will not be opened, moved, renamed, edited, or deleted.",
            "This phase does not access the filesystem.",
        ],
    )


def create_file_search_blocked_response(
    request: FileSearchRequest,
    reason: str,
) -> FileSearchResponse:
    return FileSearchResponse(
        status="blocked",
        query=request.query,
        scope=request.scope,
        risk_level="blocked",
        searched=False,
        result_count=0,
        results=[],
        message=reason,
        error=reason,
        safety_notes=[
            "The file search request was blocked for safety.",
            "No filesystem access occurred.",
        ],
    )

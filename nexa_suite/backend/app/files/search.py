"""Read-only metadata file search inside whitelisted safe directories."""

import datetime
import os
from pathlib import Path
from typing import Optional

from app.schemas.file_search import FileSearchRequest
from app.schemas.file_search import FileSearchResponse
from app.schemas.file_search import FileSearchResultItem
from app.schemas.file_search import create_file_search_blocked_response
from app.files.safe_directories import (
    get_directories_for_scope,
    contains_blocked_path_keyword,
    is_path_within_safe_directories,
)

MAX_RESULTS_LIMIT = 50
DEFAULT_MAX_RESULTS = 20

BLOCKED_SEARCH_TERMS: list[str] = [
    "delete",
    "remove",
    "move",
    "rename",
    "edit",
    "write",
    "overwrite",
    "format",
    "execute",
    "run",
    "open",
    "ডিলিট",
    "মুছে ফেল",
    "সরাও",
    "নাম বদলাও",
    "এডিট",
    "চালাও",
    "খোলো",
]


def normalize_file_query(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def normalize_extensions(extensions: Optional[list[str]]) -> set[str]:
    if not extensions:
        return set()
    result: set[str] = set()
    for ext in extensions:
        cleaned = ext.strip().lower().lstrip(".")
        if cleaned:
            result.add(cleaned)
    return result


def is_blocked_file_search_text(text: Optional[str]) -> bool:
    if not text:
        return False
    lower = text.strip().lower()
    for term in BLOCKED_SEARCH_TERMS:
        if term in lower:
            return True
    return False


def file_matches_query(path: Path, query: str, extensions: set[str]) -> bool:
    name_lower = path.name.lower()
    if query:
        if query not in name_lower:
            return False
    if extensions:
        if path.is_dir():
            return False
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in extensions:
            return False
    return True


def path_to_result_item(path: Path) -> FileSearchResultItem:
    try:
        stat = path.stat() if path.exists() else None
    except (OSError, Exception):
        stat = None

    suffix = path.suffix.lower().lstrip(".") if path.suffix else None

    modified_at: Optional[str] = None
    if stat is not None:
        try:
            ts = stat.st_mtime
            modified_at = datetime.datetime.fromtimestamp(
                ts, tz=datetime.timezone.utc
            ).isoformat()
        except Exception:
            modified_at = None

    return FileSearchResultItem(
        name=path.name,
        path=str(path),
        extension=suffix if suffix else None,
        size_bytes=stat.st_size if stat is not None else None,
        modified_at=modified_at,
        is_directory=path.is_dir() if path.exists() else False,
    )


def search_files_read_only(request: FileSearchRequest) -> FileSearchResponse:
    query = normalize_file_query(request.query)

    if is_blocked_file_search_text(request.original_text or request.query):
        return create_file_search_blocked_response(
            request, "File search request contains unsafe file operation terms."
        )

    if not query:
        return create_file_search_blocked_response(
            request, "File search query is empty."
        )

    allowed, directories, message = get_directories_for_scope(request.scope)
    if not allowed:
        return create_file_search_blocked_response(request, message)

    max_results = request.max_results or DEFAULT_MAX_RESULTS
    max_results = max(1, min(max_results, MAX_RESULTS_LIMIT))

    extensions = normalize_extensions(request.extensions)

    results: list[FileSearchResultItem] = []

    for directory in directories:
        if not directory.exists():
            continue
        try:
            for entry in directory.rglob("*"):
                try:
                    if entry.is_symlink():
                        continue
                except Exception:
                    continue

                path_str = str(entry)
                if contains_blocked_path_keyword(path_str):
                    continue
                if not is_path_within_safe_directories(entry):
                    continue
                if not file_matches_query(entry, query, extensions):
                    continue

                result_item = path_to_result_item(entry)
                results.append(result_item)

                if len(results) >= max_results:
                    break
        except Exception:
            continue
        if len(results) >= max_results:
            break

    return FileSearchResponse(
        status="completed",
        query=query,
        scope=request.scope,
        risk_level="safe",
        searched=True,
        result_count=len(results),
        results=results,
        message="Read-only file search completed.",
        safety_notes=[
            "Only whitelisted safe folders were searched.",
            "File contents were not read.",
            "Files were not opened, moved, renamed, edited, or deleted.",
        ],
    )

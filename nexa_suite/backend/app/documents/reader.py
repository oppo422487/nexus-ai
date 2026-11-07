"""Read-only document preview for Nexa AI.

Only PDF/TXT/MD files inside the safe directories (Desktop, Downloads,
Documents) can be previewed. Content is extracted as plain text with hard
caps. Files are never modified, moved, renamed, deleted, or executed.
"""

from __future__ import annotations

from pathlib import Path

from app.files.safe_directories import (
    contains_blocked_path_keyword,
    is_path_within_safe_directories,
)

ALLOWED_PREVIEW_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 5
MAX_PREVIEW_CHARS = 6000

SAFETY_NOTES = [
    "Document preview is read-only.",
    "Only PDF, TXT, and MD files in safe folders can be previewed.",
    "Files are never edited, moved, renamed, deleted, or executed.",
]


def _failed(path: str, reason: str) -> dict:
    return {
        "status": "blocked",
        "previewed": False,
        "path": path,
        "name": Path(path).name if path else "",
        "extension": None,
        "size_bytes": None,
        "page_count": None,
        "preview_text": "",
        "truncated": False,
        "message": reason,
        "safety_notes": SAFETY_NOTES,
        "error": reason,
    }


def _extract_pdf_text(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    chunks: list[str] = []
    total = 0
    for page in reader.pages[:MAX_PDF_PAGES]:
        text = page.extract_text() or ""
        chunks.append(text)
        total += len(text)
        if total >= MAX_PREVIEW_CHARS:
            break
    return "\n".join(chunks), page_count


def preview_document(path_text: str) -> dict:
    raw = (path_text or "").strip()
    if not raw:
        return _failed(raw, "Document path is empty.")

    if contains_blocked_path_keyword(raw):
        return _failed(raw, "Document path contains a blocked keyword.")

    try:
        path = Path(raw).resolve()
    except Exception:
        return _failed(raw, "Document path could not be resolved.")

    if not is_path_within_safe_directories(path):
        return _failed(raw, "Document is outside the safe folders (Desktop/Downloads/Documents).")
    if not path.exists() or not path.is_file():
        return _failed(raw, "Document was not found.")
    if path.suffix.lower() not in ALLOWED_PREVIEW_SUFFIXES:
        return _failed(raw, "Only PDF, TXT, and MD files can be previewed.")

    try:
        size = path.stat().st_size
    except OSError:
        return _failed(raw, "Document metadata could not be read.")
    if size > MAX_FILE_SIZE_BYTES:
        return _failed(raw, "Document is too large for preview (max 25 MB).")

    page_count: int | None = None
    try:
        if path.suffix.lower() == ".pdf":
            text, page_count = _extract_pdf_text(path)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return _failed(raw, f"Document text could not be extracted: {exc}")

    truncated = len(text) > MAX_PREVIEW_CHARS
    preview = text[:MAX_PREVIEW_CHARS].strip()

    return {
        "status": "completed",
        "previewed": True,
        "path": str(path),
        "name": path.name,
        "extension": path.suffix.lower().lstrip("."),
        "size_bytes": size,
        "page_count": page_count,
        "preview_text": preview,
        "truncated": truncated,
        "message": "Read-only document preview completed.",
        "safety_notes": SAFETY_NOTES,
        "error": None,
    }

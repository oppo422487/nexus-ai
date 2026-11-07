"""AssemblyAI-backed STT engine metadata and recorded-audio fallback."""

from __future__ import annotations

from pathlib import Path

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_UPLOAD_SUFFIXES = {".wav", ".webm", ".ogg", ".mp3", ".m4a", ".flac"}


def get_stt_engines_overview() -> dict:
    from app.voice.assemblyai import status
    current = status()
    return {
        "preferred_engine": "assemblyai_streaming",
        "engines": [
            {
                "name": "assemblyai_streaming",
                "label": "AssemblyAI Multilingual Streaming",
                "dependency_installed": True,
                "model_available": True,
                "ready": current["ready"],
                "message": "Uses AssemblyAI multilingual online recognition; no local model is required.",
            },
        ],
    }


def is_upload_suffix_allowed(filename: str | None) -> bool:
    if not filename:
        return False
    return Path(filename).suffix.lower() in ALLOWED_UPLOAD_SUFFIXES


def transcribe_audio_file(audio_path: str | Path, language: str | None = None) -> dict:
    from app.voice.assemblyai import transcribe_file
    return transcribe_file(Path(audio_path).read_bytes(), language)

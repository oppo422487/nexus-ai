"""faster-whisper STT engine for Nexa AI.

Local, offline transcription once the model is downloaded. The model file
is fetched on first use into backend/models/whisper. No microphone access
happens here — this module only transcribes audio files it is given.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from app.core.runtime_paths import models_dir

WHISPER_MODELS_DIR = models_dir() / "whisper"

# "small" is the smallest Whisper size with usable Bangla accuracy;
# override with NEXA_WHISPER_MODEL=tiny|base|small for low-end machines.
SUPPORTED_MODEL_SIZES = ("tiny", "base", "small")


def _resolve_model_size() -> str:
    requested = os.getenv("NEXA_WHISPER_MODEL", "small").strip().lower()
    return requested if requested in SUPPORTED_MODEL_SIZES else "small"


DEFAULT_MODEL_SIZE = _resolve_model_size()

_BANGLA_CHAR_RANGE = ("ঀ", "৿")

LOW_QUALITY_BANGLA_WARNING = (
    "Bangla transcription quality is low. Try small/medium model or clearer audio."
)


def _contains_bangla_script(text: str) -> bool:
    return any(_BANGLA_CHAR_RANGE[0] <= ch <= _BANGLA_CHAR_RANGE[1] for ch in text)

_model = None
_model_size_loaded: str | None = None
_model_lock = threading.Lock()


def check_whisper_dependency() -> tuple[bool, str]:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return (
            False,
            "faster-whisper is not installed. Install it with: pip install faster-whisper",
        )
    return True, "faster-whisper dependency is installed."


def is_whisper_model_downloaded(model_size: str | None = None) -> bool:
    size = model_size or DEFAULT_MODEL_SIZE
    marker = WHISPER_MODELS_DIR / f"models--Systran--faster-whisper-{size}"
    return marker.exists()


def get_whisper_readiness() -> dict:
    dep_ok, dep_msg = check_whisper_dependency()
    model_ok = is_whisper_model_downloaded()
    return {
        "engine": "faster_whisper",
        "model_size": DEFAULT_MODEL_SIZE,
        "dependency_installed": dep_ok,
        "dependency_message": dep_msg,
        "model_available": model_ok,
        "model_message": (
            "Whisper model is downloaded."
            if model_ok
            else "Whisper model is not downloaded yet. "
            "It downloads automatically on first transcription (internet required once)."
        ),
        "ready": dep_ok,
    }


def _get_model():
    """Lazy-load the Whisper model (downloads on first use)."""
    global _model, _model_size_loaded
    with _model_lock:
        if _model is not None and _model_size_loaded == DEFAULT_MODEL_SIZE:
            return _model
        from faster_whisper import WhisperModel

        WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        _model = WhisperModel(
            DEFAULT_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
            download_root=str(WHISPER_MODELS_DIR),
        )
        _model_size_loaded = DEFAULT_MODEL_SIZE
        return _model


def transcribe_file_with_whisper(
    audio_path: str | Path,
    language: str | None = None,
) -> dict:
    """Transcribe one audio file. Returns a plain result dict, never raises."""
    dep_ok, dep_msg = check_whisper_dependency()
    if not dep_ok:
        return {
            "status": "not_ready",
            "transcribed": False,
            "text": "",
            "language": None,
            "engine": "faster_whisper",
            "error": dep_msg,
        }

    path = Path(audio_path)
    if not path.exists():
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "language": None,
            "engine": "faster_whisper",
            "error": "Audio file was not found.",
        }

    try:
        model = _get_model()
        segments, info = model.transcribe(
            str(path),
            language=language,
            task="transcribe",
            condition_on_previous_text=False,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()

        detected_language = getattr(info, "language", None)
        warning: str | None = None
        wants_bangla = language == "bn" or (language is None and detected_language == "bn")
        if wants_bangla and text and not _contains_bangla_script(text):
            warning = LOW_QUALITY_BANGLA_WARNING

        return {
            "status": "completed",
            "transcribed": True,
            "text": text,
            "language": detected_language,
            "engine": "faster_whisper",
            "warning": warning,
            "error": None,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "transcribed": False,
            "text": "",
            "language": None,
            "engine": "faster_whisper",
            "error": f"Whisper transcription failed: {exc}",
        }

"""Voice API routes: STT status/readiness/engines/transcription and TTS."""

import tempfile
import asyncio
import re
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, Response
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
import httpx

from app.voice import assemblyai, cartesia

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.voice import VoiceSTTReadinessResponse
from app.schemas.voice import VoiceSTTStatusResponse
from app.schemas.voice import VoiceSTTTestTranscriptionResponse
from app.schemas.voice import VoiceSTTEngineInfo
from app.schemas.voice import VoiceSTTEnginesResponse
from app.schemas.voice import VoiceTranscriptionResponse
from app.schemas.voice import TTSVoiceInfo
from app.schemas.voice import TTSStatusResponse
from app.schemas.voice import TTSSpeakRequest
from app.schemas.voice import TTSSpeakResponse
from app.schemas.voice import EdgeTTSRequest
from app.voice.stt_engines import (
    MAX_UPLOAD_BYTES,
    get_stt_engines_overview,
    is_upload_suffix_allowed,
    transcribe_audio_file,
)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/stt/assemblyai/token")
async def assemblyai_streaming_token() -> dict:
    if not is_permission_enabled("voice_stt"):
        return {"ok": False, "message": permission_denied_message("voice_stt")}
    try:
        token = await assemblyai.create_streaming_token()
    except (RuntimeError, httpx.HTTPError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "token": token, "provider": "assemblyai", "model": "whisper-rt"}

EDGE_VOICES = [
    ("bn-BD-NabanitaNeural", "Bangla - Nabanita", ["bn-BD"]),
    ("bn-BD-PradeepNeural", "Bangla - Pradeep", ["bn-BD"]),
    ("en-US-AriaNeural", "English - Aria", ["en-US"]),
    ("en-US-GuyNeural", "English - Guy", ["en-US"]),
]


class CartesiaKeyRequest(BaseModel):
    api_key: str


class CartesiaVoiceRequest(BaseModel):
    language: str
    voice_id: str


class PreferredTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=800)
    language: str = "auto"
    edge_voice: str = "bn-BD-NabanitaNeural"
    rate: str = "+0%"


@router.get("/tts/cartesia/status")
def cartesia_status() -> dict:
    return cartesia.status()


@router.put("/tts/cartesia/key")
def cartesia_save_key(request: CartesiaKeyRequest) -> dict:
    try:
        cartesia.save_key(request.api_key)
    except (ValueError, RuntimeError, OSError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": "Cartesia key saved securely for this Windows user.", **cartesia.status()}


@router.delete("/tts/cartesia/key")
def cartesia_remove_key() -> dict:
    cartesia.remove_key()
    return {"ok": True, "message": "Cartesia key removed.", **cartesia.status()}


@router.get("/tts/cartesia/voices")
def cartesia_voices(language: str = "bn") -> dict:
    try:
        voices = cartesia.list_voices(language)
    except (ValueError, RuntimeError, httpx.HTTPError) as exc:
        return {"ok": False, "voices": [], "message": _cartesia_error(exc)}
    return {"ok": True, "voices": voices, "message": f"{len(voices)} voices available."}


@router.put("/tts/cartesia/voice")
def cartesia_set_voice(request: CartesiaVoiceRequest) -> dict:
    try:
        cartesia.set_voice(request.language, request.voice_id)
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": "Cartesia voice selected.", **cartesia.status()}


def _cartesia_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in {401, 403}:
            return "Cartesia rejected this key. Replace it in Settings."
        if code in {402, 429}:
            return "Cartesia credits or rate limit reached. Choose another account key in Settings."
        return f"Cartesia request failed (HTTP {code})."
    if isinstance(exc, httpx.HTTPError):
        return "Cartesia is unreachable. Check the network connection."
    return str(exc)


@router.post("/tts/audio")
def preferred_tts_audio(request: PreferredTTSRequest):
    if not is_permission_enabled("voice_tts"):
        denied = permission_denied_message("voice_tts")
        return TTSSpeakResponse(status="blocked", message=denied, error=denied)
    language = "bn" if request.language == "bn" or (request.language == "auto" and re.search(r"[\u0980-\u09ff]", request.text)) else "en"
    if cartesia.status()["configured"]:
        try:
            audio = cartesia.generate_audio(request.text.strip(), language)
            record_audit_event("voice_tts", "cartesia_audio", "completed", message=f"language={language}, chars={len(request.text)}")
            return Response(audio, media_type="audio/mpeg", headers={"X-TTS-Provider": "cartesia"})
        except (ValueError, RuntimeError, httpx.HTTPError) as exc:
            fallback_reason = _cartesia_error(exc)
    else:
        fallback_reason = "Cartesia key is not configured."
    if not is_permission_enabled("edge_tts"):
        return TTSSpeakResponse(status="failed", message=fallback_reason, error=fallback_reason)
    voice = request.edge_voice if request.edge_voice in {item[0] for item in EDGE_VOICES} else ("bn-BD-NabanitaNeural" if language == "bn" else "en-US-AriaNeural")
    fallback = edge_tts_audio(EdgeTTSRequest(text=request.text, voice=voice, rate=request.rate))
    if isinstance(fallback, FileResponse):
        fallback.headers["X-TTS-Provider"] = "edge-fallback"
        fallback.headers["X-TTS-Fallback-Reason"] = fallback_reason[:180]
    return fallback


def _edge_tts_available() -> bool:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    return True


@router.get("/stt/status", response_model=VoiceSTTStatusResponse)
def get_stt_status() -> VoiceSTTStatusResponse:
    return VoiceSTTStatusResponse(
        engine="assemblyai_whisper_streaming",
        mode="online_service",
        enabled=is_permission_enabled("voice_stt"),
        model_path="",
        sample_rate=0,
        language="auto",
        auto_start=True,
        execution_enabled=False,
        message="AssemblyAI multilingual streaming STT is selected with automatic language detection.",
    )


@router.get("/stt/readiness", response_model=VoiceSTTReadinessResponse)
def get_stt_readiness() -> VoiceSTTReadinessResponse:
    overview = get_stt_engines_overview()
    engine = overview["engines"][0]
    return VoiceSTTReadinessResponse(
        dependency_installed=engine["dependency_installed"],
        dependency_message=engine["message"],
        model_available=True,
        model_message="Online service selected; no local model is required.",
        ready=engine["ready"] and is_permission_enabled("voice_stt"),
        execution_enabled=False,
        message="AssemblyAI online STT supports Bangla and English and requires internet.",
    )


@router.get("/stt/test-transcription", response_model=VoiceSTTTestTranscriptionResponse)
def get_stt_test_transcription() -> VoiceSTTTestTranscriptionResponse:
    return VoiceSTTTestTranscriptionResponse(
        status="client_required",
        transcribed=False,
        text="",
        execution_enabled=False,
        message="Use the microphone test in the app for AssemblyAI streaming STT.",
        error=None,
    )


@router.get("/stt/engines", response_model=VoiceSTTEnginesResponse)
def get_stt_engines() -> VoiceSTTEnginesResponse:
    overview = get_stt_engines_overview()
    return VoiceSTTEnginesResponse(
        preferred_engine=overview["preferred_engine"],
        engines=[VoiceSTTEngineInfo(**engine) for engine in overview["engines"]],
    )


@router.post("/stt/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_uploaded_audio(
    audio: UploadFile = File(...),
    language: str | None = None,
) -> VoiceTranscriptionResponse:
    """Transcribe one microphone utterance detected by the frontend.

    The transcript is preview-only. It is never executed as a command —
    the frontend must route it through the normal preview/confirm flow.
    """
    if not is_permission_enabled("voice_stt"):
        denied = permission_denied_message("voice_stt")
        return VoiceTranscriptionResponse(
            status="blocked", message=denied, error=denied
        )

    if not is_upload_suffix_allowed(audio.filename):
        return VoiceTranscriptionResponse(
            status="blocked",
            message="Unsupported audio format.",
            error="Only wav/webm/ogg/mp3/m4a/flac uploads are accepted.",
        )

    data = await audio.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return VoiceTranscriptionResponse(
            status="blocked",
            message="Audio upload is too large.",
            error="Maximum upload size is 15 MB.",
        )
    if not data:
        return VoiceTranscriptionResponse(
            status="failed",
            message="Audio upload is empty.",
            error="No audio data received.",
        )

    suffix = Path(audio.filename or "audio.wav").suffix.lower() or ".wav"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        result = transcribe_audio_file(tmp_path, language=language)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    record_audit_event(
        source="voice_stt",
        intent="transcribe_push_to_talk",
        status=result["status"],
        message=f"engine={result.get('engine')}, chars={len(result.get('text', ''))}",
    )
    return VoiceTranscriptionResponse(
        status=result["status"],
        engine=result.get("engine", "none"),
        transcribed=result["transcribed"],
        text=result["text"],
        language=result.get("language"),
        message=(
            "Transcription completed. The transcript is preview-only and was not executed."
            if result["transcribed"]
            else (result.get("error") or "Transcription did not complete.")
        ),
        warning=result.get("warning"),
        error=result.get("error"),
    )


@router.get("/tts/status", response_model=TTSStatusResponse)
def tts_status() -> TTSStatusResponse:
    edge_available = _edge_tts_available()
    cartesia_configured = cartesia.status()["configured"]
    available = cartesia_configured or edge_available
    enabled = is_permission_enabled("voice_tts") and (cartesia_configured or is_permission_enabled("edge_tts"))
    return TTSStatusResponse(
        dependency_installed=edge_available,
        available=available,
        enabled=enabled,
        voices=[TTSVoiceInfo(id=voice_id, name=name, languages=languages) for voice_id, name, languages in EDGE_VOICES],
        message=(
            "Cartesia Sonic is primary; Edge neural TTS is fallback."
            if cartesia_configured and enabled
            else "Online Edge neural TTS fallback is ready. Add a Cartesia key in Settings."
            if available and enabled
            else "TTS is disabled in the Security Center."
            if available
            else "edge-tts is not installed."
        ),
        error=None if available else "Add a Cartesia key or install edge-tts.",
    )


@router.post("/tts/speak", response_model=TTSSpeakResponse)
def tts_speak(request: TTSSpeakRequest) -> TTSSpeakResponse:
    if not is_permission_enabled("voice_tts"):
        denied = permission_denied_message("voice_tts")
        return TTSSpeakResponse(status="blocked", message=denied, error=denied)
    return TTSSpeakResponse(
        status="audio_endpoint_required",
        spoken=False,
        message="Use /voice/tts/audio for Cartesia-primary audio with Edge fallback.",
        error=None,
    )


@router.get("/tts/edge/status")
def edge_tts_status() -> dict:
    return {"status": "ok", "available": _edge_tts_available(), "enabled": is_permission_enabled("edge_tts"), "voices": [voice[0] for voice in EDGE_VOICES]}


@router.post("/tts/edge/audio")
def edge_tts_audio(request: EdgeTTSRequest):
    if not is_permission_enabled("voice_tts") or not is_permission_enabled("edge_tts"):
        denied = permission_denied_message("edge_tts")
        return TTSSpeakResponse(status="blocked", message=denied, error=denied)
    if request.voice not in {voice[0] for voice in EDGE_VOICES}:
        return TTSSpeakResponse(status="blocked", message="Voice is not in the allowed Edge TTS list.", error="Unsupported voice.")
    if not re.fullmatch(r"[+-]\d{1,3}%", request.rate):
        return TTSSpeakResponse(status="blocked", message="Invalid speech rate.", error="Invalid rate.")
    try:
        import edge_tts
    except ImportError:
        return TTSSpeakResponse(status="not_ready", message="Install edge-tts first.", error="edge-tts is not installed.")
    text = request.text.strip()[:800]
    if not text:
        return TTSSpeakResponse(status="failed", message="Text is empty.", error="Text is empty.")
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = Path(tmp.name); tmp.close()
    try:
        asyncio.run(edge_tts.Communicate(text, request.voice, rate=request.rate).save(str(tmp_path)))
        record_audit_event("voice_tts", "edge_tts_audio", "completed", message=f"voice={request.voice}, chars={len(text)}")
        return FileResponse(tmp_path, media_type="audio/mpeg", filename="nexa-voice.mp3", background=BackgroundTask(tmp_path.unlink, missing_ok=True))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        return TTSSpeakResponse(status="failed", message="Edge TTS failed.", error=str(exc))

"""Cartesia TTS integration with Windows user-scoped encrypted key storage."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import re
import sys
from threading import Lock

import httpx

from app.core.runtime_paths import data_dir

API_VERSION = "2026-08-14"
MODEL_ID = "sonic-3.6"
API_BASE = "https://api.cartesia.ai"
KEY_FILE = data_dir() / "cartesia-key.dpapi"
SETTINGS_FILE = data_dir() / "cartesia-settings.json"
_LOCK = Lock()
_voice_cache: dict[tuple[str, str], str] = {}


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _protect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Secure Cartesia key storage requires Windows DPAPI.")
    source, _buffer = _blob(data)
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)):
        raise OSError("Could not encrypt Cartesia key.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _unprotect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Secure Cartesia key storage requires Windows DPAPI.")
    source, _buffer = _blob(data)
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)):
        raise OSError("Could not decrypt Cartesia key for this Windows user.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def get_key() -> str | None:
    if not KEY_FILE.exists():
        return None
    return _unprotect(KEY_FILE.read_bytes()).decode("utf-8")


def save_key(value: str) -> None:
    key = value.strip()
    if not re.fullmatch(r"sk_car_[A-Za-z0-9_-]{8,}", key):
        raise ValueError("Enter a valid Cartesia API key beginning with sk_car_.")
    encrypted = _protect(key.encode("utf-8"))
    with _LOCK:
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = KEY_FILE.with_suffix(".tmp")
        temp.write_bytes(encrypted)
        temp.replace(KEY_FILE)
        SETTINGS_FILE.unlink(missing_ok=True)
        _voice_cache.clear()


def remove_key() -> None:
    with _LOCK:
        KEY_FILE.unlink(missing_ok=True)
        _voice_cache.clear()


def _settings() -> dict[str, str]:
    try:
        value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def set_voice(language: str, voice_id: str) -> None:
    if language not in {"bn", "en"} or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", voice_id):
        raise ValueError("Invalid Cartesia voice selection.")
    with _LOCK:
        settings = _settings()
        settings[f"voice_{language}"] = voice_id
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = SETTINGS_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(settings), encoding="utf-8")
        temp.replace(SETTINGS_FILE)


def status() -> dict:
    settings = _settings()
    return {
        "configured": KEY_FILE.exists(),
        "provider": "cartesia" if KEY_FILE.exists() else "edge_fallback",
        "model": MODEL_ID,
        "voice_bn": settings.get("voice_bn", ""),
        "voice_en": settings.get("voice_en", ""),
        "key_masked": "••••••••" if KEY_FILE.exists() else "",
    }


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Cartesia-Version": API_VERSION}


def list_voices(language: str) -> list[dict[str, str]]:
    if language not in {"bn", "en"}:
        raise ValueError("Language must be bn or en.")
    key = get_key()
    if not key:
        raise RuntimeError("Cartesia API key is not configured.")
    response = httpx.get(f"{API_BASE}/voices", headers=_headers(key), params={"language": language, "limit": 100}, timeout=15)
    response.raise_for_status()
    rows = response.json().get("data", [])
    return [{"id": str(row["id"]), "name": str(row.get("name") or "Voice")} for row in rows if isinstance(row, dict) and row.get("id")]


def generate_audio(text: str, language: str) -> bytes:
    key = get_key()
    if not key:
        raise RuntimeError("Cartesia API key is not configured.")
    if language not in {"bn", "en"}:
        raise ValueError("Language must be bn or en.")
    voice_id = _settings().get(f"voice_{language}")
    if not voice_id:
        cache_key = (key, language)
        voice_id = _voice_cache.get(cache_key)
        if not voice_id:
            voices = list_voices(language)
            if not voices:
                raise RuntimeError(f"No Cartesia {language} voice found. Choose a voice in Settings.")
            voice_id = voices[0]["id"]
            _voice_cache[cache_key] = voice_id
    payload = {
        "model_id": MODEL_ID,
        "transcript": text,
        "voice": voice_id,
        "output_format": {"container": "mp3", "bit_rate": 128000, "sample_rate": 44100},
        "language": language,
    }
    response = httpx.post(f"{API_BASE}/tts/bytes", headers=_headers(key), json=payload, timeout=30)
    response.raise_for_status()
    if not response.content:
        raise RuntimeError("Cartesia returned empty audio.")
    return response.content

"""AssemblyAI Universal Streaming authentication and readiness helpers."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

TOKEN_URL = "https://streaming.assemblyai.com/v3/token"


def status() -> dict[str, Any]:
    configured = bool(os.getenv("ASSEMBLYAI_API_KEY", "").strip())
    return {
        "ready": configured,
        "dependency_installed": True,
        "configured": configured,
        "internet_required": True,
        "provider": "assemblyai",
        "model": "whisper-rt",
        "action": "Ready when online." if configured else "Add ASSEMBLYAI_API_KEY to the backend environment.",
    }


async def create_streaming_token() -> str:
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AssemblyAI API key is not configured.")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            TOKEN_URL,
            params={"expires_in_seconds": 60},
            headers={"Authorization": api_key},
        )
    if response.status_code in {401, 403}:
        raise RuntimeError("AssemblyAI rejected the API key.")
    if response.status_code in {402, 429}:
        raise RuntimeError("AssemblyAI credits or rate limit have been reached.")
    response.raise_for_status()
    token = str(response.json().get("token", "")).strip()
    if not token:
        raise RuntimeError("AssemblyAI did not return a streaming token.")
    return token


def transcribe_file(data: bytes, language: str | None = None) -> dict[str, Any]:
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    selected = "bn" if str(language or "").lower().startswith("bn") else "en"
    if not api_key:
        return {"status": "not_ready", "transcribed": False, "text": "", "language": selected, "engine": "assemblyai", "error": "AssemblyAI API key is not configured."}
    headers = {"Authorization": api_key}
    try:
        with httpx.Client(timeout=30.0) as client:
            uploaded = client.post("https://api.assemblyai.com/v2/upload", headers=headers, content=data)
            uploaded.raise_for_status()
            submitted = client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers=headers,
                json={
                    "audio_url": uploaded.json()["upload_url"],
                    "speech_models": ["universal-3-pro", "universal-2"],
                    "language_code": selected,
                },
            )
            submitted.raise_for_status()
            transcript_id = submitted.json()["id"]
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                result = client.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
                result.raise_for_status()
                payload = result.json()
                if payload.get("status") == "completed":
                    text = str(payload.get("text") or "").strip()
                    return {"status": "completed", "transcribed": bool(text), "text": text, "language": payload.get("language_code") or selected, "engine": "assemblyai", "error": None}
                if payload.get("status") == "error":
                    return {"status": "failed", "transcribed": False, "text": "", "language": selected, "engine": "assemblyai", "error": str(payload.get("error") or "AssemblyAI transcription failed.")}
                time.sleep(0.6)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return {"status": "failed", "transcribed": False, "text": "", "language": selected, "engine": "assemblyai", "error": f"AssemblyAI request failed: {exc}"}
    return {"status": "failed", "transcribed": False, "text": "", "language": selected, "engine": "assemblyai", "error": "AssemblyAI transcription timed out."}

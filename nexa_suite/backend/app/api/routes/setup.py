"""Read-only runtime readiness checks for optional desktop capabilities."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.runtime_paths import env_file

router = APIRouter(prefix="/setup", tags=["setup"])


class HuggingFaceConfigurationRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=512)
    user_confirmed: bool = False


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _chrome_available() -> bool:
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    return any(candidate and Path(candidate).is_file() for candidate in candidates)


@router.get("/readiness")
def setup_readiness() -> dict:
    from app.voice.assemblyai import status as assemblyai_status
    image_dependency = _installed("huggingface_hub") and _installed("PIL")
    edge_dependency = _installed("edge_tts")
    youtube_dependency = _installed("selenium")
    hf_configured = bool((os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or "").strip())
    capabilities = {
        "assemblyai_streaming_stt": assemblyai_status(),
        "image_generation": {
            "ready": image_dependency and hf_configured,
            "dependency_installed": image_dependency,
            "configured": hf_configured,
            "internet_required": True,
            "action": "Add HUGGINGFACE_API_KEY to the local .env file." if not hf_configured else "Ready when online.",
        },
        "edge_tts": {
            "ready": edge_dependency,
            "dependency_installed": edge_dependency,
            "configured": True,
            "internet_required": True,
            "action": "Ready when online." if edge_dependency else "Install backend requirements.",
        },
        "advanced_youtube": {
            "ready": youtube_dependency and _chrome_available(),
            "dependency_installed": youtube_dependency,
            "configured": _chrome_available(),
            "internet_required": True,
            "action": "Ready when online." if youtube_dependency and _chrome_available() else "Install Google Chrome and backend requirements.",
        },
    }
    return {
        "status": "ok",
        "packaged_backend": bool(getattr(sys, "frozen", False)),
        "python": sys.version.split()[0],
        "capabilities": capabilities,
        "all_dependencies_ready": all(item["dependency_installed"] for item in capabilities.values()),
    }


@router.post("/huggingface")
def configure_huggingface(request: HuggingFaceConfigurationRequest) -> dict:
    if not request.user_confirmed:
        return {"status": "confirmation_required", "configured": False, "message": "Saving a provider token requires confirmation."}
    token = request.token.strip()
    if not token or any(character in token for character in "\r\n\t ="):
        return {"status": "blocked", "configured": False, "message": "The token format is invalid."}
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    updated: list[str] = []
    replaced = False
    for line in existing:
        if line.strip().startswith("HUGGINGFACE_API_KEY="):
            updated.append(f"HUGGINGFACE_API_KEY={token}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(f"HUGGINGFACE_API_KEY={token}")
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    os.environ["HUGGINGFACE_API_KEY"] = token
    return {"status": "completed", "configured": True, "message": "Hugging Face token saved in Nexa's local configuration."}

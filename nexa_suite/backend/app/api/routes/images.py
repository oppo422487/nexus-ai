"""Optional image-generation API backed by Hugging Face Inference Providers."""

from __future__ import annotations

import os
import re
import uuid
import threading
import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.images import ImageGenerationRequest, ImageGenerationResponse
from app.core.runtime_paths import data_dir

try:
    from huggingface_hub import InferenceClient

    _HF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    InferenceClient = None  # type: ignore[assignment]
    _HF_AVAILABLE = False

router = APIRouter(prefix="/images", tags=["images"])

GENERATED_DIR = data_dir() / "generated_images"
DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _model() -> str:
    return os.getenv("HUGGINGFACE_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _token() -> str:
    return (os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or "").strip()


@router.get("/health")
def image_generation_health() -> dict:
    enabled = is_permission_enabled("image_generation")
    return {
        "status": "ok",
        "module": "image_generation",
        "available": _HF_AVAILABLE and bool(_token()),
        "enabled": enabled,
        "model": _model(),
        "message": "Ready." if _HF_AVAILABLE and _token() and enabled else "Enable permission and configure HUGGINGFACE_API_KEY.",
    }


@router.post("/generate", response_model=ImageGenerationResponse)
def generate_image(request: ImageGenerationRequest) -> ImageGenerationResponse:
    if not is_permission_enabled("image_generation"):
        message = permission_denied_message("image_generation")
        return ImageGenerationResponse(status="blocked", prompt=request.prompt, message=message, error=message)
    if not request.user_confirmed:
        message = "Image generation requires explicit confirmation."
        return ImageGenerationResponse(status="confirmation_required", prompt=request.prompt, message=message, error=message)
    if not _HF_AVAILABLE:
        message = "Install huggingface_hub and Pillow to enable image generation."
        return ImageGenerationResponse(status="unavailable", prompt=request.prompt, message=message, error=message)
    token = _token()
    if not token:
        message = "Configure HUGGINGFACE_API_KEY in backend/.env first."
        return ImageGenerationResponse(status="setup_required", prompt=request.prompt, message=message, error=message)

    model = _model()
    try:
        client = InferenceClient(model=model, token=token)
        image = client.text_to_image(
            request.prompt,
            width=request.width,
            height=request.height,
        )
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        image_id = uuid.uuid4().hex
        output = GENERATED_DIR / f"{image_id}.png"
        image.save(output, format="PNG")
        message = "Image generated and saved in Nexa's local generated-images folder."
        record_audit_event("images", "image_generate", "completed", "confirmed", image_id, request.prompt)
        return ImageGenerationResponse(
            status="completed",
            generated=True,
            prompt=request.prompt,
            image_id=image_id,
            image_url=f"/api/images/{image_id}",
            model=model,
            message=message,
        )
    except Exception as exc:
        message = f"Image generation failed: {exc}"
        record_audit_event("images", "image_generate", "failed", "provider", model, message)
        return ImageGenerationResponse(status="failed", prompt=request.prompt, model=model, message=message, error=message)


def _run_image_job(job_id: str, request: ImageGenerationRequest) -> None:
    with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = generate_image(request)
    with _jobs_lock:
        _jobs[job_id].update({
            "status": "completed" if result.generated else "failed",
            "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "image_id": result.image_id,
            "image_url": result.image_url,
            "message": result.message,
            "error": result.error,
        })


@router.post("/queue")
def queue_image(request: ImageGenerationRequest) -> dict:
    if not request.user_confirmed:
        return {"status": "confirmation_required", "queued": False, "message": "Image generation requires explicit confirmation."}
    if not is_permission_enabled("image_generation"):
        return {"status": "blocked", "queued": False, "message": permission_denied_message("image_generation")}
    job_id = uuid.uuid4().hex
    job = {"id": job_id, "status": "queued", "prompt": request.prompt, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "image_url": None, "error": None}
    with _jobs_lock: _jobs[job_id] = job
    worker = threading.Thread(target=_run_image_job, args=(job_id, request), daemon=True)
    worker.start()
    return {"status": "queued", "queued": True, "job": job}


@router.get("/jobs")
def image_jobs() -> dict:
    if not is_permission_enabled("image_generation"):
        return {"status": "blocked", "jobs": [], "message": permission_denied_message("image_generation")}
    with _jobs_lock:
        jobs = sorted((dict(job) for job in _jobs.values()), key=lambda row: row["created_at"], reverse=True)[:50]
    return {"status": "ok", "jobs": jobs}


@router.get("/history")
def image_history() -> dict:
    if not is_permission_enabled("image_generation"):
        return {"status": "blocked", "images": [], "message": permission_denied_message("image_generation")}
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    images = [{"id": path.stem, "image_url": f"/api/images/{path.stem}", "size": path.stat().st_size, "created_at": datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat()} for path in sorted(GENERATED_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]]
    return {"status": "ok", "images": images}


@router.get("/{image_id}")
def get_generated_image(image_id: str) -> FileResponse:
    if not re.fullmatch(r"[a-f0-9]{32}", image_id):
        raise HTTPException(status_code=404, detail="Image not found.")
    if not is_permission_enabled("image_generation"):
        raise HTTPException(status_code=403, detail=permission_denied_message("image_generation"))
    path = GENERATED_DIR / f"{image_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path, media_type="image/png", filename=f"nexa-{image_id[:8]}.png")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.commands import router as commands_router
from app.api.routes.audit import router as audit_router
from app.api.routes.database import router as database_router
from app.api.routes.health import router as health_router
from app.api.routes.actions import router as actions_router
from app.api.routes.voice import router as voice_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.web import router as web_router
from app.api.routes.documents import router as documents_router
from app.api.routes.reminders import router as reminders_router
from app.api.routes.chat import router as chat_router
from app.api.routes.contacts import router as contacts_router
from app.api.routes.youtube import router as youtube_router
from app.api.routes.images import router as images_router
from app.api.routes.system_controls import router as system_controls_router
from app.api.routes.content import router as content_router
from app.api.routes.setup import router as setup_router
from app.api.routes.productivity import router as productivity_router
from app.api.routes.email import router as email_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5178",
        "http://localhost:5178",
        "null",  # Electron production renderer loaded from file://
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-TTS-Provider", "X-TTS-Fallback-Reason"],
)

app.include_router(health_router, prefix="/api")
app.include_router(commands_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(database_router, prefix="/api")
app.include_router(actions_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(permissions_router, prefix="/api")
app.include_router(web_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(reminders_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(youtube_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(system_controls_router, prefix="/api")
app.include_router(content_router, prefix="/api")
app.include_router(setup_router, prefix="/api")
app.include_router(productivity_router, prefix="/api")
app.include_router(email_router, prefix="/api")
from app.api.routes.engine import router as engine_router
app.include_router(engine_router, prefix="/api")


@app.get("/api/nexa-integration")
def nexa_integration_identity() -> dict:
    return {"product": "nexa-ai-mark-plus", "version": 1}


# Serve the companion interface under the same local origin as the APIs.
# Existing assistant routes remain independent of this optional build.
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# backend/app/main.py -> backend -> nexa_suite -> frontend
_suite_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _suite_dist.is_dir():
    app.mount("/suite", StaticFiles(directory=str(_suite_dist), html=True), name="nexa-suite")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "status": "running",
        "version": settings.app_version,
        "environment": settings.app_env,
    }

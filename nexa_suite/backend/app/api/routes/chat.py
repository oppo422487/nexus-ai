"""API routes for real safe chat answers."""

from fastapi import APIRouter

from app.assistant.pipeline import run_chat_pipeline
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/health")
def chat_health() -> dict:
    return {
        "status": "ok",
        "module": "chat",
        "execution_enabled": False,
        "providers": ["Open-Meteo", "DuckDuckGo Instant Answer", "Wikipedia"],
        "message": "Chat answers run inside Nexa and never execute actions.",
    }


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(request: ChatMessageRequest) -> ChatMessageResponse:
    return run_chat_pipeline(request)

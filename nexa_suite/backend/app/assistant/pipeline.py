"""Stable entry point for the assistant pipeline.

The FastAPI route should continue to call the existing chat handler for now.
This module defines the merge-ready boundary where normalize -> safety ->
classify -> route -> execute -> compose will live as more logic is extracted.
"""

from __future__ import annotations

from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.memory.context_store import remember_turn


def run_chat_pipeline(request: ChatMessageRequest) -> ChatMessageResponse:
    from app.chat.service import handle_chat_message, set_preferred_reply_language, reset_preferred_reply_language, enforce_reply_language

    remember_turn(
        "user",
        request.message,
        language_style=None,
        address_style=request.address_style,
    )
    token = set_preferred_reply_language(request.message, request.preferred_language)
    try:
        response = enforce_reply_language(handle_chat_message(request), request.message, request.address_style)
    finally:
        reset_preferred_reply_language(token)
    remember_turn(
        "assistant",
        response.answer,
        intent=response.intent,
        route=response.source_type,
        topic=response.intent,
        assistant_question=response.pending_task.prompt if response.pending_task else None,
        address_style=request.address_style,
    )
    return response

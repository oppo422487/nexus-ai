"""API routes for the safe web answer service."""

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.web import WebAnswerRequest, WebAnswerResponse
from app.web import answer_question, ALLOWED_HOSTS

router = APIRouter(prefix="/web", tags=["web"])


@router.get("/health")
def web_health() -> dict:
    return {
        "status": "ok",
        "module": "web_answers",
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "enabled": is_permission_enabled("web_answers"),
        "execution_enabled": False,
    }


@router.post("/answer", response_model=WebAnswerResponse)
def web_answer(request: WebAnswerRequest) -> WebAnswerResponse:
    if not is_permission_enabled("web_answers"):
        return WebAnswerResponse(
            status="blocked",
            answered=False,
            question=request.question,
            message=permission_denied_message("web_answers"),
            error=permission_denied_message("web_answers"),
        )

    result = answer_question(request.question)
    record_audit_event(
        source="web_answers",
        intent="web_question",
        status=result["status"],
        target=result["question"][:120],
        message=(result.get("source") or ""),
    )
    return WebAnswerResponse(
        status=result["status"],
        answered=result["answered"],
        question=result["question"],
        answer=result["answer"],
        source=result["source"],
        source_url=result["source_url"],
        message=(
            "Answer found from a safe public source."
            if result["answered"]
            else (result.get("error") or "No answer found.")
        ),
        error=result.get("error"),
    )

"""Safe email preview, status and confirmed-send routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.audit.event_log import record_audit_event
from app.email import email_status, send_email

router = APIRouter(prefix="/email", tags=["email"])


class EmailRequest(BaseModel):
    recipient: str = Field(..., min_length=3, max_length=320)
    subject: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=20_000)
    user_confirmed: bool = False


@router.get("/status")
def get_email_status() -> dict:
    return email_status()


@router.post("/preview")
def preview_email(request: EmailRequest) -> dict:
    return {"status": "confirmation_required", "sent": False, "confirmation_required": True, "recipient": request.recipient.strip(), "subject": request.subject.strip(), "body": request.body.strip(), "message": "Review the email and confirm before sending."}


@router.post("/send")
def send_confirmed_email(request: EmailRequest) -> dict:
    if not request.user_confirmed:
        return {"status": "confirmation_required", "sent": False, "message": "Explicit confirmation is required before sending email."}
    try:
        result = send_email(recipient=request.recipient, subject=request.subject, body=request.body)
        record_audit_event("email", "email_send", "completed", target=request.recipient, message=f'Subject: {request.subject[:100]}')
        return {"status": "completed", "message": "Email sent successfully.", **result}
    except (ValueError, RuntimeError) as exc:
        record_audit_event("email", "email_send", "blocked", target=request.recipient, message=str(exc))
        return {"status": "blocked", "sent": False, "message": str(exc)}
    except Exception:
        record_audit_event("email", "email_send", "failed", target=request.recipient, message="Provider delivery failed.")
        return {"status": "failed", "sent": False, "message": "Email provider rejected the delivery. Check credentials and SMTP settings."}

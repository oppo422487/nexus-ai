"""Confirmation-gated SMTP email delivery for Nexa."""

from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

EMAIL_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


def _configuration() -> dict[str, Any]:
    provider = os.getenv("NEXA_EMAIL_PROVIDER", "gmail").strip().lower()
    defaults = {
        "gmail": ("smtp.gmail.com", 465, True),
        "outlook": ("smtp.office365.com", 587, False),
        "custom": ("", 587, False),
    }
    host, port, use_ssl = defaults.get(provider, defaults["custom"])
    host = os.getenv("NEXA_SMTP_HOST", host).strip()
    port = int(os.getenv("NEXA_SMTP_PORT", str(port)).strip())
    security = os.getenv("NEXA_SMTP_SECURITY", "ssl" if use_ssl else "starttls").strip().lower()
    address = os.getenv("NEXA_EMAIL_ADDRESS", "").strip()
    password = os.getenv("NEXA_EMAIL_APP_PASSWORD", "").strip()
    sender_name = os.getenv("NEXA_EMAIL_SENDER_NAME", "Nexa AI").strip()
    return {"provider": provider, "host": host, "port": port, "security": security, "address": address, "password": password, "sender_name": sender_name}


def email_status() -> dict[str, Any]:
    config = _configuration()
    configured = bool(config["host"] and EMAIL_RE.fullmatch(config["address"]) and config["password"])
    return {
        "status": "ok",
        "provider": config["provider"],
        "sender": config["address"] if configured else "",
        "configured": configured,
        "confirmation_required": True,
        "message": "Email sending is ready." if configured else "Configure NEXA_EMAIL_ADDRESS and NEXA_EMAIL_APP_PASSWORD in backend/.env.",
    }


def _clean_header(value: str, field: str, limit: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > limit or "\r" in cleaned or "\n" in cleaned:
        raise ValueError(f"Invalid {field}.")
    return cleaned


def send_email(*, recipient: str, subject: str, body: str) -> dict[str, Any]:
    config = _configuration()
    if not email_status()["configured"]:
        raise RuntimeError("Email provider is not configured.")
    recipient = _clean_header(recipient, "recipient", 320)
    subject = _clean_header(subject, "subject", 300)
    body = body.strip()
    if not EMAIL_RE.fullmatch(recipient):
        raise ValueError("Recipient email address is invalid.")
    if not body or len(body) > 20_000:
        raise ValueError("Email body must contain 1 to 20,000 characters.")

    message = EmailMessage()
    message["From"] = f'{config["sender_name"]} <{config["address"]}>'
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    context = ssl.create_default_context()
    if config["security"] == "ssl":
        with smtplib.SMTP_SSL(config["host"], config["port"], timeout=25, context=context) as smtp:
            smtp.login(config["address"], config["password"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(config["host"], config["port"], timeout=25) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(config["address"], config["password"])
            smtp.send_message(message)
    return {"sent": True, "provider": config["provider"], "recipient": recipient, "subject": subject}

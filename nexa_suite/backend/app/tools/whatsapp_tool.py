"""WhatsApp draft URL helper."""

from __future__ import annotations

import urllib.parse


def whatsapp_draft_urls(phone: str, text: str, preference: str = "auto") -> list[str]:
    encoded = urllib.parse.quote_plus(text)
    app_url = f"whatsapp://send?phone={phone}&text={encoded}"
    web_url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"
    wa_url = f"https://wa.me/{phone}?text={encoded}"
    if preference == "app":
        return [app_url, wa_url, web_url]
    if preference == "web":
        return [web_url]
    if preference == "wa_me":
        return [wa_url]
    return [app_url, wa_url, web_url]


"""Safe website whitelist and URL normalizer."""

from __future__ import annotations

import re

ALLOWED_WEBSITES: dict[str, str] = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "github": "https://github.com",
    "facebook": "https://www.facebook.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "stackoverflow": "https://stackoverflow.com",
    "spotify": "https://open.spotify.com",
    "discord": "https://discord.com/app",
    "telegram": "https://web.telegram.org",
    "notion": "https://www.notion.so",
}

ALLOWED_DOMAINS: dict[str, str] = {
    "google.com": "https://www.google.com",
    "www.google.com": "https://www.google.com",
    "youtube.com": "https://www.youtube.com",
    "www.youtube.com": "https://www.youtube.com",
    "web.whatsapp.com": "https://web.whatsapp.com",
    "whatsapp.com": "https://web.whatsapp.com",
    "www.whatsapp.com": "https://web.whatsapp.com",
    "wa.me": "https://wa.me",
    "github.com": "https://github.com",
    "www.github.com": "https://github.com",
    "facebook.com": "https://www.facebook.com",
    "www.facebook.com": "https://www.facebook.com",
    "mail.google.com": "https://mail.google.com",
    "chatgpt.com": "https://chatgpt.com",
    "www.chatgpt.com": "https://chatgpt.com",
    "stackoverflow.com": "https://stackoverflow.com",
    "www.stackoverflow.com": "https://stackoverflow.com",
    "open.spotify.com": "https://open.spotify.com",
    "discord.com": "https://discord.com/app",
    "www.discord.com": "https://discord.com/app",
    "web.telegram.org": "https://web.telegram.org",
    "notion.so": "https://www.notion.so",
    "www.notion.so": "https://www.notion.so",
}

BLOCKED_URL_SCHEMES: list[str] = [
    "javascript:",
    "file:",
    "data:",
    "powershell:",
    "cmd:",
    "shell:",
]

WHATSAPP_APP_RE = re.compile(r"^whatsapp://send\?phone=\d{10,16}&text=[^#]+$", re.IGNORECASE)
WHATSAPP_WEB_RE = re.compile(r"^https://web\.whatsapp\.com/send\?phone=\d{10,16}&text=[^#]+$", re.IGNORECASE)
WHATSAPP_WA_ME_RE = re.compile(r"^https://wa\.me/\d{10,16}\?text=[^#]+$", re.IGNORECASE)

BANGLA_ALIASES: dict[str, str] = {
    "ইউটিউব": "youtube",
    "গুগল": "google",
    "ফেসবুক": "facebook",
    "জিমেইল": "gmail",
    "গিটহাব": "github",
    "চ্যাটজিপিটি": "chatgpt",
    "স্পটিফাই": "spotify",
    "ডিসকর্ড": "discord",
    "টেলিগ্রাম": "telegram",
    "নোশন": "notion",
}

PREFIXES_TO_STRIP: list[str] = [
    "open koro",
    "open",
    "website",
    "site",
    "খুলুন",
    "খুলো",
    "খোলো",
]

COMMAND_PHRASES: tuple[str, ...] = (
    "open koro",
    "open",
    "website",
    "site",
    "খুলুন",
    "খুলো",
    "খোলো",
    "চালাও",
)


def normalize_website_key(value: str | None) -> str:
    if value is None:
        return ""

    key = value.strip().lower()

    for prefix in PREFIXES_TO_STRIP:
        if key.startswith(prefix):
            suffix = key[len(prefix) :].strip()
            if not suffix:
                return ""
            key = suffix

    key = " ".join(key.split())

    key = key.replace(". ", ".").replace(" .", ".")

    for raw, canonical in BANGLA_ALIASES.items():
        if raw in key:
            key = key.replace(raw, canonical)

    for phrase in COMMAND_PHRASES:
        key = re.sub(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", " ", key)
    key = " ".join(key.split())

    if key == "you tube":
        key = "youtube"

    return key


def is_blocked_url(value: str | None) -> bool:
    if not value:
        return True
    trimmed = value.strip().lower()
    for scheme in BLOCKED_URL_SCHEMES:
        if trimmed.startswith(scheme):
            return True
    return False


def get_allowed_website_url(
    value: str | None,
) -> tuple[bool, str | None, str]:
    if is_blocked_url(value) or not value:
        return (False, None, "Website target is empty or blocked.")

    trimmed = value.strip()
    lowered = trimmed.lower()
    if lowered.startswith("https://www.youtube.com/results?search_query="):
        return (True, trimmed, "YouTube search URL is allowed.")
    if WHATSAPP_APP_RE.match(trimmed):
        return (True, trimmed, "WhatsApp app draft URL is allowed.")
    if WHATSAPP_WEB_RE.match(trimmed):
        return (True, trimmed, "WhatsApp Web draft URL is allowed.")
    if WHATSAPP_WA_ME_RE.match(trimmed):
        return (True, trimmed, "WhatsApp draft URL is allowed.")
    if lowered.startswith("https://web.whatsapp.com"):
        return (True, trimmed, "WhatsApp Web URL is allowed.")
    if lowered.startswith("https://wa.me/?text="):
        return (True, trimmed, "WhatsApp draft URL is allowed.")
    if lowered.startswith("https://wa.me/") and "?text=" in lowered:
        return (True, trimmed, "WhatsApp draft URL is allowed.")

    # Trusted skills pass canonical HTTPS URLs, while manual actions often pass
    # a short key such as "youtube". Accept the exact canonical values through
    # the same whitelist instead of treating them as unknown keys.
    canonical_urls = {url.lower().rstrip("/"): url for url in ALLOWED_WEBSITES.values()}
    canonical = canonical_urls.get(lowered.rstrip("/"))
    if canonical:
        return (True, canonical, "Website is allowed.")

    key = normalize_website_key(value)

    if key in ALLOWED_WEBSITES:
        return (True, ALLOWED_WEBSITES[key], "Website is allowed.")

    if key in ALLOWED_DOMAINS:
        return (True, ALLOWED_DOMAINS[key], "Website is allowed.")

    return (False, None, "Website is not in the allowed whitelist.")


def list_allowed_websites() -> list[dict[str, str]]:
    return [{"key": k, "url": v} for k, v in ALLOWED_WEBSITES.items()]

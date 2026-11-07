"""Text normalization helpers for Bangla, Banglish, and English NLU."""

from __future__ import annotations

import re
import unicodedata

BANGLA_RE = re.compile(r"[\u0980-\u09ff]")


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def compact_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9\u0980-\u09ff]+", " ", normalize_text(value)).strip()


def has_bangla(value: str | None) -> bool:
    return bool(BANGLA_RE.search(value or ""))


def has_phrase_or_token(text: str, keywords: set[str]) -> bool:
    for keyword in keywords:
        if " " in keyword:
            if keyword in text:
                return True
        elif re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
            return True
    return False


def token_set(text: str) -> set[str]:
    return set(compact_text(text).split())


def detect_language_style(raw_text: str, normalized_text: str | None = None) -> str:
    text = normalized_text or normalize_text(raw_text)
    bangla = has_bangla(raw_text)
    banglish_tokens = {
        "ami",
        "amar",
        "apnar",
        "tumi",
        "tomar",
        "ki",
        "koro",
        "korteso",
        "kemon",
        "aso",
        "acho",
        "bolo",
        "dao",
        "lagbe",
        "cai",
        "chai",
        "banabo",
        "banao",
        "gaan",
        "chalao",
        "pore",
        "call",
    }
    english_tokens = {
        "what",
        "who",
        "how",
        "create",
        "build",
        "search",
        "news",
        "current",
        "latest",
        "calculator",
        "computer",
        "profile",
        "message",
    }
    tokens = token_set(text)
    has_banglish = bool(tokens & banglish_tokens)
    has_english = bool(tokens & english_tokens)
    if bangla and (has_banglish or has_english):
        return "mixed"
    if bangla:
        return "bangla"
    if has_banglish and has_english:
        return "mixed"
    if has_banglish:
        return "banglish"
    return "english"


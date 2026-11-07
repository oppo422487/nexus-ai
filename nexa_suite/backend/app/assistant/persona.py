"""Persona and address-style helpers for Nexa AI."""

from __future__ import annotations


VALID_ADDRESS_STYLES = {"boss", "sir", "vai", "neutral"}


def normalize_address_style(style: str | None) -> str:
    normalized = " ".join((style or "Boss").strip().lower().split())
    if normalized in {"neutral", "none", "no title"}:
        return "neutral"
    if normalized in {"sir"}:
        return "sir"
    if normalized in {"vai", "bhai"}:
        return "vai"
    return "boss"


def address_label(style: str | None, language_style: str = "mixed") -> str:
    normalized = normalize_address_style(style)
    if normalized == "neutral":
        return ""
    if normalized == "sir":
        return "স্যার" if language_style == "bangla" else "Sir"
    if normalized == "vai":
        return "ভাই" if language_style == "bangla" else "Vai"
    return "বস" if language_style == "bangla" else "Boss"


def prepend_address(text: str, style: str | None, language_style: str = "mixed") -> str:
    label = address_label(style, language_style)
    return f"{label}, {text}" if label else text

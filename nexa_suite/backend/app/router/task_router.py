"""Task router facade."""

from __future__ import annotations

from app.nlu.classifier import NLUClassification, classify


def route_task(message: str) -> NLUClassification:
    return classify(message)

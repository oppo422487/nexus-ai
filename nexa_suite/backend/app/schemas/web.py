"""Schemas for the safe web answer service."""

from pydantic import BaseModel


class WebAnswerRequest(BaseModel):
    question: str


class WebAnswerResponse(BaseModel):
    status: str
    module: str = "web_answers"
    answered: bool = False
    question: str = ""
    answer: str = ""
    source: str | None = None
    source_url: str | None = None
    execution_enabled: bool = False
    message: str = ""
    error: str | None = None

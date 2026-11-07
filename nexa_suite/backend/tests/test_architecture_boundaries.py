from __future__ import annotations

from app.assistant.pipeline import run_chat_pipeline
from app.assistant.response_composer import compose
from app.nlu.classifier import classify
from app.router.task_router import route_task
from app.tools.calculator import calculate
from app.safety.safety_router import is_dangerous


def test_p4_assistant_boundaries_are_importable() -> None:
    assert callable(run_chat_pipeline)
    assert compose("Calculator open kore dilam.", "Boss").startswith("Boss,")
    assert classify("delete system32").intent == "dangerous_block"
    assert route_task("2+2=?").intent == "calculator"
    assert calculate("2+2=?") == "2+2 = 4"
    assert is_dangerous("delete system32") is True

"""High-level assistant route policy notes and helpers."""

PIPELINE_ORDER = [
    "normalize_input",
    "safety_check",
    "load_context",
    "classify_intent",
    "decide_route",
    "execute_tool_or_answer",
    "compose_response",
    "save_context",
    "return_dto",
]


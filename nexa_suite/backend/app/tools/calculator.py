"""Local safe calculator tool."""

from __future__ import annotations

import re

CALCULATOR_RE = re.compile(r"^\s*\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+\s*(?:=\s*)?\??\s*$")
PERCENT_RE = re.compile(r"^\s*(?:calculate\s+)?(?P<percent>\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(?P<base>\d+(?:\.\d+)?)\s*\??\s*$")


def can_calculate(message: str) -> bool:
    return bool(CALCULATOR_RE.match(message) or PERCENT_RE.match(message))


def calculate(message: str) -> str:
    expression = " ".join((message or "").strip().lower().split())
    percent_match = PERCENT_RE.match(expression)
    if percent_match:
        percent = float(percent_match.group("percent"))
        base = float(percent_match.group("base"))
        result = base * percent / 100
        return f"{percent:g}% of {base:g} = {result:g}"
    if not CALCULATOR_RE.match(expression):
        raise ValueError("Only simple arithmetic expressions are supported locally.")
    expression = expression.strip().rstrip("?").rstrip("=").strip()
    result = eval(expression, {"__builtins__": {}}, {})
    return f"{expression} = {result:g}" if isinstance(result, float) else f"{expression} = {result}"


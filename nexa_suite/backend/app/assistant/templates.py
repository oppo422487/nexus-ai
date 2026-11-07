"""Reusable human-facing response templates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TemplateSet:
    mixed: tuple[str, ...]
    english: tuple[str, ...]
    bangla: tuple[str, ...] = ()


TEMPLATES: dict[str, TemplateSet] = {
    "youtube_open_done": TemplateSet(
        mixed=("YouTube open kore dilam.", "YouTube open hoye geche."),
        english=("YouTube open. I opened YouTube.", "YouTube open now."),
        bangla=("আপনার জন্য YouTube খুলে দিচ্ছি। আর কিছু করতে পারি?", "YouTube খুলে দিয়েছি। আর কী করতে হবে বলুন।"),
    ),
    "youtube_search_done": TemplateSet(
        mixed=("ami YouTube-e \"{query}\" search kore dicchi.", "YouTube-e \"{query}\" search open kore dilam."),
        english=("I opened a YouTube search for \"{query}\".", "YouTube search is open for \"{query}\"."),
        bangla=("আপনার জন্য YouTube-এ \"{query}\" খুঁজে দিচ্ছি। আর কিছু করতে পারি?",),
    ),
    "whatsapp_draft_done": TemplateSet(
        mixed=("WhatsApp draft ready kore dilam. Nexa did not click Send. Please review and press Send manually.",),
        english=("WhatsApp draft is ready. Nexa did not click Send. Please review and press Send manually.",),
    ),
    "calculator_open_done": TemplateSet(
        mixed=("Opened Calculator. Calculator open kore dilam.",),
        english=("Opened Calculator. Calculator open now.",),
        bangla=("আপনার জন্য Calculator খুলে দিয়েছি। আর কিছু করতে পারি?",),
    ),
    "weather_fetch": TemplateSet(
        mixed=("Dhaka-r weather niye ashchi.",),
        english=("I am fetching Dhaka weather.",),
    ),
    "llm_setup_missing": TemplateSet(
        mixed=("ei kajer jonno LLM provider key lagbe. Gemini/Groq/OpenRouter key .env-e add korle ami eta generate korte parbo.",),
        english=("this task needs an LLM provider key. Add a Gemini, Groq, or OpenRouter key in .env and I can generate it.",),
    ),
    "clarification": TemplateSet(
        mixed=("Eita ki search, action, na explanation hisebe korbo?",),
        english=("Should I handle this as a search, an action, or an explanation?",),
    ),
    "pending_cancelled": TemplateSet(
        mixed=("pending task cancel kore dilam.",),
        english=("I cancelled the pending task.",),
    ),
    "generic_done": TemplateSet(
        mixed=("done kore dilam.",),
        english=("Done.",),
    ),
}


def pick_template(intent: str, language_style: str, history_count: int = 0, **values: Any) -> str:
    template_set = TEMPLATES.get(intent) or TEMPLATES["generic_done"]
    options = (
        template_set.bangla
        if language_style == "bangla" and template_set.bangla
        else template_set.mixed
        if language_style in {"bangla", "banglish", "mixed"}
        else template_set.english
    )
    template = options[history_count % len(options)]
    return template.format(**values)

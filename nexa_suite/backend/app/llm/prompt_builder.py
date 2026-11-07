"""Prompt context helpers for Nexa's hosted LLM router."""

from __future__ import annotations

from app.memory.pending_tasks import PendingTask
from app.productivity.store import list_memories


def build_task_context(
    *,
    user_message: str,
    intent: str,
    language_style: str,
    pending_task: PendingTask | None = None,
) -> str:
    """Build strict, source-safe context for generation/composition requests."""

    lines = [
        "Nexa task context:",
        f"- User message: {user_message}",
        f"- Normalized intent: {intent}",
        f"- Language style: {language_style}",
        "- Answer the user's actual task only.",
    ]
    memories = list_memories(limit=10)
    if memories:
        lines.append("- User-approved persistent facts: " + "; ".join(item["fact"] for item in memories))
    if pending_task:
        platform = pending_task.data.get("platform") or ("web" if "page" in (user_message or "").lower() else None)
        stack = pending_task.data.get("stack") or ("HTML/CSS/JS" if platform == "web" else None)
        lines.extend(
            [
                f"- Pending task kind: {pending_task.kind}",
                f"- Pending original request: {pending_task.data.get('original_text') or pending_task.prompt}",
            ]
        )
        if platform:
            lines.append(f"- Inferred platform: {platform}")
        if pending_task.data.get("app_type"):
            lines.append(f"- Inferred app type: {pending_task.data['app_type']}")
        if pending_task.data.get("artifact"):
            lines.append(f"- Requested artifact/page: {pending_task.data['artifact']}")
        if stack:
            lines.append(f"- Default stack: {stack}")
        if pending_task.data:
            safe_data = {key: value for key, value in pending_task.data.items() if key != "secret"}
            lines.append(f"- Pending task data: {safe_data}")
    if intent in {"llm_assist", "llm_generation_continue"}:
        lines.extend(
            [
                "",
                "Code/page generation rules:",
                "- You are Nexa AI's code generation assistant.",
                "- Generate the requested code/artifact directly when enough details are present.",
                "- Stay aligned with the requested language, stack, page, and application context.",
                "- Preserve app/project context such as platform, app type, and requested page.",
                "- If stack is missing for web pages, use HTML, CSS, and JavaScript by default.",
                "- Provide usable code first; avoid explanation-only responses for code requests.",
                "- If details are missing, ask one precise question.",
            ]
        )
    return "\n".join(lines)

"""Safe directory whitelist for read-only file search."""

from pathlib import Path
from typing import Optional

BLOCKED_PATH_KEYWORDS: list[str] = [
    "system32",
    "windows",
    "program files",
    "appdata",
    "registry",
    "recycle",
    "temp",
    ".git",
    "node_modules",
]


def get_user_home() -> Path:
    return Path.home()


def get_safe_directory_map() -> dict[str, Path]:
    home = get_user_home()
    return {
        "desktop": home / "Desktop",
        "downloads": home / "Downloads",
        "documents": home / "Documents",
    }


def normalize_scope(value: Optional[str]) -> str:
    if not value:
        return "all_safe"
    val = value.lower().strip()
    if val in ("desktop", "desk", "ডেস্কটপ"):
        return "desktop"
    if val in ("downloads", "download", "ডাউনলোড"):
        return "downloads"
    if val in ("documents", "docs", "ডকুমেন্ট"):
        return "documents"
    if val in ("all", "all_safe", "safe"):
        return "all_safe"
    return "all_safe"


def is_path_within_safe_directories(path: Path) -> bool:
    try:
        resolved = path.resolve()
        safe_map = get_safe_directory_map()
        for safe_path in safe_map.values():
            try:
                safe_resolved = safe_path.resolve()
                if safe_resolved in resolved.parents or resolved == safe_resolved:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def contains_blocked_path_keyword(path_text: Optional[str]) -> bool:
    if not path_text:
        return False
    lower = path_text.lower().replace("\\", "/")
    for keyword in BLOCKED_PATH_KEYWORDS:
        if keyword in lower:
            return True
    return False


def get_directories_for_scope(scope: Optional[str]) -> tuple[bool, list[Path], str]:
    normalized = normalize_scope(scope)
    safe_map = get_safe_directory_map()

    if normalized == "all_safe":
        paths = list(safe_map.values())
    elif normalized in safe_map:
        paths = [safe_map[normalized]]
    else:
        return False, [], "Scope resolves to a blocked path."

    for p in paths:
        if contains_blocked_path_keyword(str(p)):
            return False, [], "Scope resolves to a blocked path."

    return True, paths, "Safe directories resolved."


def list_safe_directories() -> list[dict[str, str]]:
    safe_map = get_safe_directory_map()
    return [
        {"scope": scope, "path": str(path)}
        for scope, path in safe_map.items()
    ]

"""Safe Windows app whitelist config and alias normalizer."""

from __future__ import annotations

ALLOWED_APPS: dict[str, dict[str, str]] = {
    "notepad": {"command": "notepad", "label": "Notepad"},
    "calculator": {"command": "calc", "label": "Calculator"},
    "paint": {"command": "mspaint", "label": "Paint"},
    "chrome": {"command": "chrome", "label": "Google Chrome"},
    "file_explorer": {"command": "explorer", "label": "File Explorer"},
    "vscode": {"command": "code", "label": "Visual Studio Code"},
    "word": {"command": "winword", "label": "Microsoft Word"},
    "excel": {"command": "excel", "label": "Microsoft Excel"},
    "spotify": {"command": "spotify", "label": "Spotify"},
    "discord": {"command": "discord", "label": "Discord"},
    "telegram": {"command": "telegram", "label": "Telegram"},
}

BLOCKED_APP_KEYWORDS: list[str] = [
    "cmd",
    "command prompt",
    "powershell",
    "regedit",
    "registry",
    "taskmgr",
    "task manager",
    "control panel",
    "gpedit",
    "services",
    "system32",
    "shutdown",
    "restart",
    "format",
    "delete",
    "del ",
    "rm ",
    "rmdir",
    "shell",
    "terminal",
    "script",
    "bat",
    "ps1",
    "exe path",
    "c:\\",
    "ডিলিট",
    "ফরম্যাট",
    "শাটডাউন",
    "রিস্টার্ট",
]

PREFIX_WORDS: list[str] = [
    "open",
    "app",
    "software",
    "launch",
    "run",
    "start",
    "kholo",
    "khulo",
    "chalao",
    "open koro",
    "চালাও",
    "খোলো",
    "খুলুন",
]

ALIAS_MAP: dict[str, str] = {
    "note pad": "notepad",
    "notepad open koro": "notepad",
    "নোটপ্যাড": "notepad",
    "calc": "calculator",
    "calculator open koro": "calculator",
    "calculator chalao": "calculator",
    "ক্যালকুলেটর": "calculator",
    "paint": "paint",
    "paint open koro": "paint",
    "ms paint": "paint",
    "chrome browser": "chrome",
    "chrome open koro": "chrome",
    "google chrome": "chrome",
    "ক্রোম": "chrome",
    "file explorer": "file_explorer",
    "file explorer open koro": "file_explorer",
    "explorer": "file_explorer",
    "files": "file_explorer",
    "ফাইল": "file_explorer",
    "vs code": "vscode",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "vs code open koro": "vscode",
    "word": "word",
    "microsoft word": "word",
    "ms word": "word",
    "excel": "excel",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "spotify": "spotify",
    "স্পটিফাই": "spotify",
    "discord": "discord",
    "ডিসকর্ড": "discord",
    "telegram": "telegram",
    "টেলিগ্রাম": "telegram",
}


def normalize_app_key(value: str | None) -> str:
    if value is None:
        return ""

    key = value.strip().lower()
    key = " ".join(key.split())

    for raw, canonical in ALIAS_MAP.items():
        if key == raw or raw in key:
            return canonical

    for prefix in PREFIX_WORDS:
        if key.startswith(prefix):
            suffix = key[len(prefix) :].strip()
            if suffix:
                key = suffix
                break

    for raw, canonical in ALIAS_MAP.items():
        if key == raw or raw in key:
            return canonical

    return key


def is_blocked_app_request(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    normalized = " ".join(normalized.split())
    for keyword in BLOCKED_APP_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def get_allowed_app(
    value: str | None,
) -> tuple[bool, dict[str, str] | None, str]:
    if is_blocked_app_request(value) or not value:
        return (False, None, "App target is empty or blocked.")

    key = normalize_app_key(value)

    if key in ALLOWED_APPS:
        return (True, dict(ALLOWED_APPS[key]), "App is allowed.")

    return (False, None, "App is not in the allowed whitelist.")


def list_allowed_apps() -> list[dict[str, str]]:
    return [
        {"key": key, "command": value["command"], "label": value["label"]}
        for key, value in ALLOWED_APPS.items()
    ]

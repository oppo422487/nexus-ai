"""Explicit, whitelisted Windows media and app-close controls."""

from __future__ import annotations

import ctypes
import subprocess
import sys

from fastapi import APIRouter

from app.audit.event_log import record_audit_event
from app.permissions import is_permission_enabled, permission_denied_message
from app.schemas.system_controls import SystemControlRequest, SystemControlResponse

router = APIRouter(prefix="/system-controls", tags=["system-controls"])

_VK = {
    "mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "play_pause": 0xB3, "next_track": 0xB0, "previous_track": 0xB1,
}
_CLOSEABLE_APPS = {
    "notepad": ("notepad.exe", "Notepad"),
    "calculator": ("CalculatorApp.exe", "Calculator"),
    "paint": ("mspaint.exe", "Paint"),
    "chrome": ("chrome.exe", "Google Chrome"),
    "vscode": ("Code.exe", "Visual Studio Code"),
    "word": ("WINWORD.EXE", "Microsoft Word"),
    "excel": ("EXCEL.EXE", "Microsoft Excel"),
    "spotify": ("Spotify.exe", "Spotify"),
    "discord": ("Discord.exe", "Discord"),
    "telegram": ("Telegram.exe", "Telegram"),
}


def _result(status: str, request: SystemControlRequest, message: str, *, executed: bool = False, error: str | None = None) -> SystemControlResponse:
    record_audit_event("system_controls", request.action, status, "confirmed" if request.user_confirmed else "confirmation_required", request.target or "", message)
    return SystemControlResponse(status=status, action=request.action, executed=executed, message=message, error=error)


@router.get("/health")
def system_controls_health() -> dict:
    return {
        "status": "ok",
        "module": "system_controls",
        "available": sys.platform == "win32",
        "enabled": is_permission_enabled("system_media_controls"),
        "closeable_apps": [{"key": key, "label": meta[1]} for key, meta in _CLOSEABLE_APPS.items()],
    }


@router.post("/execute", response_model=SystemControlResponse)
def execute_system_control(request: SystemControlRequest) -> SystemControlResponse:
    if not is_permission_enabled("system_media_controls"):
        message = permission_denied_message("system_media_controls")
        return _result("blocked", request, message, error=message)
    if not request.user_confirmed:
        message = "System media/app controls require explicit confirmation."
        return _result("confirmation_required", request, message, error=message)
    if sys.platform != "win32":
        message = "These system controls are available on Windows only."
        return _result("unavailable", request, message, error=message)

    try:
        if request.action in _VK:
            key = _VK[request.action]
            ctypes.windll.user32.keybd_event(key, 0, 0, 0)
            ctypes.windll.user32.keybd_event(key, 0, 2, 0)
            labels = {
                "mute": "System mute toggled.", "volume_up": "System volume increased.",
                "volume_down": "System volume decreased.", "play_pause": "Media play/pause toggled.",
                "next_track": "Skipped to the next media track.", "previous_track": "Returned to the previous media track.",
            }
            return _result("executed", request, labels[request.action], executed=True)

        target = (request.target or "").strip().lower()
        if target not in _CLOSEABLE_APPS:
            message = "Only explicitly whitelisted desktop apps can be closed."
            return _result("blocked", request, message, error=message)
        image_name, label = _CLOSEABLE_APPS[target]
        completed = subprocess.run(
            ["taskkill", "/IM", image_name],
            capture_output=True,
            text=True,
            timeout=8,
            shell=False,
        )
        if completed.returncode != 0:
            message = f"{label} is not running or did not close normally."
            return _result("failed", request, message, error=(completed.stderr or completed.stdout).strip()[:300])
        return _result("executed", request, f"Closed {label}.", executed=True)
    except Exception as exc:
        message = "The confirmed system control could not be completed."
        return _result("failed", request, message, error=str(exc))

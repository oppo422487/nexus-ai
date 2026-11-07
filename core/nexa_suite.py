"""Optional Nexa services, isolated from the original voice runtime.

No network connections, imports of the backend, or processes at app startup.
Only fixed local routes are exposed; model-supplied URLs are never accepted.
"""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "nexa_suite" / "backend"
BASE_URL = "http://127.0.0.1:8766"
_process = None
_lock = threading.Lock()
_http = build_opener(ProxyHandler({}))


def _request(path: str, payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(BASE_URL + path, data=body,
                      headers={"Content-Type": "application/json"})
    with _http.open(request, timeout=20) as response:
        return json.load(response)


def _ready() -> bool:
    try:
        # A foreign service on this port must never receive Nexa requests.
        return _request("/api/nexa-integration") == {
            "product": "nexa-ai-mark-plus", "version": 1
        }
    except Exception:
        return False


def stop() -> None:
    global _process
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
            _process.wait(timeout=5)
    _process = None


atexit.register(stop)


def ensure_started() -> None:
    global _process
    with _lock:
        if _ready():
            return
        if _process is None or _process.poll() is not None:
            python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            executable = str(python) if python.is_file() else sys.executable
            env = os.environ.copy()
            env["NEXA_DATA_DIR"] = str(ROOT / "nexa_suite" / "runtime" / "data")
            env["NEXA_MODELS_DIR"] = str(ROOT / "nexa_suite" / "runtime" / "models")
            env["NEXA_ENV_FILE"] = str(BACKEND / ".env")
            env["BACKEND_PORT"] = "8766"
            env["APP_ENV"] = "production"
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            log = ROOT / "nexa_suite" / "runtime" / "backend.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as output:
                _process = subprocess.Popen(
                    [executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8766"],
                    cwd=BACKEND, env=env, stdout=output, stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if _ready():
                return
            if _process.poll() is not None:
                raise RuntimeError("Nexa service could not start. See nexa_suite/runtime/backend.log; run setup_nexa.py first.")
            time.sleep(0.2)
        stop()
        raise RuntimeError("Nexa service did not become ready within 15 seconds.")


READ_ROUTES = {
    "dashboard": "/api/productivity/dashboard",
    "diagnostics": "/api/productivity/diagnostics",
    "audit": "/api/audit/recent",
    "analytics": "/api/audit/stats",
    "images": "/api/images/history",
    "image_status": "/api/images/health",
    "email_status": "/api/email/status",
    "permissions": "/api/permissions",
}


def read(operation: str):
    path = READ_ROUTES[operation]
    ensure_started()
    return _request(path)


def open_panel() -> str:
    if not (ROOT / "nexa_suite/frontend/dist/index.html").is_file():
        return "প্যানেল প্রস্তুত হয়নি। nexa_suite/frontend-এ npm ci ও npm run build চালান।"
    ensure_started()
    if not webbrowser.open(BASE_URL + "/suite/"):
        return "ব্রাউজার খোলা যায়নি। খুলুন: " + BASE_URL + "/suite/"
    return "নেক্সা আই-এর অতিরিক্ত ফিচার প্যানেল ব্রাউজারে খোলার অনুরোধ পাঠানো হয়েছে।"


def write(operation: str, payload: dict):
    # Called only from the UI confirmation callback in the Nexa plugin.
    routes = {
        "item": "/api/productivity/items",
        "email": "/api/email/send",
        "content": "/api/content/export",
        "image": "/api/images/queue",
    }
    path = routes[operation]
    ensure_started()
    return _request(path, {**payload, "user_confirmed": True})

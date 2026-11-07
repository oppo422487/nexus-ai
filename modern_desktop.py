"""Launch the original Nexa desktop UI with the existing native voice engine."""
from pathlib import Path
import os
import json
import secrets
import subprocess
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
_http = build_opener(ProxyHandler({}))
urlopen = _http.open


def existing_desktop_ready():
    """Reuse a running suite only after verifying its identity and engine gateway."""
    try:
        with urlopen("http://127.0.0.1:8766/api/nexa-integration", timeout=2) as response:
            if json.load(response) != {"product": "nexa-ai-mark-plus", "version": 1}:
                return False
        with urlopen("http://127.0.0.1:8766/api/engine/events?after=999999999", timeout=3) as response:
            state = json.load(response)
            return isinstance(state, dict) and "generation" in state
    except Exception:
        return False


def launch_frontend():
    frontend = ROOT / "nexa_suite/frontend"
    electron = frontend / "node_modules/electron/dist/electron.exe"
    if not electron.is_file():
        raise RuntimeError("Install Electron: cd nexa_suite/frontend; node node_modules/electron/install.js")
    args = [str(electron), str(frontend)]
    debug_port = os.environ.get("NEXA_DESKTOP_DEBUG_PORT", "")
    if debug_port.isdigit():
        args.append("--remote-debugging-port=" + debug_port)
    subprocess.run(args, cwd=frontend, env=os.environ.copy(), check=True)


def main():
    os.chdir(ROOT)
    if existing_desktop_ready():
        # Electron uses this flag to select the native UI. The existing backend
        # retains its private bridge credential; this process never replaces it.
        os.environ["NEXA_ENGINE_BRIDGE_TOKEN"] = secrets.token_urlsafe(32)
        launch_frontend()
        return
    os.environ["NEXA_ENGINE_BRIDGE_TOKEN"] = secrets.token_urlsafe(32)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    logs = ROOT / "nexa_suite/runtime"
    logs.mkdir(parents=True, exist_ok=True)
    from core import nexa_suite
    engine = None
    try:
        with (logs / "engine.log").open("a", encoding="utf-8") as log:
            engine = subprocess.Popen([sys.executable, "main.py", "--modern-ui"], cwd=ROOT,
                env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
        for _ in range(160):
            try:
                request = Request("http://127.0.0.1:8767/state",
                    headers={"X-Nexa-Bridge": os.environ["NEXA_ENGINE_BRIDGE_TOKEN"]})
                with urlopen(request, timeout=1):
                    break
            except Exception:
                if engine.poll() is not None:
                    raise RuntimeError("Native engine failed; see nexa_suite/runtime/engine.log")
                time.sleep(.25)
        else:
            raise RuntimeError("Native engine startup timed out.")
        nexa_suite.ensure_started()
        launch_frontend()
    finally:
        nexa_suite.stop()
        if engine is not None and engine.poll() is None:
            try:
                request = Request("http://127.0.0.1:8767/command", data=json.dumps({"action": "shutdown"}).encode(),
                    headers={"X-Nexa-Bridge": os.environ["NEXA_ENGINE_BRIDGE_TOKEN"], "Content-Type": "application/json"})
                with urlopen(request, timeout=2):
                    pass
                engine.wait(timeout=5)
            except Exception:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(engine.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=flags)
                else:
                    engine.terminate()
                engine.wait(timeout=5)


if __name__ == "__main__":
    main()

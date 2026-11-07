"""Set up Nexa + Mark LVI; the React panel is optional."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-panel", action="store_true", help="Build the optional Nexa web panel (requires Node.js 22+).")
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        raise SystemExit("Use Python 3.11, 3.12 or 3.13 for this installer.")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if args.with_panel and npm is None:
        raise SystemExit("Install Node.js 22+ with npm, then retry --with-panel.")
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        venv.create(target, with_pip=True)
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True, cwd=ROOT)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"),
                    "-r", str(ROOT / "nexa_suite/backend/requirements.txt")], check=True, cwd=ROOT)
    try:
        subprocess.run([str(python), "-m", "playwright", "install", "chromium", "firefox"], check=True, cwd=ROOT)
    except subprocess.CalledProcessError:
        print("Browser automation browsers could not be downloaded. Retry: .venv\\Scripts\\python.exe -m playwright install chromium firefox")
    if not (ROOT / "core/face_model.obj").is_file():
        raise SystemExit("Missing avatar asset. Download and extract the complete project ZIP.")
    if args.with_panel:
        frontend = ROOT / "nexa_suite/frontend"
        subprocess.run([npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=frontend, check=True)
        subprocess.run([npm, "run", "build"], cwd=frontend, check=True)
    (target / ".nexa-setup-complete").write_text("1", encoding="ascii")
    print("Setup complete. Run start_nexa.cmd and enter your own Gemini API key.")
    if not args.with_panel:
        print("Optional web panel: python setup_nexa.py --with-panel (Node.js 22+ required).")


if __name__ == "__main__":
    main()

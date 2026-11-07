"""Make Windows Bengali fallback fonts available to Qt, including offscreen QA."""
import os
from pathlib import Path

_loaded = False


def ensure_ui_fonts():
    global _loaded
    if _loaded or os.name != "nt":
        return
    from PyQt6.QtGui import QFontDatabase, QFont
    folder = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in ("segoeui.ttf", "cour.ttf", "Nirmala.ttc", "Nirmala.ttf", "vrinda.ttf"):
        path = folder / name
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    QFont.insertSubstitutions("Courier New", ["Nirmala UI", "Segoe UI"])
    _loaded = True

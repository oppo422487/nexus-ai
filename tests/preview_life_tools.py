"""Explicit native dialog preview, no account changes or voice engine."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from core.life_tools_ui import LifeTools
app = QApplication([])
window = LifeTools()
window.show()
def save():
    (ROOT/'runtime').mkdir(exist_ok=True)
    window.grab().save(str(ROOT/'runtime/life_tools_preview.png'))
    window.close()
    app.quit()
QTimer.singleShot(1500, save)
app.exec()

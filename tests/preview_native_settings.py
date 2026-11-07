"""Synthetic, account-free visual QA for native settings pages."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_settings import SettingsTests

case = SettingsTests()
case.setUpClass(); case.setUp()
root = Path(__file__).resolve().parents[1]/'runtime/settings-preview'
root.mkdir(parents=True, exist_ok=True)
try:
    case.dialog.show()
    for key in ('general','identity','audio','providers','plugins','plugin_settings','tools'):
        case.dialog.select(key)
        for _ in range(5): case.app.processEvents()
        case.dialog.grab().save(str(root/(key+'.png')))
    case.dialog.resize(800,580)
    case.dialog.select('identity')
    for _ in range(5): case.app.processEvents()
    case.dialog.grab().save(str(root/'identity-small.png'))
finally:
    case.tearDown()
print('Synthetic settings screenshots saved.')

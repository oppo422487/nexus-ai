"""Synthetic saved routine for native visual QA; executes no desktop actions."""
from pathlib import Path
import tempfile
from unittest.mock import patch
from test_native_settings import SettingsTests
from core import teach_mode as teach, life_store as store

with tempfile.TemporaryDirectory() as temp, patch.object(store,'DB',Path(temp)/'teach.sqlite3'):
    teach._recording_id=None;teach.bind_ui(None)
    case=SettingsTests();case.setUpClass();case.setUp()
    try:
        sample=teach.start('Weekly report review')
        teach.observe('file_controller',{'action':'list','path':'Downloads'},'Synthetic listing')
        teach.observe('nexa_life',{'operation':'excel_read','path':'C:/Demo/weekly-report.xlsx','cell_range':'A1:F30'},'Synthetic workbook')
        teach.finish()
        case.dialog.select('teach');case.dialog.show()
        for _ in range(6):case.app.processEvents()
        root=Path(__file__).resolve().parents[1]/'runtime'
        root.mkdir(exist_ok=True)
        case.dialog.grab().save(str(root/'teach_mode_preview.png'))
    finally:
        teach._recording_id=None
        case.tearDown()
    teach._recording_id=None;teach.bind_ui(None)
print('Teach mode synthetic UI preview saved.')

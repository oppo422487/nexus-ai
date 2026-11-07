import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
from PIL import Image
from actions import file_controller as fc, computer_control as cc, open_app as app


class DownloadPaths(unittest.TestCase):
    def test_case_and_bengali_download_subpaths(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(fc,'_get_downloads',return_value=Path(folder)):
            for raw in ('Downloads/screenshot.png','DOWNLOADS/screenshot.png','ডাউনলোড/screenshot.png'):
                self.assertEqual(cc._safe_screenshot_path(raw),Path(folder)/'screenshot.png')

    def test_screenshot_saved_at_resolved_path(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(fc,'_get_downloads',return_value=Path(folder)),patch.object(cc,'_require_pyautogui'),patch.object(cc.pyautogui,'screenshot',return_value=Image.new('RGB',(20,20))):
            cc._screenshot('Downloads/qa.png')
            with Image.open(Path(folder)/'qa.png') as image:self.assertEqual(image.size,(20,20))

    def test_file_open_never_uses_application_search(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(fc,'_get_downloads',return_value=Path(folder)),patch.object(fc.os,'startfile') as launch,patch.object(app,'_desktop_search') as search:
            p=Path(folder)/'qa.png';p.write_bytes(b'fixture')
            app.open_app({'app_name':'Downloads/qa.png'})
            launch.assert_called_once_with(str(p));search.assert_not_called()

    def test_missing_file_does_not_search_web(self):
        with patch.object(app,'_desktop_search') as search:
            result=app.open_app({'app_name':'Downloads/nexa-nonexistent-731.png'})
        search.assert_not_called();self.assertIn('not found',result)


if __name__=='__main__':unittest.main()

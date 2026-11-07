"""Native settings navigation and preserved callbacks, no live account changes."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget
from core.qt_settings import NativeSettings, open_settings, PAGES


class Host(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget(QWidget())
        for name in ('_drawer_btn','_ctrl_btn','_autostart_btn','_brief_btn','_wake_btn','_wake_sleep_btn','_ptt_btn'):
            setattr(self, name, QPushButton(name, self))
        self._drawer_btn.setCheckable(True); self._ctrl_btn.setCheckable(True)
        self._wake_sleep_btn.hide()
        self.get_plugins = lambda: []
        self.get_plugin_settings = lambda: []
        for name in ('_close_setup','_close_controls','_preview_ui_color','_apply_name_update',
                     '_on_audio_devices_applied','_on_providers_applied','_refresh_wake_btns',
                     '_refresh_talk_btns','_create_desktop_shortcut','_open_remote'):
            setattr(self, name, Mock())


class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        import ui
        from core import teach_mode, life_store
        teach_mode._recording_id=None
        teach_mode.bind_ui(None)
        self.teach_temp=tempfile.TemporaryDirectory()
        self.host = Host()
        self.patches = [
            patch.object(life_store,'DB',Path(self.teach_temp.name)/'life.sqlite3'),
            patch.object(ui, '_read_full_config', return_value={'assistant_name':'Nexa AI','user_name':'UI Test','voice_name':'Kore'}),
            patch('core.audio_devices.list_devices', return_value=[]),
            patch('core.audio_devices.get_output_volume', return_value=None),
            patch('memory.memory_manager.all_entries_for_ui', return_value=[]),
            patch('providers.registry.discover', return_value=[]),
        ]
        for item in self.patches: item.start()
        self.dialog = NativeSettings(self.host)

    def tearDown(self):
        for form in self.dialog.forms.values():
            if hasattr(form, 'busy'): form.busy = False
        self.dialog.close(); self.app.processEvents(); self.dialog.deleteLater(); self.host.close(); self.host.deleteLater()
        self.app.processEvents()
        for item in reversed(self.patches): item.stop()
        self.teach_temp.cleanup()

    def test_every_category_opens_inside_same_window(self):
        self.dialog.show()
        for key, _, _ in PAGES:
            self.dialog.select(key)
            self.app.processEvents()
            self.assertIn(key, self.dialog.forms, key+' failed to build')
            self.assertIs(self.dialog.stack.currentWidget(), self.dialog.views[key])
            self.assertTrue(self.dialog.forms[key].isVisible(), key)
        self.host._apply_name_update.assert_not_called()
        self.host._on_audio_devices_applied.assert_not_called()
        self.host._on_providers_applied.assert_not_called()

    def test_identity_save_uses_original_callback(self):
        self.dialog.select('identity'); self.dialog.show(); self.app.processEvents()
        panel = self.dialog.forms['identity']
        panel._name_input.setText('UI Test Assistant')
        panel._user_input.setText('Sample user')
        next(b for b in panel.findChildren(QPushButton) if b.text() == 'Apply changes').click()
        self.app.processEvents()
        self.host._apply_name_update.assert_called_once()
        self.assertEqual(self.host._apply_name_update.call_args.args[:2], ('UI Test Assistant', 'Sample user'))

    def test_close_and_reopen_reuses_window_and_current_form(self):
        first = open_settings(self.host, 'plugins'); self.app.processEvents()
        form = first.forms['plugins']
        next(b for b in form.findChildren(QPushButton) if b.text() == 'Close').click()
        self.app.processEvents(); self.app.processEvents()
        self.assertFalse(first.isVisible())
        second = open_settings(self.host, 'plugins'); self.app.processEvents()
        self.assertIs(first, second); self.assertTrue(form.isVisible())
        second.close()

    def test_late_legacy_style_refresh_stays_in_current_theme(self):
        self.dialog.select('voice'); self.dialog.show(); self.app.processEvents()
        button = self.host._wake_btn
        button.setStyleSheet('background:#001a08;color:#00ff00')
        self.app.processEvents(); self.app.processEvents()
        self.assertEqual(button.styleSheet(), '')

    def test_sidebar_selection_is_clickable_and_scrollable(self):
        self.dialog.resize(800, 580); self.dialog.show()
        for i, (key, _, _) in enumerate(PAGES):
            self.dialog.navigation.setCurrentRow(i); self.app.processEvents()
            self.assertEqual(self.dialog.current_key, key)
            self.assertGreater(self.dialog.stack.width(), 250)

    def test_provider_cards_fit_the_available_width(self):
        self.dialog.resize(800, 580); self.dialog.select('providers'); self.dialog.show()
        for _ in range(8): self.app.processEvents()
        self.assertEqual(self.dialog.views['providers'].horizontalScrollBar().maximum(), 0)

    def test_account_work_is_not_discarded_by_closing_settings(self):
        self.dialog.select('gmail'); self.dialog.show(); self.app.processEvents()
        self.dialog.forms['gmail'].busy = True
        self.dialog.close(); self.app.processEvents()
        self.assertTrue(self.dialog.isVisible())
        self.dialog.forms['gmail'].busy = False
        self.dialog.close(); self.app.processEvents()
        self.assertFalse(self.dialog.isVisible())

    def test_teach_buttons_start_capture_and_save_routine(self):
        from core import teach_mode as teach
        from PyQt6.QtTest import QTest
        self.dialog.select('teach');self.dialog.show();self.app.processEvents()
        panel=self.dialog.forms['teach'];panel.name.setText('UI routine sample')
        panel.start_button.click()
        for _ in range(100):
            self.app.processEvents()
            if not panel.busy:break
            QTest.qWait(10)
        self.assertFalse(panel.busy)
        self.assertEqual(teach.status()['title'],'UI routine sample')
        teach.observe('file_controller',{'action':'list','path':self.teach_temp.name},'Synthetic listing')
        panel.finish_button.click()
        for _ in range(100):
            self.app.processEvents()
            if not panel.busy:break
            QTest.qWait(10)
        self.assertFalse(panel.busy)
        self.assertEqual(teach.workflows()[0]['status'],'ready')

    def test_cancelling_teach_review_never_executes_steps(self):
        from core import teach_mode as teach
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QDialog
        item=teach.start('Review sample');teach.observe('file_controller',{'action':'list','path':self.teach_temp.name},'Synthetic listing');teach.finish()
        self.dialog.select('teach');self.dialog.show();self.app.processEvents()
        panel=self.dialog.forms['teach'];panel.refresh();self.app.processEvents()
        def cancel():
            for dialog in panel.findChildren(QDialog):dialog.reject()
        with patch.object(teach,'run_reviewed') as run:
            QTimer.singleShot(30,cancel);panel.run_selected();self.app.processEvents()
            run.assert_not_called()

    def test_screen_guide_crop_and_clear_are_local_only(self):
        from PIL import Image
        from core import screen_guide
        self.dialog.select('screen_guide');self.dialog.show();self.app.processEvents()
        panel=self.dialog.forms['screen_guide']
        with patch.object(screen_guide,'analyze') as ai:
            panel.got_image(Image.new('RGB',(400,200),'white'))
            panel.view.selection=(100,50,300,150);panel.crop()
            self.assertEqual(panel.image.size,(200,100))
            panel.clear();self.assertIsNone(panel.image);ai.assert_not_called()

    def test_declining_screen_share_does_not_call_model(self):
        from PIL import Image
        from core import screen_guide
        from PyQt6.QtWidgets import QMessageBox
        self.dialog.select('screen_guide');self.dialog.show();self.app.processEvents()
        panel=self.dialog.forms['screen_guide'];panel.got_image(Image.new('RGB',(400,200),'white'))
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No),patch.object(screen_guide,'analyze') as ai:
            panel.analyze();ai.assert_not_called()

    def test_screen_preview_owns_its_image_after_pillow_buffer_is_freed(self):
        import gc
        from PIL import Image
        self.dialog.select('screen_guide');self.dialog.show();self.app.processEvents()
        panel=self.dialog.forms['screen_guide']
        panel.got_image(Image.new('RGB',(20,20),(11,22,33)))
        panel.image=None;gc.collect();self.app.processEvents()
        pixmap=next(x for x in panel.view.scene().items() if hasattr(x,'pixmap')).pixmap()
        self.assertEqual(pixmap.toImage().pixelColor(0,0).getRgb()[:3],(11,22,33))


class MainWindowSettingsTests(unittest.TestCase):
    def test_real_sidebar_uses_settings_window_and_keeps_legacy_drawers_hidden(self):
        import ui
        app = QApplication.instance() or QApplication([])
        with patch.object(ui, '_read_full_config', return_value={'assistant_name':'Nexa AI'}), \
             patch.object(ui.MainWindow, '_check_config', return_value=True), \
             patch.object(ui.MainWindow, '_check_autostart', return_value=False), \
             patch.object(ui.MainWindow, '_warm_wake_state'), \
             patch.object(ui.MainWindow, '_wake_state', return_value={'ready':False,'enabled':False,'awake':True}):
            win = ui.MainWindow('face.png')
            win.show(); app.processEvents()
            win._drawer_btn.click(); app.processEvents()
            dialog = win._native_settings_dialog
            self.assertTrue(dialog.isVisible()); self.assertEqual(dialog.current_key, 'general')
            self.assertFalse(win._quick_drawer.isVisible())
            win._ctrl_btn.click(); app.processEvents()
            self.assertIs(dialog, win._native_settings_dialog)
            self.assertEqual(dialog.current_key, 'voice')
            self.assertFalse(win._ctrl_drawer.isVisible())
            self.assertIsNone(win.hud._blob)
            self.assertFalse(win.hud._tmr.isActive())
            dialog.close(); win.hide(); win.deleteLater(); app.processEvents()


if __name__ == '__main__':
    unittest.main()

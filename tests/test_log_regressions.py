"""Regressions from the 2026-10-28 local session; no live desktop actions."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from actions import browser_control as browser, computer_control as desktop
from actions import file_processor as files, file_controller, send_message

class LogRegressionTests(unittest.TestCase):
    def test_browser_open_alias_uses_navigation_without_automation(self):
        with patch.object(browser, '_registry') as registry, patch.object(browser, '_open_native', return_value='Opened in chrome: https://youtube.com') as native:
            registry.has.return_value=False
            self.assertIn('Opened', browser.browser_control({'action':'open','url':'youtube.com'}))
            native.assert_called_once_with('youtube.com', None)
            registry.get.assert_not_called()

    def test_native_close_never_creates_unrelated_automation_window(self):
        with patch.object(browser, '_registry') as registry, patch.object(browser, '_close_native_tab', return_value='foreground check') as close:
            registry.has.return_value=False
            self.assertEqual(browser.browser_control({'action':'close_tab','browser':'chrome'}),'foreground check')
            close.assert_called_once_with('chrome'); registry.get.assert_not_called()

    def test_closed_context_is_not_an_active_browser(self):
        registry=browser._SessionRegistry()
        registry._sessions['chrome']=Mock(_context_closed=True)
        self.assertFalse(registry.has('chrome'));self.assertFalse(registry.has())

    def test_last_managed_tab_clears_stale_context(self):
        session=browser._BrowserSession('chrome')
        context=Mock(pages=[])
        session._context=context
        page=Mock(context=context);page.is_closed.return_value=False;page.close=AsyncMock()
        session._page=page
        self.assertEqual(asyncio.run(session.close_tab()),'Tab closed.')
        self.assertIsNone(session._context);self.assertTrue(session._context_closed)

    def test_closed_context_can_launch_again(self):
        session=browser._BrowserSession('chrome');session._context=Mock();session._context_closed=True
        session._spec=None
        # Reaching the explicit missing-browser error proves stale context no longer short-circuits launch.
        with self.assertRaises(RuntimeError): asyncio.run(session._launch())
        self.assertIsNone(session._context)

    def test_unicode_short_text_uses_clipboard_not_typewrite(self):
        with patch.object(desktop,'_require_pyautogui'),patch.object(desktop,'_require_pyperclip',return_value=True),patch.object(desktop,'pyperclip') as clip,patch.object(desktop,'pyautogui') as gui,patch.object(desktop.time,'sleep'):
            desktop._type('বাংলা')
            clip.copy.assert_called_once_with('বাংলা');gui.typewrite.assert_not_called();gui.hotkey.assert_called_once()

    def test_keyboard_keys_alias_is_understood(self):
        with patch.object(desktop,'_hotkey',return_value='keys sent') as hotkey:
            self.assertEqual(desktop.computer_control({'action':'keyboard_keys','keys':'ctrl+f'}),'keys sent')
            hotkey.assert_called_once_with('ctrl','f')

    def test_file_processor_uses_real_downloads_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'notes.txt';path.write_text('local fixture')
            with patch.object(file_controller,'_get_downloads',return_value=Path(folder)):
                self.assertIn('local fixture',files.file_processor({'file_path':'downloads/notes.txt','action':'extract_text'}))

    def test_missing_optional_whatsapp_driver_restores_desktop_fallback(self):
        import sys
        with patch.dict(sys.modules,{'plugins._whatsapp_core':None}),patch.object(send_message,'_desktop_send',return_value='status=unverified') as fallback:
            result=send_message._send_whatsapp('fixture','not a real message')
            self.assertEqual(result,'status=unverified')
            fallback.assert_called_once_with('WhatsApp','fixture','not a real message')

    def test_failed_whatsapp_focus_is_not_reported_as_success(self):
        from core import windows_whatsapp
        with patch.object(desktop,'_get_os',return_value='windows'),patch.object(windows_whatsapp,'focus_existing',return_value=False):
            self.assertIn('Focus failed',desktop._focus_window('WhatsApp'))

    def test_notifications_filter_sender_and_do_not_consume_other_matches(self):
        from plugins import notification_reader as reader
        rows=[dict(id=900001,app='WhatsApp',title='Alice',body='hello'),dict(id=900002,app='WhatsApp',title='Bob',body='hi')]
        def mock_async(coro):
            coro.close()
            return rows, 'ALLOWED'
        with patch.object(reader,'_ensure_winsdk',return_value=True),patch.object(reader,'_run_async',side_effect=mock_async),patch.object(reader,'_seen_ids',set()):
            first=reader.run({'action':'check','app':'whatsapp','pattern':'Alice'})
            self.assertIn('Alice',first);self.assertNotIn('Bob:',first)
            second=reader.run({'action':'check','app':'whatsapp','pattern':'Bob'})
            self.assertIn('Bob',second)
            third=reader.run({'action':'check','app':'whatsapp','pattern':'nobody'})
            self.assertIn('does not establish',third)

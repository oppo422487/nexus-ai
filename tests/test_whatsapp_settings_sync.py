"""Native settings synchronization against chat writes, isolated offscreen."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from core import whatsapp_calls as calls,whatsapp_auto_reply as auto
from core.whatsapp_calls_ui import WhatsAppCallsPanel

class SettingsSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patches=[patch.object(calls,'CONFIG',Path(self.tmp.name)/'calls.json'),patch.object(calls,'audio_outputs',return_value=[]),patch('core.whatsapp_caller_notes.return_inputs',return_value=[])]
        for p in self.patches:p.start()
        calls.update_settings(dict(auto_answer_message='Old message',auto_answer_enabled=False))
        self.panel=WhatsAppCallsPanel();self.panel.watch_timer.stop()
    def tearDown(self):
        self.panel.close();self.panel.deleteLater()
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def test_chat_updates_visible_message_without_overwriting_unsaved_edit(self):
        calls.update_settings({'auto_answer_message':'From chat'})
        self.panel.refresh_watch_status()
        self.assertEqual(self.panel.auto_message.toPlainText(),'From chat')
        self.panel.auto_message.setPlainText('Unsaved edit')
        calls.update_settings({'auto_answer_message':'Newer chat'})
        self.panel.refresh_watch_status()
        self.assertEqual(self.panel.auto_message.toPlainText(),'Unsaved edit')
        self.panel.save()
        self.assertEqual(calls.settings()['auto_answer_message'],'Newer chat')
        self.assertIn('Not saved',self.panel.result.text())
    def test_routing_save_preserves_latest_chat_message_and_expiry(self):
        calls.update_settings(dict(auto_answer_message='Newest',auto_answer_expires_at=9876543210))
        self.panel.save()
        self.assertEqual(calls.settings()['auto_answer_message'],'Newest')
        self.assertEqual(calls.settings()['auto_answer_expires_at'],9876543210)

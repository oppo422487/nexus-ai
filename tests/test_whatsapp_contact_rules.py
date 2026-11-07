"""Exact caller selection, persisted independent timers; no live calls."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from core import whatsapp_calls as calls,whatsapp_contact_rules as rules,whatsapp_auto_reply as auto
from plugins import whatsapp_desktop_call as plugin

class CallerRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=patch.object(calls,'CONFIG',Path(self.tmp.name)/'calls.json');self.p.start()
    def tearDown(self):self.p.stop();self.tmp.cleanup()
    def save(self,name,message,minutes=None,aliases=None):
        with patch.object(calls,'audio_ready'),patch.object(auto,'start'):
            return rules.configure(name,message,minutes,aliases)
    def test_independent_messages_deadlines_and_exact_number_alias(self):
        with patch('time.time',return_value=1000):
            self.save('Mother','At work',10,['+880 123-456'])
            self.save('Supervisor','Will send report',60)
            cfg=calls.settings()
            self.assertEqual(rules.choose(cfg,'+880123456')['message'],'At work')
            self.assertEqual(rules.choose(cfg,'Supervisor')['message'],'Will send report')
            self.assertIsNone(rules.choose(cfg,'Unknown'))
            self.assertIsNone(rules.choose(cfg,'Mother other'))
        with patch('time.time',return_value=1700):
            self.assertIsNone(rules.choose(cfg,'Mother'))
            self.assertEqual(rules.choose(cfg,'Supervisor')['message'],'Will send report')
    def test_unknown_caller_uses_only_live_default(self):
        cfg=dict(auto_answer_enabled=True,auto_answer_message='Default',auto_answer_expires_at=1500,caller_rules=[])
        with patch('time.time',return_value=1000):self.assertFalse(rules.choose(cfg,'Unknown')['matched'])
        with patch('time.time',return_value=1600):self.assertIsNone(rules.choose(cfg,'Unknown'))
    def test_duplicate_alias_rejected_without_mutation(self):
        self.save('Mother','First',aliases=['123'])
        before=calls.settings()
        with self.assertRaises(ValueError):self.save('Boss','Second',aliases=['123'])
        self.assertEqual(calls.settings(),before)
    def test_disable_one_preserves_other_and_default(self):
        calls.update_settings(dict(auto_answer_enabled=True,auto_answer_message='Default'))
        self.save('Mother','First');self.save('Father','Second')
        rules.configure('Mother',enabled=False)
        self.assertEqual(rules.choose(calls.settings(),'Mother')['message'],'Default')
        self.assertEqual(rules.choose(calls.settings(),'Father')['message'],'Second')
    def test_stale_settings_write_is_rejected(self):
        calls.update_settings({'auto_answer_message':'old'})
        calls.update_settings({'auto_answer_message':'from chat'})
        with self.assertRaises(RuntimeError):calls.update_settings({'auto_answer_message':'stale'},expected_message='old')
        self.assertEqual(calls.settings()['auto_answer_message'],'from chat')
    def test_plugin_persists_contact_instead_of_changing_default(self):
        calls.update_settings({'auto_answer_message':'Default'})
        with patch.object(calls,'audio_ready'),patch.object(auto,'start'):
            result=json.loads(plugin.run(dict(action='set_caller_reply',contact_name='Mother',message='Exact',duration_minutes=10)))
        self.assertTrue(result['saved']);self.assertEqual(calls.settings()['auto_answer_message'],'Default')
    def test_caller_identity_must_be_incoming_not_chat_sidebar(self):
        vision=Mock();vision.observe.return_value=(None,dict(state='chat',recipient='Mother'))
        with patch.object(calls,'visual_controller',return_value=vision):
            with self.assertRaises(RuntimeError):rules.current_caller(Mock())

    def test_watcher_uses_prepared_personal_message_and_rechecks_caller(self):
        import threading
        calls.update_settings(dict(auto_answer_enabled=True,auto_answer_message='Default',caller_rules=[dict(contact_name='Mother',message='Personal exact',enabled=True,expires_at=None,aliases=[])]))
        stop=threading.Event()
        async def hints():return ['toast:fixture']
        def handled(*args,**kwargs):
            stop.set();return dict(status='played_to_virtual_cable',accepted=True,playback_complete=True)
        with patch.object(auto,'_stop',stop),patch.object(auto,'arm_expiry'),patch.object(auto,'notification_hints',hints),patch.object(auto,'window_hints',return_value=({42},set())),patch.object(calls,'audio_ready',return_value=dict(id=19,rate=48000,name='CABLE Input')),patch.object(calls,'synthesize',side_effect=lambda message:(message,48000,19)),patch.object(rules,'current_caller',return_value='Mother'),patch.object(calls,'message_operation',side_effect=handled) as operation:
            auto.worker()
        operation.assert_called_once_with('answer_and_say','','Personal exact',prepared_audio=('Personal exact',48000,19),expected_caller='Mother')

    def test_rule_expiring_before_acceptance_does_not_click(self):
        from contextlib import contextmanager
        calls.update_settings(dict(caller_rules=[dict(contact_name='Mother',message='Expired',expires_at=1,enabled=True)]))
        @contextmanager
        def controller():yield Mock()
        with patch.object(calls,'controller',controller),patch.object(calls,'audio_ready',return_value=dict(id=19,rate=48000,name='CABLE Input')),patch.object(calls,'preflight_playback'),patch.object(rules,'current_caller',return_value='Mother'),patch.object(calls,'perform') as action:
            with self.assertRaisesRegex(RuntimeError,'expired'):
                calls.message_operation('answer_and_say','','Expired',prepared_audio=([0.1],48000,19),expected_caller='Mother')
        action.assert_not_called()

    def test_literal_no_name_bengali_english_and_decoration_are_same_contact(self):
        self.save('নো নেম','কালকে অফিসে যাবে না।')
        for caller in ('No Name','No Name 😍','নো নেম'):
            self.assertEqual(rules.choose(calls.settings(),caller)['message'],'কালকে অফিসে যাবে না।')
        self.assertIsNone(rules.choose(calls.settings(),'Unknown'))
        self.assertIsNone(rules.choose(calls.settings(),'No Name other'))

    def test_local_incoming_name_works_without_online_vision(self):
        from types import SimpleNamespace
        self.save('নো নেম','Exact')
        c=Mock();c.window=SimpleNamespace(Name='Voice call')
        c.state.return_value='incoming'
        c.nodes.return_value=[SimpleNamespace(Name='No Name 😍',ControlTypeName='TextControl',IsOffscreen=False)]
        with patch.object(calls,'visual_controller') as online:
            self.assertEqual(rules.identity_key(rules.current_caller(c)),'noname')
        online.assert_not_called()

    def test_main_window_sidebar_name_cannot_supply_caller_identity(self):
        from types import SimpleNamespace
        from core.whatsapp_caller_identity import local_caller
        c=Mock();c.window=SimpleNamespace(Name='WhatsApp')
        with self.assertRaisesRegex(RuntimeError,'separate current call window'):local_caller(c,{})
        c.nodes.assert_not_called()

    def test_identification_failure_does_not_speak_default_instead_of_personal(self):
        import threading
        calls.update_settings(dict(auto_answer_enabled=True,auto_answer_message='Default',caller_rules=[dict(contact_name='No Name',message='Personal exact',enabled=True,expires_at=None,aliases=[])]))
        stop=threading.Event()
        async def hints():return ['toast:fixture']
        def report(phase,error=''):
            if phase=='caller_unidentified':stop.set()
        with patch.object(auto,'_stop',stop),patch.object(auto,'report',side_effect=report),patch.object(auto,'arm_expiry'),patch.object(auto,'notification_hints',hints),patch.object(auto,'window_hints',return_value=({42},set())),patch.object(calls,'audio_ready',return_value=dict(id=19,rate=48000,name='CABLE Input')),patch.object(calls,'synthesize',return_value=([0.1],48000,19)),patch.object(rules,'current_caller',side_effect=RuntimeError('unreadable')),patch.object(calls,'message_operation') as operation:
            auto.worker()
        operation.assert_not_called()

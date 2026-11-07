"""No live UI, notifications, calls, synthesis or device playback."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch
from core import whatsapp_auto_reply as auto,whatsapp_calls as calls
from plugins import whatsapp_desktop_call as plugin


class AutoReplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.config=Path(self.tmp.name)/'calls.json'
        self.patch=patch.object(calls,'CONFIG',self.config);self.patch.start()
        self.oldstate=dict(auto._state);auto._state.update(phase='disabled',watching=False,error='')
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup();auto._state.clear();auto._state.update(self.oldstate)
    def test_enabling_requires_exact_message_and_routing(self):
        with self.assertRaises(ValueError):auto.configure(True,'')
        with patch.object(calls,'audio_ready',side_effect=RuntimeError('routing missing')):
            with self.assertRaises(RuntimeError):auto.configure(True,'fixture')
        self.assertFalse(self.config.exists())
    def test_exact_message_and_enabled_state_persist(self):
        with patch.object(calls,'audio_ready'),patch.object(auto,'start') as start:
            result=auto.configure(True,'Exact fixture greeting')
            self.assertTrue(result['enabled']);start.assert_called_once()
            self.assertEqual(calls.settings()['auto_answer_message'],'Exact fixture greeting')
    def test_disable_preserves_message_and_does_not_hang_up(self):
        self.config.write_text(json.dumps(dict(auto_answer_enabled=True,auto_answer_message='fixture')))
        auto._state['phase']='handling'
        with patch.object(calls,'stop_speaking') as cancel,patch.object(calls,'control') as control:
            auto.configure(False)
            cancel.assert_called_once();control.assert_not_called()
            self.assertEqual(calls.settings()['auto_answer_message'],'fixture')
    def test_old_missed_video_and_other_apps_do_not_trigger(self):
        base=dict(app='WhatsApp',title='Incoming voice call',ts=990)
        self.assertTrue(auto.incoming_notification(base,1000))
        for change in (dict(ts=900),dict(app='Other'),dict(title='Missed incoming call'),dict(title='Incoming video call'),dict(title='New message'),dict(ts=1100)):
            self.assertFalse(auto.incoming_notification(dict(base,**change),1000))
    def test_schema_and_missing_message(self):
        enum=plugin.PLUGIN['parameters']['properties']['action']['enum']
        self.assertIn('enable_auto_reply',enum);self.assertIn('disable_auto_reply',enum)
        self.assertIn('exact message',plugin.run(dict(action='enable_auto_reply')))
    def test_incoming_hint_routes_only_answer_and_exact_prepared_audio(self):
        self.config.write_text(json.dumps(dict(auto_answer_enabled=True,auto_answer_message='fixture')))
        stop=threading.Event();prepared=([0.0],44100,6)
        async def hints():return ['toast:fixture']
        def operation(*args,**kwargs):
            stop.set();return dict(status='played_to_virtual_cable')
        with patch.object(auto,'_stop',stop),patch.object(calls,'audio_ready',return_value=dict(id=6,rate=44100,name='CABLE Input')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'synthesize',return_value=prepared),patch.object(auto,'window_hints',return_value=({42},set())),patch.object(auto,'notification_hints',hints),patch.object(calls,'message_operation',side_effect=operation) as handler:
            auto.worker()
            handler.assert_called_once_with('answer_and_say','','fixture',prepared_audio=prepared)
    def test_same_incoming_hint_not_repeated(self):
        self.config.write_text(json.dumps(dict(auto_answer_enabled=True,auto_answer_message='fixture')))
        stop=Mock();stop.is_set.return_value=False;rounds=[]
        def wait(*args):
            rounds.append(1)
            if len(rounds)>=3:stop.is_set.return_value=True
        stop.wait.side_effect=wait
        async def hints():return ['toast:fixture']
        with patch.object(auto,'_stop',stop),patch.object(calls,'audio_ready',return_value=dict(id=6,rate=44100,name='CABLE Input')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'synthesize',return_value=([],44100,6)),patch.object(auto,'window_hints',return_value=({42},{'uia:42'})),patch.object(auto,'notification_hints',hints),patch.object(calls,'message_operation',return_value=dict(status='played_to_virtual_cable')) as handler:
            auto.worker();handler.assert_called_once()
    def test_prepared_auto_audio_avoids_synthesis_after_answer(self):
        from contextlib import contextmanager
        c=Mock();c.state.return_value='connected_timer_visible'
        @contextmanager
        def controller():yield c
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=dict(id=6,rate=44100,name='CABLE Input')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'synthesize') as synth,patch.object(calls,'perform') as perform,patch.object(calls,'play_buffered',return_value={'complete':True}),patch('sounddevice.OutputStream'):
            result=calls.message_operation('answer_and_say','','fixture',prepared_audio=([],44100,6))
            self.assertEqual(result['status'],'played_to_virtual_cable')
            synth.assert_not_called();perform.assert_called_once_with(c,'answer_call')

class TimedAutoReplyTests(unittest.TestCase):
    setUp=AutoReplyTests.setUp
    tearDown=AutoReplyTests.tearDown
    def test_one_hour_rule_persists_exact_words_and_deadline(self):
        with patch.object(calls,'audio_ready'),patch.object(auto,'start'),patch.object(auto,'arm_expiry'),patch.object(auto.time,'time',return_value=1000):
            result=auto.configure(True,'Exact next-hour message',60)
            self.assertEqual(calls.settings()['auto_answer_expires_at'],4600)
            self.assertEqual(result['remaining_seconds'],3600)
            self.assertEqual(result['message'],'Exact next-hour message')
            self.assertTrue(result['expires_at'].endswith('+06:00'))
    def test_expired_rule_inactive_after_restart_without_waiting_timer(self):
        cfg=dict(auto_answer_enabled=True,auto_answer_expires_at=900)
        with patch.object(auto.time,'time',return_value=1000):self.assertFalse(auto.active(cfg))
    def test_invalid_duration_cannot_enable_rule(self):
        for value in (0,-1,True,1.5,'60',10081):
            with self.subTest(value=value),patch.object(calls,'audio_ready'),self.assertRaises(ValueError):auto.configure(True,'fixture',value)
    def test_expiry_disables_and_cancels_active_reply(self):
        self.config.write_text(json.dumps(dict(auto_answer_enabled=True,auto_answer_message='fixture',auto_answer_expires_at=2000)))
        auto._state['phase']='handling'
        with patch.object(auto.threading,'Timer') as timer,patch.object(calls,'stop_speaking') as cancel:
            auto.arm_expiry(calls.settings())
            timer.call_args.args[1]()
            self.assertFalse(calls.settings()['auto_answer_enabled']);cancel.assert_called_once()
    def test_plugin_passes_duration_with_exact_message(self):
        with patch.object(auto,'configure',return_value={'enabled':True}) as configure:
            plugin.run(dict(action='enable_auto_reply',message='fixture exact',duration_minutes=60))
            configure.assert_called_once_with(True,'fixture exact',60)
    def test_changing_message_cancels_outdated_audio(self):
        self.config.write_text(json.dumps(dict(auto_answer_enabled=True,auto_answer_message='old')))
        auto._state['phase']='handling'
        with patch.object(calls,'audio_ready'),patch.object(auto,'start'),patch.object(calls,'stop_speaking') as cancel:
            auto.configure(True,'new exact message');cancel.assert_called_once()

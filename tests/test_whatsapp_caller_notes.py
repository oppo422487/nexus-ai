"""Personal introduction and caller note fixtures. No live recording/calls."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch
import numpy as np
from core import whatsapp_caller_notes as notes,whatsapp_calls as calls,life_store as store


class CallerNotesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.patches=[patch.object(store,'DB',root/'notes.sqlite3'),patch.object(store,'DATA',root/'data'),patch.object(calls,'CONFIG',root/'calls.json')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def test_profile_name_is_dynamic_and_saved_message_preserved(self):
        cfg=dict(personal_intro_enabled=True,caller_notes_enabled=True)
        with patch('memory.config_manager.get_user_name',return_value='Fixture Owner'):
            text=notes.compose_message('Busy; call later.',cfg)
            self.assertIn('Fixture Owner',text);self.assertIn('Busy; call later.',text)
        with patch('memory.config_manager.get_user_name',return_value='Another Owner'):
            self.assertIn('Another Owner',notes.compose_message('fixture',cfg))
    def test_no_owner_name_is_invented(self):
        with patch('memory.config_manager.get_user_name',return_value=''):
            with self.assertRaises(ValueError):notes.compose_message('fixture',dict(personal_intro_enabled=True))
    def test_return_route_never_falls_back_to_room_mic(self):
        with patch.object(calls,'settings',return_value={}),patch.object(notes,'return_inputs') as inputs:
            with self.assertRaisesRegex(RuntimeError,'not confirmed'):notes.return_ready()
            inputs.assert_not_called()
    def test_silence_stops_after_initial_two_seconds(self):
        stream=Mock();stream.read.return_value=(np.zeros((100,1),dtype=np.float32),False)
        with patch('sounddevice.InputStream') as source:
            source.return_value.__enter__.return_value=stream
            samples,rate=notes.capture_reply(dict(id=7,rate=1000),threading.Event(),initial_wait=2)
        self.assertEqual(len(samples),0);self.assertLessEqual(stream.read.call_count,21)
        self.assertEqual(source.call_args.kwargs['device'],7)
    def test_reply_continues_until_two_seconds_of_silence(self):
        frames=[np.ones((100,1),dtype=np.float32)*.1]*5+[np.zeros((100,1),dtype=np.float32)]*25
        stream=Mock();stream.read.side_effect=[(f,False) for f in frames]
        with patch('sounddevice.InputStream') as source:
            source.return_value.__enter__.return_value=stream
            samples,rate=notes.capture_reply(dict(id=7,rate=1000),threading.Event())
        self.assertGreater(len(samples),2000);self.assertLess(stream.read.call_count,30)
    def test_no_reply_is_saved_truthfully_without_transcription(self):
        with patch.object(notes,'return_ready',return_value={'name':'Hi-Fi Cable Output','id':22,'rate':16000}),patch('core.whatsapp_call_audio.render_route_readiness',return_value={'ready':True}),patch.object(notes,'capture_reply',return_value=(np.empty(0,dtype=np.float32),16000)),patch.object(notes.threading,'Thread') as worker:
            result=notes.take_note()
        item=store.get(result['note_id']);self.assertEqual(item['payload']['transcription_status'],'no_signal');worker.assert_not_called()
    def test_atomic_note_updates_preserve_hangup_and_transcript(self):
        item=store.add('call_note','fixture',dict(transcription_status='pending'),status='unread')
        notes.patch_note(item['id'],dict(transcript='fixture reply',transcription_status='ready'))
        notes.patch_note(item['id'],dict(hangup_status='capture_ended'))
        data=store.get(item['id'])['payload'];self.assertEqual(data['transcript'],'fixture reply');self.assertEqual(data['hangup_status'],'capture_ended')
        self.assertEqual(len(notes.list_notes()),1);notes.mark_read(item['id']);self.assertEqual(notes.list_notes(),[])
    def test_hangup_is_a_new_action_not_a_retry_of_accept(self):
        c=Mock(external_action=True);c.end.side_effect=RuntimeError('uia end missing');visual=Mock(external_action=True);visual.action.return_value={'status':'requested'}
        with patch.object(calls,'visual_controller',return_value=visual):
            calls.perform(c,'end_call');visual.action.assert_called_once_with('end_call')

    def test_hifi_return_is_distinct_from_original_cable_output(self):
        devices=[{'name':'CABLE Output (VB-Audio)','max_input_channels':2,'default_samplerate':44100}, {'name':'Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)','max_input_channels':2,'default_samplerate':44100}, {'name':'Internal Microphone','max_input_channels':1,'default_samplerate':44100}]
        with patch.object(calls,'settings',return_value={'output_name':'CABLE Input'}),patch('sounddevice.query_devices',return_value=devices):
            result=notes.return_inputs()
            self.assertEqual(len(result),1);self.assertEqual(result[0]['id'],1)

    def test_delayed_caller_gets_a_chance_after_greeting(self):
        quiet=np.zeros((100,1),dtype=np.float32)
        voice=np.ones((100,1),dtype=np.float32)*.1
        stream=Mock();stream.read.side_effect=[(f,False) for f in [quiet]*30+[voice]*8+[quiet]*25]
        with patch('sounddevice.InputStream') as source:
            source.return_value.__enter__.return_value=stream
            samples,rate=notes.capture_reply(dict(id=7,rate=1000),threading.Event(),initial_wait=5)
        self.assertGreater(len(samples),2500)
        self.assertGreater(stream.read.call_count,50)

    def test_missing_return_endpoint_does_not_hang_up(self):
        with patch.object(notes,'return_ready',return_value={'name':'Hi-Fi Cable Output','id':22,'rate':16000}),patch('core.whatsapp_call_audio.render_route_readiness',return_value={'ready':False,'detail':'missing endpoint'}),patch.object(notes,'capture_reply') as capture:
            result=notes.take_note()
        with patch.object(calls,'perform') as action:
            notes.end_handled_call(Mock(),result)
        action.assert_not_called();capture.assert_not_called()
        self.assertEqual(result['hangup_status'],'manual_takeover')

    def test_inactive_but_available_return_route_still_listens_and_saves(self):
        samples=np.ones(1600,dtype=np.float32)*.1
        with patch.object(notes,'return_ready',return_value={'name':'Hi-Fi Cable Output','id':22,'rate':16000}),patch('core.whatsapp_call_audio.render_route_readiness',return_value={'ready':True,'active':False}),patch.object(notes,'capture_reply',return_value=(samples,16000)) as capture,patch.object(notes,'queue_transcription') as transcribe:
            result=notes.take_note()
        self.assertEqual(capture.call_args.kwargs['initial_wait'],15)
        item=store.get(result['note_id'])
        self.assertTrue(Path(item['payload']['audio_path']).is_file())
        self.assertEqual(result['caller_reply'],'pending');transcribe.assert_called_once()

    def test_quiet_right_channel_caller_is_recorded(self):
        voice=np.column_stack([np.zeros(100),np.ones(100)*.001]).astype(np.float32)
        quiet=np.zeros((100,2),dtype=np.float32)
        stream=Mock();stream.read.side_effect=[(f,False) for f in [quiet]*70+[voice]*6+[quiet]*25]
        with patch('sounddevice.InputStream') as source:
            source.return_value.__enter__.return_value=stream
            samples,rate=notes.capture_reply(dict(id=22,rate=1000,channels=2),threading.Event())
        self.assertGreater(float(samples.max()),.0009)
        self.assertGreater(stream.read.call_count,90)
        self.assertEqual(source.call_args.kwargs['channels'],2)

    def test_silent_return_cable_never_triggers_automatic_hangup(self):
        item=store.add('call_note','fixture',dict(transcription_status='no_reply'),status='unread')
        outcome=dict(note_id=item['id'],caller_reply='no_reply')
        with patch.object(calls,'perform') as action:
            notes.end_handled_call(Mock(),outcome)
        action.assert_not_called()
        self.assertEqual(outcome['hangup_status'],'manual_takeover')
        self.assertEqual(store.get(item['id'])['payload']['hangup_status'],'manual_takeover')

    def test_saved_reply_transcription_is_exposed_as_ready_note(self):
        import wave
        from unittest.mock import AsyncMock
        path=Path(self.tmp.name)/'caller.wav'
        with wave.open(str(path),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\x00\x00'*1600)
        item=store.add('call_note','fixture',dict(transcription_status='pending',audio_path=str(path)),status='unread')
        with patch.object(notes,'transcribe',new=AsyncMock(return_value='Please call me later.')),patch('core.whatsapp_auto_reply._log') as notify:
            notes.finish_transcription(item['id'],path)
        payload=notes.list_notes()[0]['payload']
        self.assertEqual(payload['transcription_status'],'ready');self.assertEqual(payload['transcript'],'Please call me later.')
        notify.assert_called_once()

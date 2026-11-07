"""Regressions for pre-speech hangup, buffering and persistent diagnostics."""
import tempfile
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace as S
import threading
import unittest
from unittest.mock import Mock,patch
import numpy as np
import sounddevice as sd
from core import whatsapp_calls as calls,call_diagnostics as diag


class FakeStream:
    def __init__(self,**kwargs):self.kwargs=kwargs;self.blocks=[]
    def __enter__(self):self.start();return self
    def close(self):pass
    def start(self):
        for i in range(100):
            block=np.empty((8,self.kwargs['channels']),dtype=np.float32)
            try:self.kwargs['callback'](block,8,None,S(output_underflow=i==0))
            except (sd.CallbackStop,sd.CallbackAbort):
                self.blocks.append(block.copy());break
            self.blocks.append(block.copy())
        self.kwargs['finished_callback']();return self
    def __exit__(self,*args):pass
    def abort(self):self.kwargs['finished_callback']()


class CallCompletionTests(unittest.TestCase):
    def test_callback_buffers_exact_audio_despite_initial_underflow(self):
        created=[]
        def stream(**kw):obj=FakeStream(**kw);created.append(obj);return obj
        samples=np.arange(19,dtype=np.float32)/20
        with patch('sounddevice.OutputStream',side_effect=stream):
            result=calls.play_buffered(samples,44100,6,threading.Event())
        played=np.concatenate(created[0].blocks).reshape(-1)
        np.testing.assert_array_equal(played[:19],samples)
        self.assertTrue(result['complete']);self.assertEqual(result['underflows'],1)
        self.assertEqual(created[0].kwargs['device'],6)
    def test_empty_audio_does_not_open_device(self):
        with patch('sounddevice.OutputStream') as stream:
            with self.assertRaisesRegex(RuntimeError,'empty'):calls.play_buffered([],44100,6,threading.Event())
            stream.assert_not_called()
    def test_cancelled_buffer_does_not_claim_complete(self):
        cancelled=threading.Event();cancelled.set()
        with patch('sounddevice.OutputStream',side_effect=lambda **kw:FakeStream(**kw)):
            self.assertFalse(calls.play_buffered([0.1]*16,44100,6,cancelled)['complete'])
    def test_accepted_call_is_not_hung_up_when_microphone_wrong(self):
        @contextmanager
        def controller():yield Mock()
        cleanup=Mock();caller=Mock()
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value={'name':'CABLE Input','id':6,'rate':44100}),patch.object(calls,'perform'),patch('core.whatsapp_call_audio.readiness',return_value={'ready':False,'reason':'wrong_microphone','detail':'wrong route'}),patch.object(calls,'play_buffered') as play:
            result=calls.message_operation('answer_and_say','','fixture',prepared_audio=([.1],44100,6),incoming_handler=caller,cleanup_handler=cleanup)
        self.assertTrue(result['accepted']);self.assertFalse(result['playback_complete'])
        cleanup.assert_not_called();caller.assert_not_called();play.assert_not_called()
    def test_playback_error_does_not_run_hangup_cleanup(self):
        @contextmanager
        def controller():yield Mock()
        device={'name':'CABLE Input','id':6,'rate':44100};cleanup=Mock()
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=device),patch.object(calls,'perform'),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'play_buffered',side_effect=RuntimeError('fixture audio failure')):
            with self.assertRaisesRegex(RuntimeError,'fixture audio failure') as caught:
                calls.message_operation('answer_and_say','','fixture',prepared_audio=([.1],44100,6),cleanup_handler=cleanup)
        self.assertTrue(caught.exception.accepted);cleanup.assert_not_called()
        calls.reserve();calls.release()
    def test_note_failure_after_speech_still_requests_authorized_hangup(self):
        @contextmanager
        def controller():yield Mock()
        device={'name':'CABLE Input','id':6,'rate':44100};cleanup=Mock()
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=device),patch.object(calls,'perform'),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'play_buffered',return_value={'complete':True}),patch('core.whatsapp_call_audio.monitor_capture') as monitor:
            monitor.return_value.__enter__.return_value=threading.Event()
            with self.assertRaisesRegex(RuntimeError,'note failure'):
                calls.message_operation('answer_and_say','','fixture',prepared_audio=([.1],44100,6),incoming_handler=Mock(side_effect=RuntimeError('note failure')),cleanup_handler=cleanup)
        cleanup.assert_called_once()
    def test_diagnostics_persist_without_console(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(diag,'PATH',Path(folder)/'events.jsonl'),patch('sys.stdout',None):
            diag.event('fixture',stage='playback')
            self.assertIn('playback',diag.PATH.read_text(encoding='utf-8'))
    def test_new_caller_is_not_blocked_for_a_minute(self):
        from core import whatsapp_auto_reply as auto
        import json
        clock=[0];waits=[0];hint=[0];stop=Mock();stop.is_set.return_value=False
        def wait(seconds):
            waits[0]+=1;clock[0]+=4
            if waits[0]>4:stop.is_set.return_value=True
        stop.wait.side_effect=wait
        async def hints():hint[0]+=1;return ['toast:'+str(hint[0])]
        def handle(*args,**kwargs):
            if hint[0]>=2:stop.is_set.return_value=True
            return {'status':'played_to_virtual_cable','accepted':True,'playback_complete':True}
        with tempfile.TemporaryDirectory() as folder:
            config=Path(folder)/'calls.json';config.write_text(json.dumps({'auto_answer_enabled':True,'auto_answer_message':'fixture'}))
            before=dict(auto._state)
            try:
                with patch.object(calls,'CONFIG',config),patch.object(auto,'_stop',stop),patch.object(auto,'arm_expiry'),patch.object(auto.time,'monotonic',side_effect=lambda:clock[0]),patch.object(calls,'audio_ready',return_value={'id':6,'rate':44100,'name':'CABLE Input'}),patch.object(calls,'synthesize',return_value=([.1],44100,6)),patch.object(auto,'window_hints',return_value=({42},set())),patch.object(auto,'notification_hints',hints),patch.object(calls,'message_operation',side_effect=handle) as handler:
                    auto.worker();self.assertEqual(handler.call_count,2)
            finally:auto._state.clear();auto._state.update(before)
    def test_selected_mme_alias_resolves_only_to_same_shared_cable(self):
        cfg={'microphone_routed':True,'output_name':'CABLE Input (VB-Audio Virtual C','output_id':6}
        endpoints=[{'id':6,'name':cfg['output_name'],'rate':44100,'api':'MME','channels':2},{'id':19,'name':'CABLE Input (VB-Audio Virtual Cable)','rate':48000,'api':'Windows WASAPI','channels':2},{'id':20,'name':'Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)','rate':44100,'api':'Windows WASAPI','channels':2}]
        with patch.object(calls,'settings',return_value=cfg),patch.object(calls,'audio_outputs',return_value=endpoints):
            device=calls.audio_ready();self.assertEqual(device['id'],19);self.assertEqual(device['rate'],48000)
    def test_preflight_opens_closes_without_starting_or_writing(self):
        with patch('sounddevice.OutputStream') as stream:
            calls.preflight_playback({'id':19,'rate':48000,'channels':2})
            stream.return_value.start.assert_not_called();stream.return_value.write.assert_not_called()
            stream.return_value.__enter__.assert_not_called();stream.return_value.close.assert_called_once()
    def test_unavailable_output_is_reported_before_accept(self):
        device={'id':19,'rate':48000,'channels':2}
        with patch.object(calls,'audio_ready',return_value=device),patch('sounddevice.OutputStream',side_effect=RuntimeError('Device unavailable -9985')),patch.object(calls,'controller') as controller:
            with self.assertRaisesRegex(RuntimeError,'output_preflight') as error:
                calls.message_operation('answer_and_say','','fixture',prepared_audio=([.1]*16,48000,19))
            controller.assert_not_called();self.assertFalse(error.exception.accepted)
    def test_stereo_callback_duplicates_mono_without_changing_timing(self):
        created=[]
        def stream(**kw):obj=FakeStream(**kw);created.append(obj);return obj
        samples=np.arange(19,dtype=np.float32)/20
        with patch('sounddevice.OutputStream',side_effect=stream):
            self.assertTrue(calls.play_buffered(samples,48000,19,threading.Event(),channels=2)['complete'])
        stereo=np.concatenate(created[0].blocks)
        np.testing.assert_array_equal(stereo[:19,0],samples)
        np.testing.assert_array_equal(stereo[:19,1],samples)
    def test_wasapi_settings_are_shared_and_allow_engine_conversion(self):
        with patch('sounddevice.WasapiSettings',return_value='fixture') as setting:
            options=calls.playback_kwargs({'id':19,'rate':48000,'channels':2,'api':'Windows WASAPI'})
            setting.assert_called_once_with(exclusive=False,auto_convert=True)
            self.assertEqual(options['channels'],2);self.assertEqual(options['extra_settings'],'fixture')
    def test_exact_preopened_callback_stream_is_started_after_accept_without_reopen(self):
        events=[];opened=[]
        class OrderedStream(FakeStream):
            def __init__(self,**kw):super().__init__(**kw);events.append('open');opened.append(self)
            def start(self):events.append('play');super().start()
            def close(self):events.append('close')
        @contextmanager
        def controller():yield Mock()
        device={'id':19,'rate':48000,'name':'CABLE Input','channels':2}
        with patch.object(calls,'audio_ready',return_value=device),patch.object(calls,'controller',controller),patch.object(calls,'perform',side_effect=lambda *a:events.append('accept')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch('core.whatsapp_call_audio.monitor_capture') as monitor,patch('sounddevice.OutputStream',side_effect=lambda **kw:OrderedStream(**kw)) as constructor:
            monitor.return_value.__enter__.return_value=threading.Event()
            result=calls.message_operation('answer_and_say','','fixture',prepared_audio=([.1]*16,48000,19))
        self.assertEqual(events,['open','accept','play','close'])
        constructor.assert_called_once();self.assertTrue(result['playback_complete'])

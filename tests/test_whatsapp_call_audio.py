"""Local capture metadata policy, no live calls/audio/UI."""
import unittest
from unittest.mock import Mock,patch
from core import whatsapp_call_audio as audio,whatsapp_calls as calls


class CaptureReadinessTests(unittest.TestCase):
    def test_only_expected_live_cable_reader_is_ready(self):
        self.assertTrue(audio.evaluate([dict(endpoint='CABLE Output (VB Audio)',active=True,muted=False)],'CABLE Input')['ready'])
    def test_inactive_or_other_microphone_is_not_ready(self):
        self.assertFalse(audio.evaluate([dict(endpoint='CABLE Output',active=False)],'CABLE Input')['ready'])
        self.assertEqual(audio.evaluate([dict(endpoint='Internal Microphone',active=True)],'CABLE Input')['reason'],'wrong_microphone')
    def test_muted_capture_cannot_claim_ready(self):
        self.assertEqual(audio.evaluate([dict(endpoint='CABLE Output',active=True,muted=True)],'CABLE Input')['reason'],'muted')
    def test_voicemeeter_aux_does_not_match_main_output(self):
        self.assertFalse(audio.evaluate([dict(endpoint='Voicemeeter Output',active=True)],'Voicemeeter AUX Input')['ready'])
    def test_incoming_playback_uses_capture_proof_without_cloud_or_reaccept(self):
        from contextlib import contextmanager
        c=Mock();c.window.NativeWindowHandle=42
        @contextmanager
        def controller():yield c
        device=dict(id=6,rate=44100,name='CABLE Input')
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=device),patch.object(calls,'perform') as accept,patch.object(calls,'call_state') as cloud_state,patch.object(audio,'readiness',return_value=dict(ready=True,detail='fixture')) as readiness,patch('core.whatsapp_call_vision.window_rect') as old_popup,patch.object(calls,'play_buffered',return_value={'complete':True}) as player,patch('sounddevice.OutputStream') as stream:
            result=calls.message_operation('answer_and_say','','fixture',prepared_audio=([0.0]*16,44100,6))
            self.assertEqual(result['status'],'played_to_virtual_cable')
            accept.assert_called_once_with(c,'answer_call');cloud_state.assert_not_called();old_popup.assert_not_called()
            self.assertEqual(readiness.call_count,2)
            player.assert_called_once()
    def test_wrong_whatsapp_microphone_does_not_play_to_nowhere(self):
        from contextlib import contextmanager
        @contextmanager
        def controller():yield Mock()
        with patch.object(calls,'controller',controller),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=dict(name='CABLE Input',id=6,rate=44100)),patch.object(calls,'perform'),patch.object(audio,'readiness',return_value=dict(ready=False,reason='wrong_microphone',detail='Select CABLE Output')),patch.object(calls,'play_buffered',return_value={'complete':True}) as player,patch('sounddevice.OutputStream') as stream:
            result=calls.message_operation('answer_and_say','','fixture',prepared_audio=([],44100,6))
            self.assertEqual(result['status'],'not_played');self.assertIn('CABLE Output',result['detail']);stream.assert_not_called()
    def test_com_failure_before_click_can_use_visual_fallback_once(self):
        c=Mock(external_action=False);c.answer.side_effect=calls.COMError(-2147220991,'stale',None)
        v=Mock(external_action=True);v.action.return_value={'status':'requested'}
        with patch.object(calls,'visual_controller',return_value=v):
            self.assertEqual(calls.perform(c,'answer_call')['status'],'requested');v.action.assert_called_once_with('answer_call')
    def test_uncertain_com_click_is_not_repeated(self):
        c=Mock(external_action=True)
        def uncertain():
            c.external_action=True
            raise calls.COMError(-2147220991,'uncertain',None)
        c.answer.side_effect=uncertain
        with patch.object(calls,'visual_controller') as fallback:
            with self.assertRaises(calls.COMError):calls.perform(c,'answer_call')
            fallback.assert_not_called()

    def test_broken_uia_can_attach_to_exact_native_whatsapp_window(self):
        auto=Mock();auto.GetRootControl.side_effect=calls.COMError(-2147220991,'stale',None)
        c=calls.Controller(auto)
        with patch('core.windows_whatsapp.owned_pids',return_value={7}),patch('core.windows_whatsapp.visible_windows',return_value=[{'hwnd':42,'pid':7}]),patch('core.whatsapp_call_vision.focus_window') as focus:
            c.attach();self.assertEqual(c.window.NativeWindowHandle,42)
            self.assertEqual(c.nodes(),[]);focus.assert_called_once_with(42)
    def test_capture_reader_loss_is_reported_off_audio_thread(self):
        with patch.object(audio,'readiness',return_value={'ready':False}) as read:
            with audio.monitor_capture('fixture') as lost:
                self.assertTrue(lost.wait(2))
            read.assert_called_once_with('fixture')

    def test_return_cable_speakers_alias_does_not_match_physical_or_outbound(self):
        recording='Hi-Fi Cable Output (VB-Audio Hi-Fi Cable)'
        self.assertTrue(audio.return_endpoint_matches(recording,'Speakers (VB-Audio Hi-Fi Cable)'))
        self.assertTrue(audio.return_endpoint_matches(recording,'Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)'))
        self.assertFalse(audio.return_endpoint_matches(recording,'Speakers (2- Conexant ISST Audio)'))
        self.assertFalse(audio.return_endpoint_matches(recording,'CABLE Input (VB-Audio Virtual Cable)'))
        self.assertFalse(audio.return_endpoint_matches('Internal Microphone','Speakers'))

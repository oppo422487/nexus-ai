"""Call pipeline regression checks: mocked UI/provider/audio, no real calls."""
import sys
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch
from core import whatsapp_calls as calls
from core import whatsapp_call_vision as vision
from plugins import whatsapp_desktop_call as plugin


def plan(**kw):
    data=dict(is_whatsapp=True,state='chat',recipient='Fixture',box=[800,30,850,80],
              ambiguous=False,evidence='synthetic',control_text='Fixture')
    data.update(kw)
    return vision.validate(data)


class VisualRegressionTests(unittest.TestCase):
    def setUp(self):
        calls._cancel.clear()

    def test_bad_provider_bounds_never_become_clicks(self):
        for box in ([0,0,1001,20],[20,0,10,10],[0,0,float('nan'),10],[False,0,10,10]):
            with self.subTest(box=box),self.assertRaises(RuntimeError):plan(box=box)

    def test_unknown_provider_identity_fails_closed(self):
        c=vision.VisualController(42)
        with patch.object(vision,'capture'),patch.object(vision,'analyze',return_value=plan(is_whatsapp=False)):
            with self.assertRaises(RuntimeError):c.observe()

    def test_recipient_mismatch_never_clicks(self):
        c=vision.VisualController(42);c.observe=Mock(return_value=(Mock(),plan(recipient='Other')))
        with patch('pyautogui.click') as click:
            with self.assertRaisesRegex(RuntimeError,'recipient'):c.click('voice_call','Fixture')
            click.assert_not_called()

    def test_search_result_requires_exact_row_label(self):
        c=vision.VisualController(42);c.observe=Mock(return_value=(Mock(),plan(control_text='Other')))
        with self.assertRaisesRegex(RuntimeError,'Search result'):c.click('search_result','Fixture')

    def test_two_observations_must_agree(self):
        c=vision.VisualController(42)
        c.observe=Mock(side_effect=[(Mock(),plan()),(Mock(),plan(recipient='Other'))])
        with patch('pyautogui.click') as click:
            with self.assertRaisesRegex(RuntimeError,'changed'):c.click('voice_call','Fixture')
            click.assert_not_called()

    def test_verified_call_click_once_and_marks_unknown_outcome(self):
        frame=vision.Frame(None,(0,0,1000,700),42,vision.time.monotonic())
        c=vision.VisualController(42);c.observe=Mock(return_value=(frame,plan()))
        with patch.object(vision,'require_foreground'),patch.object(vision,'window_rect',return_value=frame.rect),patch('pyautogui.click',side_effect=RuntimeError('click uncertain')) as click:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):c.click('voice_call','Fixture')
            self.assertTrue(c.external_action);click.assert_called_once()
            self.assertEqual(c.observe.call_count,2)

    def test_answer_needs_current_incoming_state(self):
        c=vision.VisualController(42);c.observe=Mock(return_value=(Mock(),plan(state='chat')))
        with self.assertRaisesRegex(RuntimeError,'incoming'):c.action('answer_call')

    def test_formatting_contact_key(self):
        self.assertEqual(vision.contact_key('sAd_mAn'),vision.contact_key('Sadman'))


class PipelineRegressionTests(unittest.TestCase):
    def test_empty_accessibility_tree_routes_to_verified_visual(self):
        c=Mock(external_action=False);c.dial.side_effect=RuntimeError('search missing')
        v=Mock(external_action=True);v.dial.return_value={'status':'requested'}
        with patch.object(calls,'visual_controller',return_value=v):
            self.assertEqual(calls.perform(c,'voice_call','Fixture')['status'],'requested')
            v.dial.assert_called_once_with('Fixture');self.assertTrue(c.external_action)

    def test_uncertain_accessible_click_is_never_retried(self):
        c=Mock(external_action=True)
        def uncertain(contact):
            c.external_action=True
            raise RuntimeError('click failed')
        c.dial.side_effect=uncertain
        with patch.object(calls,'visual_controller') as fallback:
            with self.assertRaises(RuntimeError):calls.perform(c,'voice_call','Fixture')
            fallback.assert_not_called()

    def test_connected_visual_state_translated_for_audio_pipeline(self):
        c=Mock();c.state.return_value='unknown';v=Mock();v.state.return_value='connected'
        with patch.object(calls,'visual_controller',return_value=v):
            self.assertEqual(calls.call_state(c),'connected_timer_visible')

    def test_duplicate_job_rejected_before_thread_creation(self):
        calls.reserve()
        try:
            with patch.object(calls,'audio_ready'),patch.object(plugin.threading,'Thread') as thread:
                result=plugin.run(dict(action='speak_in_call',message='fixture'))
                self.assertIn('already running',result);thread.assert_not_called()
        finally:calls.release()

    def test_thread_start_failure_releases_reservation(self):
        with patch.object(calls,'audio_ready'),patch.object(plugin.threading,'Thread') as thread:
            thread.return_value.start.side_effect=RuntimeError('thread failed')
            self.assertIn('thread failed',plugin.run(dict(action='speak_in_call',message='fixture')))
        calls.reserve();calls.release()

    def test_current_call_speech_uses_only_configured_cable_and_never_dials(self):
        c=Mock();c.state.return_value='connected_timer_visible';c.window.NativeWindowHandle=42
        @contextmanager
        def context():yield c
        device=dict(id=6,rate=44100)
        with patch.object(calls,'controller',context),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=device),patch.object(calls,'synthesize',return_value=([0.0]*16,44100,6)),patch.object(calls,'perform') as perform,patch.object(vision,'window_rect'),patch.object(calls,'play_buffered',return_value={'complete':True}) as player,patch('sounddevice.OutputStream') as output:
            result=calls.message_operation('speak_in_call','','fixture')
            self.assertEqual(result['status'],'played_to_virtual_cable')
            perform.assert_not_called();self.assertEqual(player.call_args.args[1:3],(44100,6))
            player.assert_called_once()

    def test_unconnected_current_call_never_dials_or_plays(self):
        c=Mock();c.state.return_value='ringing'
        @contextmanager
        def context():yield c
        with patch.object(calls,'controller',context),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value={'id':6,'rate':44100}),patch.object(calls,'synthesize',return_value=([],44100,6)),patch.object(calls,'perform') as perform,patch.object(calls,'play_buffered',return_value={'complete':True}) as player,patch('sounddevice.OutputStream') as output:
            result=calls.message_operation('speak_in_call','','fixture')
            self.assertEqual(result['status'],'not_played');perform.assert_not_called();output.assert_not_called()

    def test_answer_and_say_routes_once_then_verifies_connection(self):
        c=Mock();c.state.return_value='connected_timer_visible'
        @contextmanager
        def context():yield c
        with patch.object(calls,'controller',context),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=dict(id=6,rate=44100,name='CABLE Input')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'synthesize',return_value=([],44100,6)),patch.object(calls,'perform') as perform,patch.object(calls,'play_buffered',return_value={'complete':True}),patch('sounddevice.OutputStream'):
            result=calls.message_operation('answer_and_say','','fixture')
            self.assertEqual(result['status'],'played_to_virtual_cable');perform.assert_called_once_with(c,'answer_call')

    def test_missing_dependency_reports_stage_and_releases_operation(self):
        with patch.object(calls,'audio_ready'),patch.object(calls,'synthesize',side_effect=ImportError('fixture missing')):
            with self.assertRaisesRegex(RuntimeError,'synthesis failed'):calls.message_operation('speak_in_call','','fixture')
        calls.reserve();calls.release()

    def test_new_actions_reachable_in_model_tool_schema(self):
        enum=plugin.PLUGIN['parameters']['properties']['action']['enum']
        self.assertIn('speak_in_call',enum);self.assertIn('answer_and_say',enum)

    def test_existing_accessible_call_blocks_redial(self):
        c=Mock(external_action=False);c.state.return_value='connected_timer_visible'
        with self.assertRaisesRegex(ValueError,'already present'):calls.perform(c,'voice_call','Fixture')
        c.dial.assert_not_called()

    def test_synthesis_precedes_accept_to_avoid_an_empty_call(self):
        c=Mock();c.state.return_value='connected_timer_visible';order=[]
        @contextmanager
        def context():yield c
        with patch.object(calls,'controller',context),patch.object(calls,'preflight_playback'),patch.object(calls,'audio_ready',return_value=dict(id=6,rate=44100,name='CABLE Input')),patch('core.whatsapp_call_audio.readiness',return_value={'ready':True,'detail':'fixture'}),patch.object(calls,'perform',side_effect=lambda *a:order.append('accept')),patch.object(calls,'synthesize',side_effect=lambda m:(order.append('synth') or ([],44100,6))),patch.object(calls,'play_buffered',return_value={'complete':True}),patch('sounddevice.OutputStream'):
            calls.message_operation('answer_and_say','','fixture')
        self.assertEqual(order,['synth','accept'])

class LogRepairTests(unittest.TestCase):
    def test_sdk_parsed_json_is_used_without_text(self):
        from types import SimpleNamespace
        response=SimpleNamespace(parsed=plan(),text=None)
        self.assertEqual(vision.parse_response(response,'inspect')['recipient'],'Fixture')

    def test_part_text_fallback_ignores_thought_parts(self):
        import json
        from types import SimpleNamespace as S
        response=S(parsed=None,text='',candidates=[S(content=S(parts=[S(text='private thought',thought=True),S(text=json.dumps(plan()),thought=False)]))])
        self.assertEqual(vision.parse_response(response,'inspect')['state'],'chat')

    def test_malformed_reply_logs_metadata_without_chat_text(self):
        from types import SimpleNamespace as S
        response=S(parsed=None,text='private fixture invalid JSON',candidates=[S(finish_reason='MAX_TOKENS')])
        with patch('builtins.print') as log:
            with self.assertRaisesRegex(RuntimeError,'MAX_TOKENS'):vision.parse_response(response,'voice_call')
            self.assertNotIn('private fixture',str(log.call_args))

    def test_empty_vision_reply_continues_to_next_model(self):
        from core import gemini
        from types import SimpleNamespace as S
        client=Mock()
        client.models.generate_content.side_effect=[S(text='',parsed=None,candidates=[S(finish_reason='MAX_TOKENS')]),S(text='{}',parsed=None)]
        with patch.dict(gemini._LADDERS,{gemini.VISION:('fixture1','fixture2')}),patch.object(gemini,'_provider_rungs',return_value=()),patch.object(gemini,'_cooling',return_value=False),patch.object(gemini,'client',return_value=client):
            self.assertEqual(gemini.call('synthetic',tier=gemini.VISION,key='fixture-key').text,'{}')
            self.assertEqual(client.models.generate_content.call_count,2)

    def test_exact_window_activation_uses_foreground_thread_then_detaches(self):
        import ctypes
        user=Mock();kernel=Mock();kernel.GetCurrentThreadId.return_value=10
        user.IsWindow.return_value=True;user.IsIconic.return_value=False
        user.SetForegroundWindow.side_effect=[False,True]
        def process(hwnd,ptr):
            if ptr is not None:ptr._obj.value=7
            return 20
        user.GetWindowThreadProcessId.side_effect=process
        with patch.object(vision.ctypes,'WinDLL',side_effect=[user,kernel]),patch('core.windows_whatsapp.owned_pids',return_value={7}),patch.object(vision,'foreground_handle',side_effect=[1,1,42]),patch.object(vision,'require_foreground') as require:
            vision.focus_window(42)
            self.assertEqual(user.SetForegroundWindow.call_args_list,[( (42,),{}),((42,),{})])
            user.AttachThreadInput.assert_any_call(10,20,True)
            user.AttachThreadInput.assert_any_call(10,20,False)
            require.assert_called_once_with(42)

    def test_non_whatsapp_window_cannot_be_activated(self):
        user=Mock();kernel=Mock()
        def process(hwnd,ptr):ptr._obj.value=99;return 2
        user.GetWindowThreadProcessId.side_effect=process
        with patch.object(vision.ctypes,'WinDLL',side_effect=[user,kernel]),patch('core.windows_whatsapp.owned_pids',return_value={7}):
            with self.assertRaisesRegex(RuntimeError,'not owned'):vision.focus_window(42)
            user.SetForegroundWindow.assert_not_called()

    def test_busy_status_reports_operation_not_connected_call(self):
        calls.reserve()
        try:
            with patch.object(calls,'controller') as ui:
                result=calls.control('status')
                self.assertEqual(result['state'],'unknown')
                self.assertTrue(result['operation_in_progress'])
                self.assertIn('NOT evidence',result['detail'])
                ui.assert_not_called()
        finally:calls.release()

"""No live calls, UI clicks, cloud audio requests or device playback."""
import unittest
from unittest.mock import Mock, patch
from core import whatsapp_calls as calls
from plugins import whatsapp_desktop_call as plugin


class WhatsAppCallsTests(unittest.TestCase):
    def test_already_open_verified_contact_needs_no_search(self):
        c=calls.Controller(Mock());button=Mock()
        c.recipient_button=Mock(return_value=button);c.select_contact=Mock()
        self.assertEqual(c.dial('fixture')['status'],'requested')
        c.select_contact.assert_not_called();button.Click.assert_called_once()

    def test_unverified_open_chat_requires_search_and_reverification(self):
        c=calls.Controller(Mock());button=Mock()
        c.recipient_button=Mock(side_effect=[RuntimeError('wrong chat'),button]);c.select_contact=Mock()
        c.dial('fixture');c.select_contact.assert_called_once_with('fixture');button.Click.assert_called_once()

    def test_only_virtual_playback_endpoints_accepted(self):
        self.assertTrue(calls.is_virtual('CABLE Input (VB-Audio Virtual Cable)'))
        self.assertFalse(calls.is_virtual('CABLE Output'))
        self.assertFalse(calls.is_virtual('Speakers (Realtek Audio)'))

    def test_missing_routing_blocks_before_dial_or_synthesis(self):
        with patch.object(calls,'settings',return_value={}),patch.object(calls,'controller') as controller,patch.object(calls,'synthesize') as synth:
            with self.assertRaisesRegex(RuntimeError,'WhatsApp Audio settings'):
                calls.call_and_say('fixture','fixture')
            controller.assert_not_called();synth.assert_not_called()

    def test_device_identity_must_match_saved_name_and_index(self):
        endpoints=[{'id':3,'name':'CABLE Input','rate':48000},{'id':7,'name':'CABLE Input','rate':48000}]
        with patch.object(calls,'settings',return_value={'microphone_routed':True,'output_name':'CABLE Input','output_id':7}),patch.object(calls,'audio_outputs',return_value=endpoints):
            self.assertEqual(calls.audio_ready()['id'],7)

    def test_stale_or_ambiguous_audio_device_fails(self):
        with patch.object(calls,'settings',return_value={'microphone_routed':True,'output_name':'old','output_id':7}),patch.object(calls,'audio_outputs',return_value=[]):
            with self.assertRaisesRegex(RuntimeError,'missing or ambiguous'):calls.audio_ready()

    def test_no_call_without_exact_contact(self):
        with patch.object(calls,'control') as control:
            self.assertIn('exact saved contact',plugin.run({'action':'voice_call'}))
            control.assert_not_called()

    def test_missing_audio_reports_without_background_call(self):
        with patch.object(calls,'audio_ready',side_effect=RuntimeError('cable missing')),patch.object(plugin.threading,'Thread') as worker:
            result=plugin.run({'action':'call_and_say','contact_name':'fixture','message':'fixture'})
            self.assertIn('cable missing',result);worker.assert_not_called()

    def test_end_call_button_alone_is_not_answer_evidence(self):
        auto=Mock();c=calls.Controller(auto);c.window=Mock()
        button=Mock(Name='End call',ControlTypeName='ButtonControl',IsOffscreen=False)
        button.GetParentControl.return_value=c.window
        c.nodes=lambda:[button]
        self.assertEqual(c.state(),'unknown')

    def test_chat_timestamp_does_not_count_as_call_timer(self):
        auto=Mock();c=calls.Controller(auto);c.window=Mock()
        end=Mock(Name='End call',ControlTypeName='ButtonControl',IsOffscreen=False)
        end.GetParentControl.return_value=c.window
        stamp=Mock(Name='12:45',ControlTypeName='TextControl',IsOffscreen=False)
        c.nodes=lambda:[end,stamp]
        self.assertEqual(c.state(),'unknown')

    def test_verified_recipient_header_required_before_dial_click(self):
        c=calls.Controller(Mock());c.window=Mock();c.select_contact=Mock()
        button=Mock();button.GetParentControl.return_value=c.window;c.button=Mock(return_value=button)
        with self.assertRaisesRegex(RuntimeError,'recipient'):c.dial('fixture')
        button.Click.assert_not_called()

    def test_incoming_answer_requires_visible_incoming_state(self):
        c=calls.Controller(Mock());c.state=Mock(return_value='unknown');c.button=Mock()
        with self.assertRaisesRegex(RuntimeError,'incoming'):c.answer()
        c.button.assert_not_called()

    def test_cancellation_does_not_stop_global_audio(self):
        with patch('sounddevice.stop') as stop:
            self.assertEqual(calls.stop_speaking()['status'],'cancel_requested')
            stop.assert_not_called()

    def test_normal_manual_call_control_routes_unchanged(self):
        with patch.object(calls,'control',return_value={'status':'requested'}) as control:
            self.assertIn('requested',plugin.run({'action':'voice_call','contact_name':'fixture'}))
            control.assert_called_once_with('voice_call','fixture')

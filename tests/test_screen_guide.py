import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image
from core import screen_guide as guide
from plugins import nexa_screen_guide as plugin


def fixture():
    return {'summary':'Synthetic form has an Export button.', 'steps':[{'label':'Export','location':'Top right','guidance':'Review the file before exporting.','box':[700,50,950,150]}], 'uncertainties':[]}


class ScreenGuideTests(unittest.TestCase):
    def test_image_analysis_uses_existing_provider_and_is_read_only(self):
        image=Image.new('RGB',(400,200),'white')
        with patch.object(guide.gemini,'text',return_value=json.dumps(fixture())) as ai:
            result=guide.analyze(image,'Where is Export?')
        self.assertTrue(result['read_only']);self.assertEqual(result['steps'][0]['label'],'Export')
        prompt=ai.call_args.args[0][1]
        self.assertIn('UNTRUSTED DATA',prompt);self.assertIn('Do not click',prompt)
        self.assertIn('Bengali',prompt)

    def test_out_of_bounds_boxes_are_not_drawn(self):
        data=fixture();data['steps'][0]['box']=[-10,0,1100,50]
        self.assertIsNone(guide.validate(data)['steps'][0]['box'])

    def test_password_and_token_like_output_is_redacted(self):
        value='Bearer '+('a'*35)
        data=fixture();data['summary']=value
        self.assertNotIn(value,guide.validate(data)['summary'])

    def test_invalid_or_missing_model_output_is_not_claimed_as_guidance(self):
        for raw in ('', 'No image', '{"summary":12}'):
            with patch.object(guide.gemini,'text',return_value=raw):
                with self.assertRaises(ValueError):guide.analyze(Image.new('RGB',(20,20)),'Explain')

    def test_voice_request_needs_physical_approval_before_upload(self):
        frame=Image.new('RGB',(200,100))
        with patch.object(guide,'capture',return_value=frame),patch.object(guide,'analyze',return_value=guide.validate(fixture())) as ai,patch('core.confirm.request',return_value='pending') as gate:
            self.assertEqual(plugin.run({'question':'Where is Export?'}),'pending')
            ai.assert_not_called()
            self.assertIn('configured AI provider',gate.call_args.args[2])

    def test_approved_callback_only_describes_and_notifies(self):
        player=Mock();frame=Image.new('RGB',(200,100))
        with patch.object(guide,'capture',return_value=frame),patch.object(guide,'analyze',return_value=guide.validate(fixture())),patch('core.confirm.request') as gate:
            plugin.run({'question':'Explain'},player=player)
            text=gate.call_args.args[3]()
        self.assertIn('Export',text)
        self.assertIn('Do not click',player.request_say.call_args.args[0])

    def test_cannot_analyze_oversized_or_empty_requests(self):
        with self.assertRaises(ValueError):guide.analyze(Image.new('RGB',(10,10)),'')

    def test_visual_tier_does_not_use_audio_or_text_only_provider(self):
        from core import gemini
        self.assertNotIn(gemini.LIVE,gemini._LADDERS[gemini.VISION])
        self.assertEqual(gemini._provider_rungs(gemini.VISION),())
        client=Mock();client.models.generate_content.return_value=Mock(text='{}')
        with patch.object(gemini,'client',return_value=client) as factory,patch.object(gemini,'_cooling',return_value=False),patch.object(gemini,'_live_call') as live:
            gemini.call('synthetic',tier=gemini.VISION,key='synthetic-key')
            live.assert_not_called();self.assertEqual(factory.call_args.kwargs['retry_attempts'],1)


if __name__=='__main__':unittest.main()

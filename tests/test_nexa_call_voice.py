"""Native voice generation fixtures: no live API, audio output or calls."""
import asyncio
from types import SimpleNamespace as S
import unittest
from unittest.mock import Mock,patch
from core import nexa_call_voice as voice


class Session:
    def __init__(self,events):self.events=events
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def send_client_content(self,**kwargs):self.sent=kwargs
    async def receive(self):
        for event in self.events:yield event


def response(text='Hello.',complete=True,pcm=b'\x00\x00'*240):
    return S(server_content=S(interrupted=False,output_transcription=S(text=text),
        model_turn=S(parts=[S(inline_data=S(data=pcm,mime_type='audio/pcm;rate=24000'))]),turn_complete=complete))


class NativeVoiceTests(unittest.TestCase):
    def generate(self,events):
        from google import genai
        client=Mock();session=Session(events);client.aio.live.connect.return_value=session
        with patch.object(genai,'Client',return_value=client),patch('core.gemini.api_key',return_value='fixture'):
            result=asyncio.run(voice.generate('Hello.','Aoede'))
        return result,client,session
    def test_selected_nexa_voice_is_sent_without_tools_or_microphone(self):
        result,client,session=self.generate([response()])
        config=client.aio.live.connect.call_args.kwargs['config']
        self.assertEqual(config.speech_config.voice_config.prebuilt_voice_config.voice_name,'Aoede')
        self.assertFalse(config.tools);self.assertEqual(result[1],24000)
        self.assertTrue(session.sent['turn_complete'])
    def test_altered_message_never_plays(self):
        with self.assertRaisesRegex(RuntimeError,'did not match'):self.generate([response('Extra words Hello')])
    def test_incomplete_audio_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'incomplete'):self.generate([response(complete=False)])
    def test_known_brand_transcription_and_punctuation_match(self):
        self.assertEqual(voice.text_key('আমি Nexa, ব্যক্তিগত সহকারী'),voice.text_key('আমি নেক্সা ব্যক্তিগত সহকারী।'))
    def test_pcm_conversion_keeps_duration_and_target_rate(self):
        import numpy as np
        async def generated(*args):return b'\x00\x00'*24000,24000
        with patch.object(voice,'generate',generated),patch('memory.config_manager.get_voice',return_value='Aoede'):
            samples,rate,device=voice.synthesize('fixture',dict(id=6,rate=44100))
        self.assertEqual(rate,44100);self.assertEqual(device,6)
        self.assertAlmostEqual(len(samples)/rate,1,places=2);self.assertEqual(samples.dtype,np.float32)

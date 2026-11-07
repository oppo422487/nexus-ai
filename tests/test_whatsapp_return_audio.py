"""Dedicated speaker loopback selection and bounded callback reads."""
import unittest
from unittest.mock import Mock,patch
from core.whatsapp_return_audio import select_endpoint,open_return

class ReturnAudioTests(unittest.TestCase):
    def test_only_dedicated_speaker_selected(self):
        devices=[dict(name='Speakers (Realtek) [Loopback]',index=1),dict(name='CABLE Input [Loopback]',index=2),dict(name='Hi-Fi Cable Input (VB-Audio Hi-Fi Cable) [Loopback]',index=3)]
        self.assertEqual(select_endpoint(devices,'Hi-Fi Cable Output')['index'],3)
        with self.assertRaises(RuntimeError):select_endpoint(devices[:2],'Hi-Fi Cable Output')
        with self.assertRaises(RuntimeError):select_endpoint(devices+[devices[2]],'Hi-Fi Cable Output')
    def test_loopback_callback_keeps_right_channel_and_closes_owned_stream(self):
        import numpy as np
        manager=Mock();manager.get_loopback_device_info_generator.return_value=iter([dict(name='Hi-Fi Cable Input [Loopback]',index=27,defaultSampleRate=1000,maxInputChannels=2)])
        frames=np.column_stack([np.zeros(100),np.ones(100)*.1]).astype(np.float32)
        def opened(**kw):
            kw['stream_callback'](frames.tobytes(),100,{},0)
            self.assertEqual(kw['input_device_index'],27)
            return manager.stream
        manager.open.side_effect=opened
        with patch('pyaudiowpatch.PyAudio',return_value=manager):
            with open_return(dict(name='Hi-Fi Cable Output')) as (reader,device):
                data,overflow=reader.read(100)
                self.assertFalse(overflow);self.assertEqual(data.shape,(100,2));self.assertAlmostEqual(float(data[0,1]),.1,places=6)
        manager.stream.close.assert_called_once();manager.terminate.assert_called_once()
    def test_no_callback_does_not_block_forever(self):
        manager=Mock();manager.get_loopback_device_info_generator.return_value=iter([dict(name='Hi-Fi Cable Input [Loopback]',index=27,defaultSampleRate=1000,maxInputChannels=2)])
        with patch('pyaudiowpatch.PyAudio',return_value=manager):
            with open_return(dict(name='Hi-Fi Cable Output')) as (reader,device):
                data,overflow=reader.read(100)
                self.assertEqual(float(data.max()),0)

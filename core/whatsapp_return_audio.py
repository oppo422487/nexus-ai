"""Bounded WASAPI loopback of the dedicated call-return cable, never defaults."""
from contextlib import contextmanager
import queue


def select_endpoint(devices, recording_name):
    from core.whatsapp_call_audio import return_endpoint_matches
    found=[d for d in devices if return_endpoint_matches(recording_name,d['name'])]
    if len(found)!=1:
        raise RuntimeError('Dedicated return speaker loopback is missing or ambiguous. No default speaker/microphone fallback.')
    return found[0]


@contextmanager
def open_return(device, start=True):
    import numpy as np
    import pyaudiowpatch as pa
    audio=pa.PyAudio();stream=None
    try:
        endpoint=select_endpoint(list(audio.get_loopback_device_info_generator()),device['name'])
        rate=int(endpoint['defaultSampleRate']);channels=int(endpoint['maxInputChannels'])
        frames=max(1,int(rate*.1));pending=queue.Queue(maxsize=32);overrun=[False]
        def callback(data,count,info,status):
            if status:overrun[0]=True
            try:pending.put_nowait(data)
            except queue.Full:overrun[0]=True
            return (None,pa.paContinue)
        stream=audio.open(format=pa.paFloat32,channels=channels,rate=rate,input=True,
                          input_device_index=endpoint['index'],frames_per_buffer=frames,
                          stream_callback=callback,start=start)
        class Reader:
            def read(self,count):
                try:data=pending.get(timeout=.15)
                except queue.Empty:return np.zeros((frames,channels),dtype=np.float32),False
                return np.frombuffer(data,dtype=np.float32).reshape(-1,channels),overrun[0]
        yield Reader(),dict(device,id=endpoint['index'],rate=rate,channels=channels,backend='dedicated_wasapi_loopback')
    finally:
        if stream is not None:stream.close()
        audio.terminate()

"""Read Windows capture-session metadata; never record, play or change devices."""

def expected_recording_family(playback_name):
    name=str(playback_name).casefold()
    if 'cable input' in name:return 'cable output'
    if 'voicemeeter aux input' in name:return 'voicemeeter aux output'
    if 'voicemeeter input' in name:return 'voicemeeter output'
    return ''


def evaluate(sessions,playback_name):
    expected=expected_recording_family(playback_name)
    active=[s for s in sessions if s.get('active')]
    routed=[s for s in active if expected and expected in s['endpoint'].casefold()]
    usable=[s for s in routed if not s.get('muted')]
    if usable:
        return {'ready':True,'source':'windows_whatsapp_capture','detail':'WhatsApp is actively reading the configured virtual recording endpoint; remote hearing is unverified.'}
    if routed:return {'ready':False,'reason':'muted','detail':'WhatsApp virtual recording endpoint/session is muted or has zero volume.'}
    if active:return {'ready':False,'reason':'wrong_microphone','detail':'WhatsApp is using another microphone. In WhatsApp Audio settings choose the virtual cable recording endpoint (CABLE Output for CABLE Input).'}
    return {'ready':False,'reason':'not_active','detail':'WhatsApp has not opened the expected recording stream yet.'}


def readiness(playback_name):
    import comtypes
    from pycaw.utils import AudioUtilities
    from pycaw.api.audiopolicy import IAudioSessionControl2
    from pycaw.constants import EDataFlow,DEVICE_STATE
    from core.windows_whatsapp import owned_pids
    comtypes.CoInitialize()
    try:
        owned=owned_pids();sessions=[]
        for device in AudioUtilities.GetAllDevices(EDataFlow.eCapture.value,DEVICE_STATE.ACTIVE.value):
            try:
                enum=device.AudioSessionManager.GetSessionEnumerator()
                for i in range(enum.GetCount()):
                    ctl=enum.GetSession(i).QueryInterface(IAudioSessionControl2)
                    if ctl.GetProcessId() not in owned:continue
                    from pycaw.api.audioclient import ISimpleAudioVolume
                    volume=ctl.QueryInterface(ISimpleAudioVolume)
                    endpoint=device.EndpointVolume
                    muted=bool(volume.GetMute() or endpoint.GetMute() or endpoint.GetMasterVolumeLevelScalar()<=0)
                    sessions.append({'endpoint':device.FriendlyName or '', 'active':ctl.GetState()==1,'muted':muted})
            except Exception as exc:
                # Losing one device must not turn a partial scan into a false
                # "no capture" verdict. Report unavailable; caller fails safely.
                raise RuntimeError('Windows WhatsApp capture metadata could not be read: '+type(exc).__name__) from exc
        return evaluate(sessions,playback_name)
    finally:
        comtypes.CoUninitialize()


from contextlib import contextmanager


@contextmanager
def monitor_capture(playback_name):
    """Metadata polling off the PCM-writing thread; stops when the reader ends."""
    import threading
    stop=threading.Event();lost=threading.Event()
    def watch():
        while not stop.wait(.5):
            try:
                if not readiness(playback_name)['ready']:
                    lost.set();return
            except Exception:
                lost.set();return
    thread=threading.Thread(target=watch,name='whatsapp-capture-liveness',daemon=True)
    thread.start()
    try:yield lost
    finally:
        stop.set();thread.join(timeout=1)


def return_endpoint_matches(recording_name, render_name):
    """Match dedicated cable identity, including Windows' Speakers alias."""
    def key(value):return ''.join(c for c in str(value).casefold() if c.isalnum())
    recording=key(recording_name);render=key(render_name)
    family=recording.split('output')[0]
    if family not in ('hificable','cablea','cableb','cablec','cabled','voicemeeteraux'):
        return False
    if render.startswith(family+'input'):return True
    return family=='hificable' and render.startswith('speakers') and 'vbaudiohificable' in render


def render_route_readiness(recording_name):
    """Verify WhatsApp renders into the caller-only return cable."""
    import comtypes
    from pycaw.utils import AudioUtilities
    from pycaw.api.audiopolicy import IAudioSessionControl2
    from pycaw.constants import EDataFlow,DEVICE_STATE
    from core.windows_whatsapp import owned_pids
    owned=owned_pids();found=False;comtypes.CoInitialize()
    try:
        for device in AudioUtilities.GetAllDevices(EDataFlow.eRender.value,DEVICE_STATE.ACTIVE.value):
            if not return_endpoint_matches(recording_name,device.FriendlyName):continue
            found=True
            enum=device.AudioSessionManager.GetSessionEnumerator()
            for i in range(enum.GetCount()):
                ctl=enum.GetSession(i).QueryInterface(IAudioSessionControl2)
                if ctl.GetProcessId() in owned and ctl.GetState()==1:
                    return {'ready':True,'detail':'WhatsApp render session is active on the dedicated return cable.'}
        # A silent caller can leave the render session inactive. The confirmed,
        # dedicated cable is still safe to read; never substitute a default mic.
        if found:return {'ready':True,'active':False,'detail':'Dedicated return cable available; waiting for caller audio. WhatsApp render activity is not yet verified.'}
        return {'ready':False,'detail':'Dedicated return cable playback endpoint is missing. Check WhatsApp speaker routing; call left open for manual takeover.'}
    finally:comtypes.CoUninitialize()

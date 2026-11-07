"""WhatsApp Desktop call controls, adapted from BitCrush777/Jarvis-Ai-Assistant.
MIT copyright (c) 2026 Saidarshan.K; see licenses/whatsapp-calls-MIT.txt.
No fixed-coordinate clicking or global TTS routing. Configured incoming rules
are owned by core.whatsapp_auto_reply.
"""
import asyncio
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import re
import threading
import time
from _ctypes import COMError

CONFIG = Path(__file__).resolve().parents[1] / 'config/whatsapp_calls.json'
_settings_lock = threading.RLock()
_lock = threading.Lock()
_cancel = threading.Event()


def settings():
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def update_settings(changes,expected_message=None):
    with _settings_lock:
        cfg=settings()
        if expected_message is not None and cfg.get('auto_answer_message','')!=expected_message:
            raise RuntimeError('Call message changed from chat while this settings form was open. Reload it before saving.')
        cfg.update(changes);CONFIG.parent.mkdir(parents=True,exist_ok=True)
        temp=CONFIG.with_suffix('.tmp')
        temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(CONFIG)
        return cfg


def audio_outputs():
    import sounddevice as sd
    apis=sd.query_hostapis()
    return [{'id':i,'name':d['name'],'rate':d['default_samplerate'],
             'api':apis[d['hostapi']]['name'],'channels':min(2,d['max_output_channels'])}
            for i,d in enumerate(sd.query_devices())
            if d['max_output_channels']>0 and is_virtual(d['name'])]


def is_virtual(name):
    # Windows playback endpoint. CABLE Output is the recording endpoint that
    # WhatsApp must select as its microphone, not where Nexa plays audio.
    return any(x in name.casefold() for x in ('cable input', 'voicemeeter input', 'voicemeeter aux input'))


def audio_ready():
    cfg = settings()
    if not cfg.get('microphone_routed'):
        raise RuntimeError('In WhatsApp Audio settings select the matching virtual cable recording endpoint as microphone, then confirm routing in Nexa Settings > WhatsApp calls.')
    outputs=audio_outputs()
    choices = [d for d in outputs if d['name'] == cfg.get('output_name')]
    if len(choices) != 1:
        # Same device appears through several Windows APIs. Stored API index is
        # accepted only while it still resolves to the same endpoint name.
        choices = [d for d in choices if d['id'] == cfg.get('output_id')]
    if len(choices) != 1:
        raise RuntimeError('Virtual audio output missing or ambiguous. Select it again in WhatsApp calls settings. No call was placed.')
    selected=choices[0]
    # Resolve the SAME logical cable across API aliases. MME truncates names;
    # never fall through to a default speaker or a different cable family.
    name=selected['name'].casefold()
    aliases=[d for d in outputs if d['name'].casefold()==name or
             (min(len(name),len(d['name']))>=24 and
              (d['name'].casefold().startswith(name) or name.startswith(d['name'].casefold())))]
    for api in ('Windows WASAPI','Windows DirectSound'):
        matches=[d for d in aliases if d.get('api')==api]
        if len(matches)>1:raise RuntimeError('Logical cable has ambiguous shared audio endpoints. Select a unique output.')
        if matches:return matches[0]
    return selected


def playback_kwargs(device):
    import sounddevice as sd
    result={'device':device['id'],'samplerate':int(device['rate']),
            'channels':device.get('channels',1),'dtype':'float32','latency':'high'}
    if device.get('api')=='Windows WASAPI':
        result['extra_settings']=sd.WasapiSettings(exclusive=False,auto_convert=True)
    return result


def preflight_playback(device,samples=None,cancel=None):
    """Open but do NOT start/write audio, before any call action."""
    import sounddevice as sd
    from core.call_diagnostics import event
    if samples is not None:
        options=playback_kwargs(device)
        held=BufferedPlayback(samples,int(device['rate']),options,cancel or _cancel)
        event('output_preflight_ok',device=device['id'],api=device.get('api'),rate=device['rate'],channels=options['channels'],retained=True)
        return held
    stream=sd.OutputStream(**playback_kwargs(device))
    try:
        event('output_preflight_ok',device=device['id'],api=device.get('api'),rate=device['rate'],channels=device.get('channels',1))
    finally:stream.close()


def normal(text):
    return ' '.join(str(text).casefold().split())


class Controller:
    def __init__(self, auto):
        self.auto = auto
        self.window = None
        self.external_action = False

    def attach(self, focus=True):
        from core.windows_whatsapp import owned_pids, focus_existing, foreground_pid
        pids = owned_pids()
        try:
            windows = [w for w in self.auto.GetRootControl().GetChildren() if w.ProcessId in pids
                       and w.ControlTypeName == 'WindowControl' and not w.IsOffscreen]
        except COMError:
            windows=[]
        if not windows:
            # A broken accessibility provider must not prevent attaching to a
            # native, process-verified window for the visual fallback.
            from types import SimpleNamespace
            from core.windows_whatsapp import visible_windows
            windows=[SimpleNamespace(NativeWindowHandle=w['hwnd'],ProcessId=w['pid'],
                       ControlTypeName='WindowControl',Name=w.get('title',''),IsOffscreen=False,native_only=True)
                     for w in visible_windows()]
        if len(windows)>1:
            # WhatsApp can move the call into a separate top-level window.
            call_windows=[]
            for w in windows:
                probe=Controller(self.auto);probe.window=w
                try:
                    if any(c.ControlTypeName=='ButtonControl' and normal(c.Name) in
                           {'accept','accept call','answer','answer call','end call','hang up'}
                           and not c.IsOffscreen for c in probe.nodes()):
                        call_windows.append(w)
                except COMError:
                    continue
            if not call_windows:
                call_windows=[w for w in windows if isinstance(getattr(w,'Name',None),str) and w.Name.casefold().strip() in ('voice call','incoming voice call','incoming call','whatsapp voice call')]
            if call_windows:
                windows=call_windows
            else:
                from core.whatsapp_call_vision import foreground_handle
                front=foreground_handle()
                windows=[w for w in windows if w.NativeWindowHandle==front]
        if len(windows) != 1:
            raise RuntimeError('Open the installed WhatsApp Desktop app. A unique desktop window could not be identified.')
        self.window = windows[0]
        if focus:
            from core.whatsapp_call_vision import focus_window
            focus_window(self.window.NativeWindowHandle)
        return self

    def nodes(self):
        if getattr(self.window,'native_only',False) is True:
            return []
        try:
            return [c for c, _ in self.auto.WalkControl(self.window, maxDepth=14)]
        except COMError:
            return []

    def button(self, names):
        wanted = {normal(n) for n in names}
        found = [c for c in self.nodes() if c.ControlTypeName == 'ButtonControl'
                 and normal(c.Name) in wanted and c.IsEnabled and not c.IsOffscreen]
        if len(found) != 1:
            raise RuntimeError('Call button missing or ambiguous. No coordinate fallback was used.')
        return found[0]

    def state(self):
        names = {normal(c.Name) for c in self.nodes() if not c.IsOffscreen}
        if names & {'accept', 'accept call', 'answer', 'answer call'}:
            return 'incoming'
        if names & {'calling', 'ringing', 'connecting', 'calling…', 'ringing…'}:
            return 'ringing'
        # End-call alone also appears while dialing: never equate it to answered.
        for node in self.nodes():
            if node.ControlTypeName != 'ButtonControl' or normal(node.Name) not in {'end call','hang up'} or node.IsOffscreen:
                continue
            panel = node
            for _ in range(3):
                panel = panel.GetParentControl()
                if not panel or panel == self.window:
                    break
                group = [c for c, _ in self.auto.WalkControl(panel,maxDepth=5)]
                if len(group)>80:
                    break
                for c in group:
                    name = normal(c.Name)
                    if not c.IsOffscreen and re.fullmatch(r'\d{1,2}:\d{2}(?::\d{2})?',name) and any(int(v) for v in name.split(':')):
                        return 'connected_timer_visible'
        return 'unknown'

    def select_contact(self, contact):
        target = normal(contact)
        if not target or len(contact) > 120:
            raise ValueError('Provide the exact saved contact or group name (1–120 characters).')
        # Read the named search input, not the first EditControl/chat composer.
        inputs = [c for c in self.nodes() if c.ControlTypeName == 'EditControl'
                  and normal(c.Name) in {'search', 'search or start a new chat', 'search chats', 'search or start new chat', 'search input textbox'}
                  and not c.IsOffscreen]
        if len(inputs) != 1:
            raise RuntimeError('WhatsApp chat-search field not identifiable. Open the target chat manually; no blind keys were sent.')
        try:
            inputs[0].GetValuePattern().SetValue(contact)
        except Exception:
            # WebView content-editable search sometimes lacks ValuePattern.
            # Focus only the identified search control, then paste Unicode.
            import pyperclip
            inputs[0].SetFocus()
            inputs[0].SendKeys('{Ctrl}a',waitTime=.1)
            pyperclip.copy(contact)
            inputs[0].SendKeys('{Ctrl}v',waitTime=.2)
        time.sleep(1)
        rows = [c for c in self.nodes() if normal(c.Name) == target
                and c.ControlTypeName in ('ListItemControl', 'TextControl', 'ButtonControl') and not c.IsOffscreen]
        # Nested label+row is fine only if they resolve to the same row.
        targets = {}
        for c in rows:
            row = c
            for _ in range(4):
                if row.ControlTypeName == 'ListItemControl':
                    break
                parent = row.GetParentControl()
                if not parent or parent == self.window:
                    break
                row = parent
            if row.ControlTypeName == 'ListItemControl':
                targets[tuple(row.GetRuntimeId())] = row
        if len(targets) != 1:
            raise RuntimeError('Exact WhatsApp recipient is missing or ambiguous. No call was placed.')
        next(iter(targets.values())).Click()
        time.sleep(.5)
        # Must see exact recipient AND call control after selection.
        if not any(normal(c.Name) == target for c in self.nodes() if c.ControlTypeName in ('TextControl', 'ButtonControl') and not c.IsOffscreen):
            raise RuntimeError('Selected recipient could not be read back. No call placed.')

    def recipient_button(self, contact):
        button = self.button(('Voice call', 'Audio call', 'Call'))
        header = button
        verified = False
        for _ in range(4):
            header = header.GetParentControl()
            if not header or header == self.window:
                break
            group = [c for c, _ in self.auto.WalkControl(header,maxDepth=5)]
            if len(group)>80:
                break
            if any(normal(c.Name)==normal(contact) and not c.IsOffscreen for c in group):
                verified=True
                break
        if not verified:
            raise RuntimeError('Exact recipient could not be verified beside the call button. No call placed.')
        return button

    def dial(self, contact):
        if not contact.strip() or len(contact)>120:
            raise ValueError('Provide an exact saved contact name (1–120 characters).')
        try:
            # A manually opened, verified target chat needs no search field.
            button = self.recipient_button(contact)
        except RuntimeError:
            self.select_contact(contact)
            button = self.recipient_button(contact)
        self.external_action = True
        button.Click()
        return {'status': 'requested', 'contact': contact, 'detail': 'Voice-call button clicked; answer is not confirmed.'}

    def answer(self):
        if self.state() != 'incoming':
            raise RuntimeError('No readable incoming call. Nothing was accepted.')
        if any('video call' in normal(n.Name) or '\u09ad\u09bf\u09a1\u09bf\u0993' in normal(n.Name) for n in self.nodes() if not n.IsOffscreen):
            raise RuntimeError('Incoming video calls are not accepted by the voice reply feature.')
        button=self.button(('Accept', 'Accept call', 'Answer', 'Answer call'))
        self.external_action=True
        button.Click()
        return {'status': 'requested', 'detail': 'Accept clicked; audio connection not independently confirmed.'}

    def end(self):
        button=self.button(('End call', 'Hang up'))
        self.external_action=True
        button.Click()
        return {'status': 'requested', 'detail': 'End-call clicked.'}

    def reject(self):
        if self.state() != 'incoming':
            raise RuntimeError('No readable incoming call.')
        button=self.button(('Decline', 'Reject', 'Decline call'))
        self.external_action=True
        button.Click()
        return {'status': 'requested', 'detail': 'Decline clicked.'}


@contextmanager
def controller(focus=True):
    import uiautomation as auto
    with auto.UIAutomationInitializerInThread():
        yield Controller(auto).attach(focus=focus)


def visual_controller(c):
    if not settings().get('visual_fallback', True):
        raise RuntimeError('WhatsApp accessibility is unavailable. Enable window visual fallback in WhatsApp calls settings.')
    from core.whatsapp_call_vision import VisualController
    return VisualController(c.window.NativeWindowHandle)


def perform(c, action, contact=''):
    """Fallback only before this action's click; never repeat an uncertain click."""
    c.external_action=False
    try:
        if action=='voice_call':
            if c.state() in ('incoming','ringing','connected_timer_visible'):
                raise ValueError('A WhatsApp call is already present. No second call placed.')
            return c.dial(contact)
        return getattr(c, {'answer_call':'answer','reject_call':'reject','end_call':'end'}[action])()
    except (RuntimeError,COMError):
        if c.external_action:
            raise
        visual=visual_controller(c)
        try:
            return visual.dial(contact) if action=='voice_call' else visual.action(action)
        finally:
            c.external_action = c.external_action or visual.external_action


def call_state(c):
    state=c.state()
    if state!='unknown':
        return state
    state=visual_controller(c).state()
    return 'connected_timer_visible' if state=='connected' else state


def reserve():
    if not _lock.acquire(blocking=False):
        raise RuntimeError('A WhatsApp call operation is already running. Stop speaking or wait; no second operation started.')
    _cancel.clear()


def release():
    _lock.release()


def control(action, contact=''):
    if action=='status' and _lock.locked():
        return {'state':'unknown','operation_in_progress':True,'detail':'A background operation is preparing or inspecting WhatsApp. This is NOT evidence of a dialing or connected call. Wait for its final result; do not claim an existing call.'}
    if action=='end_call':
        _cancel.set()
    reserve()
    try:
        with controller(focus=action != 'status') as c:
            if action=='status':
                from core.whatsapp_auto_reply import status as auto_status
                return {'state':call_state(c),'auto_reply':auto_status()}
            if action in ('voice_call','answer_call','reject_call','end_call'):
                return perform(c,action,contact)
            raise ValueError('Unknown WhatsApp call action.')
    finally:
        release()


def stop_speaking():
    _cancel.set()
    return {'status': 'cancel_requested', 'detail': 'Stops call-message playback; does not hang up or stop normal Nexa audio.'}


def synthesize(message):
    if not message.strip() or len(message)>1500:
        raise ValueError('A spoken message must be 1–1500 characters.')
    from core.nexa_call_voice import synthesize as nexa_speech
    return nexa_speech(message,audio_ready())


class BufferedPlayback:
    """Own one callback stream from before acceptance until operation cleanup."""
    def __init__(self,samples,rate,options,cancel):
        import numpy as np
        import sounddevice as sd
        self.samples=np.asarray(samples,dtype=np.float32).reshape(-1)
        if not len(self.samples):raise RuntimeError('Prepared call audio is empty; no stream started.')
        self.rate=rate;self.cancel=cancel;self.lost=None
        self.cursor=0;self.underflows=0;self.aborted=False;self.done=threading.Event()
        self.stream=sd.OutputStream(**options,callback=self.callback,finished_callback=self.done.set)
    def callback(self,outdata,frames,timing,status):
        import sounddevice as sd
        outdata.fill(0)
        if getattr(status,'output_underflow',False):self.underflows+=1
        if self.cancel.is_set() or (self.lost is not None and self.lost.is_set()):
            self.aborted=True
            raise sd.CallbackAbort
        count=min(frames,len(self.samples)-self.cursor)
        outdata[:count,:]=self.samples[self.cursor:self.cursor+count,None]
        self.cursor+=count
        if self.cursor>=len(self.samples):raise sd.CallbackStop
    def play(self,lost_capture=None):
        from core.call_diagnostics import event
        self.lost=lost_capture
        event('playback_start',rate=self.rate,frames=len(self.samples),retained_stream=True)
        self.stream.start()  # Start the already-open stream. NEVER reopen it.
        deadline=time.monotonic()+len(self.samples)/self.rate+15
        while not self.done.wait(.1):
            if time.monotonic()>deadline:
                self.stream.abort()
                raise RuntimeError('Call audio stream did not finish within its playback deadline.')
            if self.cancel.is_set() or (self.lost is not None and self.lost.is_set()):
                self.aborted=True;self.stream.abort();break
        event('playback_end',frames_played=self.cursor,total_frames=len(self.samples),underflows=self.underflows,aborted=self.aborted)
        return {'complete':not self.aborted and self.cursor==len(self.samples),'underflows':self.underflows}
    def close(self):self.stream.close()


def play_buffered(samples,rate,device,cancel,lost_capture=None,channels=1,extra_settings=None,prepared_stream=None):
    if prepared_stream is not None:
        return prepared_stream.play(lost_capture)
    options=dict(device=device,samplerate=rate,channels=channels,dtype='float32',latency='high')
    if extra_settings is not None:options['extra_settings']=extra_settings
    held=BufferedPlayback(samples,rate,options,cancel)
    try:return held.play(lost_capture)
    finally:held.close()


def message_operation(action, contact, message, notify=lambda text: None, reserved=False, prepared_audio=None, incoming_handler=None, cleanup_handler=None, expected_caller=None):
    if not reserved:
        reserve()
    stage='audio_setup'
    outcome={'accepted':False,'playback_complete':False}
    from core.call_diagnostics import event
    event('operation_start',action=action)
    held=None
    try:
        audio_ready()  # No outgoing call if cable configuration is missing.
        stage='synthesis'
        # Incoming calls must be accepted promptly, before cloud TTS latency.
        prepared = prepared_audio if prepared_audio is not None else synthesize(message)
        if _cancel.is_set():
            return {'status':'cancelled','stage':stage,'detail':'No new call or audio started.'}
        stage='output_preflight'
        samples,rate,device=prepared
        selected=audio_ready()
        if selected['id']!=device or int(selected['rate'])!=rate:
            raise RuntimeError('Prepared speech endpoint changed; no call accepted.')
        held=preflight_playback(selected,samples,_cancel)
        with controller() as c, ExitStack() as cleanup:
            if action=='call_and_say':
                stage='dial'
                perform(c,'voice_call',contact)
            elif action=='answer_and_say':
                stage='answer'
                if expected_caller:
                    from core.whatsapp_contact_rules import current_caller,identity_key
                    if identity_key(current_caller(c))!=identity_key(expected_caller):
                        raise RuntimeError('Incoming caller changed during preparation; no personalized reply sent.')
                    from core.whatsapp_contact_rules import choose
                    from core.whatsapp_caller_notes import compose_message
                    selected_rule=choose(settings(),expected_caller)
                    if not selected_rule or not selected_rule.get('matched') or compose_message(selected_rule['message'],settings())!=message:
                        raise RuntimeError('Caller reply changed or expired before acceptance; no stale message sent.')
                perform(c,'answer_call')
                outcome['accepted']=True
                event('incoming_accepted')
            elif action!='speak_in_call':
                raise ValueError('Unknown call message action.')
            stage='connection_verification'
            notify('Checking current call/audio readiness before virtual-cable playback; no delivery claimed.')
            deadline=time.monotonic()+45
            capture_confirmations=0
            capture_detail='No local microphone readiness result.'
            while not _cancel.is_set():
                if action=='answer_and_say':
                    # Accept was already requested after verifying incoming UI.
                    # Confirm the actual cable reader locally, not via another
                    # cloud screenshot request after accepting the call.
                    from core.whatsapp_call_audio import readiness
                    routing=readiness(audio_ready()['name'])
                    capture_detail=routing['detail']
                    if routing['ready']:
                        capture_confirmations+=1
                        if capture_confirmations>=2:
                            print('[WHATSAPP_CALL] Accepted incoming call; local cable capture ready.',flush=True)
                            break
                    else:
                        capture_confirmations=0
                        if routing.get('reason') in ('wrong_microphone','muted'):
                            return dict(outcome,status='not_played',stage=stage,detail=capture_detail+' Call left open; no automatic hangup.')
                    if time.monotonic()>=deadline:
                        return dict(outcome,status='not_played',stage=stage,detail=capture_detail+' Call left open; no automatic hangup or retry.')
                    _cancel.wait(.5)
                    continue
                c.attach(focus=False)
                state=call_state(c)
                if state=='connected_timer_visible':
                    break
                if action=='speak_in_call' or state=='ended' or time.monotonic()>=deadline:
                    return {'status':'not_played','stage':stage,'detail':'No verified connected call. No audio played and no redial.'}
                _cancel.wait(.5)
            if _cancel.is_set():
                return dict(outcome,status='cancelled',stage=stage)
            stage='virtual_cable_playback'
            # Synthesis may take time: endpoint identity must still match.
            current=audio_ready()
            if current['id']!=device or int(current['rate'])!=rate:
                raise RuntimeError('Virtual cable changed during preparation. No playback started.')
            import sounddevice as sd
            from core.whatsapp_call_vision import window_rect
            # No model invocation per audio chunk: that used to stall playback.
            # Check that the call window still exists; the complete current-call
            # connection was verified immediately before opening our own stream.
            next_check=0
            with ExitStack() as lifetime:
                lost_capture=None
                if action=='answer_and_say':
                    from core.whatsapp_call_audio import monitor_capture
                    lost_capture=lifetime.enter_context(monitor_capture(current['name']))
                options=playback_kwargs(current)
                playback=play_buffered(samples,rate,device,_cancel,lost_capture,channels=options['channels'],extra_settings=options.get('extra_settings'),prepared_stream=held)
                if not playback['complete']:
                    return dict(outcome,status='interrupted',stage=stage,detail='Call audio interrupted. Call left open for manual takeover; no automatic hangup.')
            outcome['playback_complete']=True
            if cleanup_handler:cleanup.callback(cleanup_handler,c,outcome)
            outcome.update(status='played_to_virtual_cable',stage='complete',detail='Exact message finished on configured cable. Remote hearing is not independently verified; no automatic repeat.')
            if incoming_handler:
                stage='caller_reply'
                outcome.update(incoming_handler())
            return outcome
    except Exception as exc:
        event('operation_error',**dict(outcome,action=action,stage=stage,error=str(exc)))
        error=RuntimeError(f'WhatsApp {stage} failed: {exc}. No automatic retry.')
        error.accepted=outcome['accepted'];error.playback_complete=outcome['playback_complete']
        raise error from exc
    finally:
        try:
            if held is not None:held.close()
        finally:
            event('operation_end',**dict(outcome,action=action,stage=stage))
            release()


def call_and_say(contact, message, notify=lambda text: None, reserved=False):
    return message_operation('call_and_say',contact,message,notify,reserved)

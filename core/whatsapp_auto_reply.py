"""Opt-in WhatsApp incoming calls: exact saved message, no caller conversation."""
import asyncio
import json
import threading
import time
from core import whatsapp_calls as calls

_stop=threading.Event()
_thread=None
_guard=threading.Lock()
_state={'watching':False,'phase':'disabled','error':''}
_log=lambda text:None
_expiry_timer=None
_expiry_deadline=None
_timer_guard=threading.Lock()
_config_guard=calls._settings_lock


def report(phase,error=''):
    from core.call_diagnostics import event
    changed=(_state.get('phase'),_state.get('error'))!=(phase,error)
    _state.update(phase=phase,error=error)
    if phase in ('error','not_played','interrupted','played_to_virtual_cable','manual_takeover','note_failed'):
        _state.update(last_call_status=phase,last_call_detail=error)
    if changed:event('watcher_status',phase=phase,error=error)
    if changed and (error or phase in ('checking_audio','preparing_message','watching','handling','played_to_virtual_cable','disabled','expired')):
        text='WhatsApp auto reply: '+phase+(' — '+error if error else '')
        print('[WHATSAPP_AUTO] '+text,flush=True)
        try:_log('SYS: '+text)
        except Exception:pass


def active(cfg):
    expires=cfg.get('auto_answer_expires_at')
    from core.whatsapp_contact_rules import live_rules
    return bool(live_rules(cfg)) or (bool(cfg.get('auto_answer_enabled')) and (expires is None or time.time()<float(expires)))


def status():
    from datetime import datetime,timezone,timedelta
    dhaka=timezone(timedelta(hours=6),name='Asia/Dhaka')
    cfg=calls.settings();expires=cfg.get('auto_answer_expires_at')
    from core.whatsapp_contact_rules import describe_rules
    return dict(_state,enabled=active(cfg),automatic_incoming_reply=True,mode='exact_saved_message',
                message=cfg.get('auto_answer_message',''),caller_rules=describe_rules(cfg),
                default_enabled=bool(cfg.get('auto_answer_enabled')) and (expires is None or time.time()<expires),
                readiness_note='Watching/prepared means ready to detect a call, not that a call/audio delivery succeeded. Inspect last_call_status and last_call_detail.',
                expires_at=datetime.fromtimestamp(expires,dhaka).isoformat() if expires else None,
                remaining_seconds=max(0,int(expires-time.time())) if expires else None)


def arm_expiry(cfg):
    global _expiry_timer,_expiry_deadline
    deadline=cfg.get('auto_answer_expires_at') if cfg.get('auto_answer_enabled') else None
    with _timer_guard:
        if deadline==_expiry_deadline:return
        if _expiry_timer:_expiry_timer.cancel()
        _expiry_deadline=deadline;_expiry_timer=None
        if deadline is None:return
        def expire():
            with _config_guard:
                latest=calls.settings()
                if latest.get('auto_answer_enabled') and latest.get('auto_answer_expires_at')==deadline:
                    from core.whatsapp_contact_rules import live_rules
                    if live_rules(latest):
                        calls.update_settings({'auto_answer_enabled':False})
                        report('default_expired')
                    else:
                        configure(False)
                        report('expired')
        _expiry_timer=threading.Timer(max(0,float(deadline)-time.time()),expire)
        _expiry_timer.daemon=True;_expiry_timer.start()


def configure(enabled,message=None,duration_minutes=None,*,disable_contacts=True):
    with _config_guard:
        cfg=calls.settings()
        previous_message=cfg.get('auto_answer_message','')
        text=message if message is not None else cfg.get('auto_answer_message','')
        if enabled:
            if not isinstance(text,str) or not text.strip() or len(text)>1500:
                raise ValueError('Save an exact auto-reply message of 1–1500 characters before enabling.')
            if duration_minutes is not None and (isinstance(duration_minutes,bool) or not isinstance(duration_minutes,int) or not 1<=duration_minutes<=10080):
                raise ValueError('duration_minutes must be a whole number from 1 to 10080, or omitted for no expiry.')
            calls.audio_ready()
            from core.whatsapp_caller_notes import compose_message,return_ready
            compose_message(text,cfg)
            if cfg.get('caller_notes_enabled'):return_ready()
        cfg.update(auto_answer_enabled=bool(enabled),auto_answer_message=text.strip(),
                   auto_answer_expires_at=time.time()+duration_minutes*60 if enabled and duration_minutes is not None else None)
        if not enabled and disable_contacts:cfg['caller_rules']=[dict(r,enabled=False) for r in cfg.get('caller_rules',[])]
        calls.update_settings(cfg)
        if _state.get('phase')=='handling' and (not enabled or text.strip()!=previous_message):calls.stop_speaking()
        arm_expiry(cfg)
        if enabled:start()
        return status()


def incoming_notification(item,now):
    if 'whatsapp' not in str(item.get('app','')).casefold():return False
    age=now-float(item.get('ts',0))
    if not 0<=age<=30:return False
    text=(str(item.get('title',''))+' '+str(item.get('body',''))).casefold()
    if any(word in text for word in ('missed','video','ended','declined','মিসড','মিস্','ভিডিও')):return False
    return any(word in text for word in ('incoming voice call','incoming call','voice call from','ইনকামিং কল','ইনকামিং ভয়েস কল'))


async def notification_hints():
    # Never request a permission or open a Windows prompt from the watcher.
    from winsdk.windows.ui.notifications.management import UserNotificationListener,UserNotificationListenerAccessStatus
    from winsdk.windows.ui.notifications import NotificationKinds
    listener=UserNotificationListener.current
    if listener.get_access_status()!=UserNotificationListenerAccessStatus.ALLOWED:return []
    raw=await listener.get_notifications_async(NotificationKinds.TOAST)
    from plugins.notification_reader import _winrt_dt_to_ts
    items=[]
    for n in raw:
        try:
            name=n.app_info.display_info.display_name
            if 'whatsapp' not in name.casefold():continue
            lines=[t.text for b in n.notification.visual.bindings for t in b.get_text_elements() if t.text]
            item={'app':name,'title':' '.join(lines),'body':'','ts':_winrt_dt_to_ts(n.creation_time)}
            if incoming_notification(item,time.time()):items.append('toast:'+str(n.id))
        except Exception:continue
    return items


def window_hints():
    """Local inspection only: no focus changes, screenshots or model requests."""
    import uiautomation as auto
    from core.windows_whatsapp import owned_pids
    pids=owned_pids();windows=set();incoming=set()
    with auto.UIAutomationInitializerInThread():
        try:
            children=auto.GetRootControl().GetChildren()
        except calls.COMError:
            from core.windows_whatsapp import visible_windows
            return {w['hwnd'] for w in visible_windows()},set()
        for w in children:
            try:
                if w.ProcessId not in pids or w.ControlTypeName!='WindowControl' or w.IsOffscreen:continue
                hwnd=int(w.NativeWindowHandle);windows.add(hwnd)
                c=calls.Controller(auto);c.window=w
                names=' '.join(calls.normal(n.Name) for n in c.nodes() if not n.IsOffscreen)
                if c.state()=='incoming' and 'video call' not in names and 'ভিডিও' not in names:
                    incoming.add('uia:'+str(hwnd))
            except calls.COMError:
                continue
    return windows,incoming


def worker():
    _state['watching']=True
    seen_toasts=set();latched=set();previous_windows=None;prepared=None;speech_cache={};signature=None;next_attempt=0;pending=set();needs_takeover=False
    try:
        while not _stop.is_set():
            cfg=calls.settings()
            arm_expiry(cfg)
            if not active(cfg):
                report('disabled');prepared=None;signature=None
                _stop.wait(2);continue
            try:
                if signature is None and _state.get('phase') not in ('error','setup_required'):report('checking_audio')
                device=calls.audio_ready()
                message=cfg.get('auto_answer_message','').strip()
                from memory.config_manager import get_voice,get_user_name
                from core import whatsapp_caller_notes as notes
                spoken=notes.compose_message(message,cfg)
                if cfg.get('caller_notes_enabled'):notes.return_ready()
                current=(message,get_voice(),device['id'],int(device['rate']),get_user_name(),spoken,bool(cfg.get('caller_notes_enabled')),json.dumps(cfg.get('caller_rules',[]),sort_keys=True))
                if not message and not cfg.get('caller_rules'):raise RuntimeError('No exact auto-reply message saved.')
                if signature!=current:
                    report('preparing_message')
                    speech_cache={}
                    default_deadline=cfg.get('auto_answer_expires_at')
                    default_live=cfg.get('auto_answer_enabled') and (default_deadline is None or time.time()<default_deadline)
                    prepared=calls.synthesize(spoken) if message and default_live else None
                    if prepared is not None:speech_cache[spoken]=prepared
                    from core.whatsapp_contact_rules import live_rules
                    for rule in live_rules(cfg):
                        text=notes.compose_message(rule['message'],cfg)
                        if text not in speech_cache:speech_cache[text]=calls.synthesize(text)
                    signature=current
                    report('watching')
                if calls.settings().get('auto_answer_message','').strip()!=message:
                    signature=None
                    continue  # A chat update superseded audio prepared off-thread.
                if calls._lock.locked():
                    _stop.wait(2);continue
                windows,local=window_hints()
                newly_opened=set() if previous_windows is None else windows-previous_windows
                previous_windows=windows
                try:
                    toasts=set(asyncio.run(asyncio.wait_for(notification_hints(),timeout=3)))
                except Exception:
                    toasts=set()  # UIA/new-window detection remains available.
                candidates=pending|(local-latched)|(toasts-seen_toasts)|{'window:'+str(h) for h in newly_opened}
                latched=local;seen_toasts.update(toasts)
                if len(seen_toasts)>1000:seen_toasts=set(toasts)
                if needs_takeover:
                    from core.whatsapp_call_audio import readiness
                    ended=readiness(device['name']).get('reason')=='not_active'
                    if ended or candidates:
                        # A fresh hint still goes through exact incoming-call
                        # verification. A persistent mic session cannot hide it.
                        needs_takeover=False
                    else:
                        report('manual_takeover','The accepted call needs manual takeover after incomplete speech or caller capture. End/take over that call; fresh incoming calls will still be checked.')
                        _stop.wait(2);continue
                if candidates and time.monotonic()<next_attempt:
                    pending=candidates
                if candidates and time.monotonic()>=next_attempt and active(calls.settings()) and not _stop.is_set():
                    # Hints never authorize a click: answer_and_say independently
                    # verifies a CURRENT incoming call before accepting it.
                    latest=calls.settings()
                    if latest.get('auto_answer_message','').strip()!=message or get_voice()!=signature[1] or get_user_name()!=signature[4] or notes.compose_message(message,latest)!=spoken:
                        pending=candidates;signature=None
                        continue
                    pending=set()
                    next_attempt=time.monotonic()+3  # Short debounce, not a one-minute block on the next caller.
                    from core import whatsapp_contact_rules as rules
                    caller='';selected=None
                    if rules.live_rules(latest):
                        try:caller=rules.current_caller()
                        except Exception as exc:
                            report('caller_unidentified',str(exc)+' Personalized rule not verified; call left unanswered.')
                            continue
                        selected=rules.choose(latest,caller)
                        if selected is None:
                            report('unmatched_caller','No verified matching caller rule and no active default reply; call not answered.')
                            continue
                    selected_message=selected['message'] if selected else message
                    _state['last_selected_reply']={'rule':selected.get('contact_name','default') if selected else 'default','message':selected_message}
                    from core.call_diagnostics import event
                    from hashlib import sha256
                    event('reply_selected',mode='contact' if selected and selected.get('matched') else 'default',message_fingerprint=sha256(selected_message.encode('utf-8')).hexdigest()[:16])
                    selected_spoken=notes.compose_message(selected_message,latest)
                    selected_audio=speech_cache.get(selected_spoken)
                    if selected_audio is None:selected_audio=calls.synthesize(selected_spoken)
                    # Recheck the saved rule after potentially slow synthesis.
                    if selected and rules.choose(calls.settings(),caller)!=selected:
                        pending=candidates;continue
                    options={}
                    if selected and selected.get('matched'):options['expected_caller']=caller
                    if caller:options['incoming_handler']=lambda:notes.take_note(caller)
                    report('handling')
                    if cfg.get('caller_notes_enabled'):
                        options.setdefault('incoming_handler',notes.take_note)
                        options['cleanup_handler']=notes.end_handled_call
                    else:options.pop('incoming_handler',None)
                    result=calls.message_operation('answer_and_say','',selected_spoken,prepared_audio=selected_audio,**options)
                    _state['last_call_result']={k:result.get(k) for k in ('accepted','playback_complete','caller_reply','note_id','hangup_status','hangup_error')}
                    needs_takeover=bool(result.get('accepted') and (not result.get('playback_complete') or result.get('hangup_status')=='manual_takeover'))
                    if result.get('hangup_status')=='manual_takeover':
                        report('manual_takeover',result.get('hangup_error','Caller reply was not captured; call left open.'))
                    elif result.get('caller_reply')=='error':
                        report('note_failed',result.get('caller_reply_error','Caller reply was not captured.'))
                    else:
                        report(result['status'],'' if result['status']=='played_to_virtual_cable' else result.get('detail','No audio delivery verified.'))
            except Exception as exc:
                needs_takeover=needs_takeover or bool(getattr(exc,'accepted',False) and not getattr(exc,'playback_complete',False))
                report('error',str(exc))
                # Do not retry the same call. Future fresh incoming events can
                # be handled; setup/synthesis failures back off without spam.
                _stop.wait(10)
            _stop.wait(2)
    finally:
        _state['watching']=False


def start(log=None):
    global _thread,_log
    if log is not None:_log=log
    with _guard:
        if _thread and _thread.is_alive():return
        _stop.clear()
        from core.call_diagnostics import event
        event('watcher_start',rule_active=active(calls.settings()))
        _thread=threading.Thread(target=worker,name='whatsapp-incoming-watch',daemon=True)
        _thread.start()


def stop():
    _stop.set()
    if _state.get('phase')=='handling':calls.stop_speaking()

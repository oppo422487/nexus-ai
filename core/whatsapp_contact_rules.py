"""Exact caller matches and independent, durable per-contact expiry."""
import time
import unicodedata


def identity_key(value):
    value=unicodedata.normalize('NFKC',str(value)).casefold()
    key=''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value if c.isalnum() or (unicodedata.category(c).startswith('M') and not '\ufe00'<=c<='\ufe0f'))
    # A literal contact name, not the category of unknown/unsaved callers.
    return 'noname' if key in ('নোনেম','noname') else key


def live_rules(cfg):
    return [r for r in cfg.get('caller_rules',[]) if r.get('enabled',True)
            and (r.get('expires_at') is None or time.time()<r['expires_at'])]


def choose(cfg, caller):
    key=identity_key(caller)
    matches=[r for r in live_rules(cfg) if key and key in
             {identity_key(n) for n in [r['contact_name'],*r.get('aliases',[])]}]
    if len(matches)>1:raise RuntimeError('Caller matches multiple reply rules; no personalized message selected.')
    if matches:return dict(matches[0],matched=True,caller=caller)
    deadline=cfg.get('auto_answer_expires_at')
    if cfg.get('auto_answer_enabled') and (deadline is None or time.time()<deadline) and cfg.get('auto_answer_message','').strip():
        return dict(message=cfg['auto_answer_message'],matched=False,caller=caller)
    return None


def configure(contact_name,message=None,duration_minutes=None,aliases=None,enabled=True):
    from core import whatsapp_calls as calls,whatsapp_auto_reply as auto
    name=str(contact_name).strip()
    if not identity_key(name):raise ValueError('Provide the exact WhatsApp caller name or phone number.')
    if enabled:
        if not isinstance(message,str) or not message.strip() or len(message)>1500:raise ValueError('An exact message of 1–1500 characters is required.')
        if duration_minutes is not None and (type(duration_minutes) is not int or not 1<=duration_minutes<=10080):raise ValueError('Duration must be 1–10080 minutes, or omitted.')
        calls.audio_ready()
        from core.whatsapp_caller_notes import compose_message,return_ready
        cfg=calls.settings();compose_message(message,cfg)
        if cfg.get('caller_notes_enabled'):return_ready()
    with calls._settings_lock:
        cfg=calls.settings();rules=list(cfg.get('caller_rules',[]))
        previous=next((r for r in rules if identity_key(r['contact_name'])==identity_key(name)),None)
        rules=[r for r in rules if identity_key(r['contact_name'])!=identity_key(name)]
        if enabled:
            if len(rules)>=20:raise ValueError('At most 20 caller rules are supported.')
            alias=[str(a).strip() for a in (aliases or []) if str(a).strip()]
            keys={identity_key(a) for a in [name,*alias]}
            if any(keys & {identity_key(a) for a in [r['contact_name'],*r.get('aliases',[])]} for r in rules):
                raise ValueError('This name/number already belongs to another caller rule.')
            rules.append(dict(contact_name=name,aliases=alias,message=message.strip(),enabled=True,
                              expires_at=time.time()+duration_minutes*60 if duration_minutes is not None else None))
        elif previous:rules.append(dict(previous,enabled=False))
        calls.update_settings({'caller_rules':rules})
    if enabled:auto.start()
    return dict(saved=True,caller_rules=describe_rules(calls.settings()))


def current_caller(controller=None):
    """Read only the verified incoming call partner, never a sidebar/chat guess."""
    from core import whatsapp_calls as calls
    if controller is None:
        with calls.controller() as c:return current_caller(c)
    try:
        from core.whatsapp_caller_identity import local_caller
        name=local_caller(controller,calls.settings())
        from core.call_diagnostics import event
        event('caller_identity_verified',source='local_window')
        return name
    except Exception:
        pass  # Only a verified local result may bypass the online reader.
    if not calls.settings().get('visual_fallback',True):
        raise RuntimeError('Verified caller identification needs WhatsApp-window vision enabled.')
    _,plan=calls.visual_controller(controller).observe('inspect')
    if plan.get('state')!='incoming':raise RuntimeError('No current incoming call identity verified.')
    name=str(plan.get('recipient','')).strip()
    if not identity_key(name):raise RuntimeError('Incoming caller identity is not readable.')
    return name


def describe_rules(cfg):
    from datetime import datetime,timezone,timedelta
    zone=timezone(timedelta(hours=6))
    live=live_rules(cfg)
    return [dict(r,active=r in live,expires_at_local=datetime.fromtimestamp(r['expires_at'],zone).isoformat() if r.get('expires_at') else None) for r in cfg.get('caller_rules',[])]

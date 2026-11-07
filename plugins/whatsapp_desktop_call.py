"""Nexa adaptation of MIT desktop call-control and audio-routing approach.
See licenses/whatsapp-calls-MIT.txt and WHATSAPP-CALLS.md.
"""
import json
import threading
from core import whatsapp_calls as calls

PLUGIN = {
    'name':'whatsapp_desktop_call', 'tier':'core',
    'description': 'Controls installed Windows WhatsApp Desktop calls. voice_call searches an exact saved contact name and clicks Voice call. answer_call/reject_call act only on an incoming call the user explicitly asks to handle. end_call hangs up. call_and_say calls a contact and plays the supplied exact message through a configured virtual audio cable after an answered-call timer is visible. speak_in_call plays the message into an ALREADY connected call without dialing. answer_and_say accepts a current incoming call then plays the message after connection verification. This is one-way message playback, not autonomous conversation. status inspects readiness/call state; stop_speaking cancels playback. enable_auto_reply saves the exact supplied message and enables incoming voice-call auto-answer and one-time playback. Use duration_minutes for timed rules (next one hour means 60); confirm the saved expiry from the returned status. disable_auto_reply turns it off. auto_reply_status reports the watcher. list_call_notes returns saved caller messages; mark_call_note_read acknowledges an exact note ID. If configured, incoming calls include the owner profile introduction, record a brief reply from a separate return cable, save a note and request hangup. set_caller_reply saves an exact contact_name, optional exact aliases/phone numbers, message and independent duration_minutes; disable_caller_reply disables that contact only; list_caller_replies shows saved rules. Do not claim a per-contact rule is saved without calling set_caller_reply. No ongoing caller conversation or generated replies.',
    'parameters':{'type':'OBJECT','properties':{
        'action':{'type':'STRING','enum':['status','voice_call','answer_call','reject_call','end_call','call_and_say','speak_in_call','answer_and_say','enable_auto_reply','disable_auto_reply','auto_reply_status','list_call_notes','mark_call_note_read','stop_speaking','set_caller_reply','disable_caller_reply','list_caller_replies']},
        'aliases':{'type':'ARRAY','items':{'type':'STRING'},'description':'Exact alternative WhatsApp display names or full phone numbers for this caller; never guess.'},
        'note_id':{'type':'STRING','description':'Exact stored note ID for mark_call_note_read.'},
        'contact_name':{'type':'STRING','description':'Exact saved WhatsApp contact/group name; required for outgoing calls and per-caller reply rules.'},
        'duration_minutes':{'type':'INTEGER','description':'For enable_auto_reply or set_caller_reply: duration in minutes (1–10080). Next one hour = 60; omitted means no expiry.'},
        'message':{'type':'STRING','description':'Exact user-authorized words to speak, required for enable_auto_reply, set_caller_reply, call_and_say, speak_in_call and answer_and_say. Do not invent facts.'}},'required':['action']}}


def run(parameters, player=None, session_memory=None):
    action = parameters.get('action','status')
    contact = parameters.get('contact_name','').strip()
    message = parameters.get('message','').strip()
    def notify(text):
        print('[WHATSAPP_CALL] '+text,flush=True)
        if player:
            player.write_log('Nexa AI: '+text)
            if hasattr(player,'request_say'):
                player.request_say('Internal WhatsApp call result: '+text+' Explain briefly in the user language. Do not call tools or retry calls.')
    try:
        if action in ('set_caller_reply','disable_caller_reply','list_caller_replies'):
            from core import whatsapp_contact_rules as rules
            result={'caller_rules':rules.describe_rules(calls.settings())} if action=='list_caller_replies' else rules.configure(contact,message,parameters.get('duration_minutes'),parameters.get('aliases'),enabled=action=='set_caller_reply')
            return json.dumps(result,ensure_ascii=False)
        if action in ('list_call_notes','mark_call_note_read'):
            from core import whatsapp_caller_notes as notes
            result=notes.list_notes() if action=='list_call_notes' else notes.mark_read(parameters.get('note_id',''))
            return json.dumps({'untrusted_caller_notes':result},ensure_ascii=False)
        if action in ('enable_auto_reply','disable_auto_reply','auto_reply_status'):
            from core import whatsapp_auto_reply as auto
            if action=='auto_reply_status':return json.dumps(auto.status(),ensure_ascii=False)
            if action=='enable_auto_reply' and not message:
                return 'Provide the exact message before enabling automatic replies.'
            return json.dumps(auto.configure(action=='enable_auto_reply',message if action=='enable_auto_reply' else None,parameters.get('duration_minutes')),ensure_ascii=False)
        if action == 'stop_speaking':
            return json.dumps(calls.stop_speaking())
        if action in ('voice_call','call_and_say') and not contact:
            return 'Call not started: provide the exact saved contact name.'
        if action in ('call_and_say','speak_in_call','answer_and_say'):
            if not message or len(message)>1500:
                return 'Call not started: provide a message of 1–1500 characters.'
            calls.audio_ready()
            handlers={}
            if action=='answer_and_say':
                from core import whatsapp_caller_notes as notes
                cfg=calls.settings();message=notes.compose_message(message,cfg)
                if cfg.get('caller_notes_enabled'):
                    notes.return_ready();handlers={'incoming_handler':notes.take_note,'cleanup_handler':notes.end_handled_call}
            calls.reserve()  # Reserve before advertising an asynchronous job.
            def worker():
                try:
                    result=calls.message_operation(action,contact,message,notify,reserved=True,**handlers)
                    notify(json.dumps(result,ensure_ascii=False))
                except Exception as exc:
                    notify('WhatsApp call-message operation failed: '+str(exc)+'. No automatic retry.')
            try:
                threading.Thread(target=worker,daemon=True,name='whatsapp-call-message').start()
            except Exception:
                calls.release()
                raise
            return 'status=started: preparing the exact message; call/audio results follow asynchronously. Do not claim a call or delivery yet.'
        return json.dumps(calls.control(action,contact),ensure_ascii=False)
    except Exception as exc:
        error='WhatsApp call operation failed: '+str(exc)+' No automatic retry.'
        print('[WHATSAPP_CALL] '+error,flush=True)
        return error

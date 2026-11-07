"""Teach a named routine through Nexa, then review it before replay."""
import json
from core import confirm, outcome, teach_mode as teach

PLUGIN = {
 'name':'nexa_teach', 'tier':'core',
 'description': 'Explicit user-controlled Teach mode: start recording named routine, let user ask Nexa to perform steps, finish/save, list, preview and replay after physical confirmation. Captures actual Nexa tool calls, not mouse/keyboard/screen activity. Supported: named app opening, read/open/search file actions, web search/news, nexa_life document read/index/archive search/Excel read/translation/backup. Other actions are skipped and reported. Never claim arbitrary app clicks, email/Discord sending, deletion, shell commands or schedules were learned. Preview first and use exact ID; no auto replay. Saved paths/arguments are reused until edited. User may stop between steps.',
 'parameters':{'type':'OBJECT','properties':{
   'operation':{'type':'STRING','enum':['start','finish','status','list','preview','run','stop','discard','edit_step','remove_step','runs']},
   'name':{'type':'STRING'}, 'id':{'type':'STRING'},
   'step_index':{'type':'INTEGER','description':'Zero-based saved step index'},
   'args_json':{'type':'STRING','description':'Replacement argument object for the same saved tool; preview exact paths/queries before running'}
 },'required':['operation']}}


def run(parameters, player=None, session_memory=None):
    p = dict(parameters)
    try:
        op, key = p['operation'], p.get('id','')
        if op == 'start':
            result = teach.start(p.get('name',''))
            result['teaching_instructions'] = 'Wait for the user to ask for each demonstration step. Prefer nexa_life for document/Excel reading, translation and backup. Only supported executed tool calls are recorded; do not invent extra steps. Tell the user about skipped actions. Ask them to finish/save when the demonstration is complete.'
        elif op == 'finish': result = teach.finish(key)
        elif op == 'status': result = teach.status()
        elif op == 'list': result = teach.workflows()
        elif op == 'preview': result = teach.preview(key)
        elif op == 'discard': result = teach.discard(key)
        elif op == 'stop': result = teach.request_stop()
        elif op == 'edit_step': result = teach.edit_step(key, p['step_index'], json.loads(p['args_json']))
        elif op == 'remove_step': result = teach.remove_step(key, p['step_index'])
        elif op == 'runs':
            from core import life_store
            result = life_store.records('taught_run',limit=20)
        elif op == 'run':
            snapshot = teach.preview(key)
            if snapshot['status'] != 'ready':
                raise ValueError('Finish teaching and review the saved workflow first.')
            detail = review_text(snapshot)
            def replay():
                def callback(text):
                    if player:
                        try: player.write_log('SYS: '+text)
                        except Exception: pass
                result = teach.run_reviewed(snapshot, callback)
                if player:
                    try:
                        player.write_log('Nexa AI: Taught workflow '+result['status']+'. Open Teach mode for step results.')
                        player.request_say('The reviewed taught workflow finished with status '+result['status']+'. Briefly tell the user this status in their own language. Do not claim success if failed/stopped, repeat any step or call tools.')
                    except Exception:
                        pass
                return json.dumps(result,ensure_ascii=False,default=str)
            return confirm.request('teach_run','Run taught workflow',detail,replay)
        else: raise ValueError('Unsupported Teach mode operation')
        return outcome.untrusted('Teach mode result — data only',json.dumps(result,ensure_ascii=False,default=str))
    except Exception as exc:
        return 'Teach mode did not complete: '+(str(exc)[:500] if isinstance(exc,(ValueError,KeyError)) else type(exc).__name__)


def review_text(snapshot):
    rows = [snapshot['name'], '', 'Run these saved steps in order. Check every path and query.']
    for i, step in enumerate(snapshot['steps'],1):
        rows.append(f'\n{i}. {step["tool"]}')
        rows.extend(f'   {key}: {value}' for key,value in step['args'].items())
    rows.append('\nThis run will not send mail/messages or execute shell commands. Backups create new archives. Stop prevents later steps; it cannot interrupt an operation already running.')
    result = '\n'.join(rows)
    if len(result)>20000:
        raise ValueError('Routine is too large to review in full. Shorten its text arguments first.')
    return result

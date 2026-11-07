"""Opt-in teaching from Nexa tool calls, with a closed replay vocabulary."""
from copy import deepcopy
from hashlib import sha256
import json
import re
from threading import Lock, Event
from core import life_store as store

_lock = Lock()
_run_lock = Lock()
_stop = Event()
_recording_id = None
_ui_callback = None
MAX_STEPS = 24
FILE_ACTIONS = {'open', 'list', 'read', 'find', 'info', 'disk_usage'}
LIFE_ACTIONS = {'document_read', 'document_index', 'archive_search', 'excel_read', 'translate', 'backup'}
FIELDS = {
    'open_app': {'app_name'},
    'file_controller': {'action', 'path', 'name'},
    'web_search': {'mode', 'query'},
    'nexa_life': {'operation', 'path', 'destination', 'query', 'language', 'sheet', 'cell_range', 'text', 'source', 'target'},
}
SECRET = re.compile(r'AIza[\w-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[\w]{30,}|-----BEGIN .*PRIVATE KEY-----')


def bind_ui(callback):
    global _ui_callback
    _ui_callback = callback
    item = status()
    _announce(item if item.get('id') else None)


def _announce(item=None):
    if _ui_callback:
        try:
            _ui_callback(f'REC: {item["title"]} ({len(item["payload"]["steps"])})' if item else 'Teach mode')
        except Exception:
            pass


def validate(tool, args):
    if tool not in FIELDS or not isinstance(args, dict):
        raise ValueError('This tool is not supported by Teach mode.')
    if set(args)-FIELDS[tool]:
        raise ValueError('This action contains unsupported parameters.')
    data = deepcopy(args)
    if any(not isinstance(v, str) for v in data.values()) or len(json.dumps(data,ensure_ascii=False)) > 16000:
        raise ValueError('Only bounded text parameters can be recorded.')
    if SECRET.search(json.dumps(data)):
        raise ValueError('Credential-like text is not recorded.')
    for value in data.values():
        if re.search(r'(?:api_keys|gmail_token|gmail_client|calendar_token|spotify_token|life_connectors)\.json|(?:^|[/\\])\.env(?:$|\.)', value, re.I):
            raise ValueError('Private account configuration is not recorded.')
    if tool == 'open_app':
        name = data.get('app_name', '').strip()
        if name.casefold() in ('downloads','download','desktop','documents','pictures','music','videos','home'):
            return {'tool':'file_controller','args':{'action':'open','path':name}}
        if not name or re.search(r'[:/\\&|;<>\n\r]', name):
            raise ValueError('Teach mode supports application names, not paths, URLs or commands.')
    elif tool == 'file_controller':
        if data.get('action') not in FILE_ACTIONS:
            raise ValueError('Only opening and reading/searching files is supported here.')
    elif tool == 'web_search':
        if data.get('mode', 'search') not in ('search', 'news') or not data.get('query', '').strip():
            raise ValueError('Teach mode supports web search and news queries only.')
    elif data.get('operation') not in LIFE_ACTIONS:
        raise ValueError('This productivity action cannot be replayed in Teach mode.')
    return {'tool': tool, 'args': data}


def _recipe(key):
    item = store.get(key)
    if item['kind'] != 'taught_workflow':
        raise ValueError('Choose a taught workflow ID.')
    return item


def start(title):
    global _recording_id
    if not title.strip() or len(title) > 100:
        raise ValueError('Give the workflow a name of 1–100 characters.')
    with _lock:
        if _recording_id:
            raise ValueError('Finish or discard the current teaching session first.')
        if _run_lock.locked():
            raise ValueError('Wait for the running workflow to finish.')
        # No interrupted session is automatically resumed after process restart.
        for item in store.records('taught_workflow', 'recording'):
            store.update(item['id'], status='interrupted')
        item = store.add('taught_workflow', title.strip(), {'steps': [], 'skipped': [], 'version': 1}, 'recording')
        _recording_id = item['id']
        _announce(item)
        return item


def status():
    with _lock:
        return _recipe(_recording_id) if _recording_id else {'recording': False, 'running': _run_lock.locked()}


def observe(tool, args, result):
    """Called after an engine tool invocation; no screenshots or global hooks."""
    if tool == 'nexa_teach':
        return None
    with _lock:
        if not _recording_id:
            return None
        item = _recipe(_recording_id)
        payload = item['payload']
        try:
            step = validate(tool, args)
            lower = str(result).lower()
            if any(x in lower for x in ('status=failed', 'did not complete', 'tool \'', '[confirmation_pending]')):
                raise ValueError('The action failed or is waiting for confirmation; it was not recorded.')
            if tool == 'file_controller' and any(x in lower[:200] for x in ('not found', 'access denied', 'permission denied', 'could not', 'error:', 'failed')):
                raise ValueError('The file operation did not complete; it was not recorded.')
            if len(payload['steps']) >= MAX_STEPS:
                raise ValueError('Maximum 24 steps reached. Finish this teaching session.')
            step['observed_status'] = 'requested' if any(x in lower for x in ('status=started', 'status=unverified')) else 'completed'
            if len(json.dumps(payload['steps']+[step],ensure_ascii=False)) > 16000:
                raise ValueError('Routine is too large to review in full. Use file paths instead of long pasted text.')
            payload['steps'].append(step)
            message = f"Recorded step {len(payload['steps'])}: {tool}"
        except ValueError as exc:
            # Unsupported actions never retain their arguments or private results.
            payload['skipped'] = (payload['skipped'] + [{'tool':tool, 'reason':str(exc)}])[-24:]
            message = 'Not recorded: '+tool+'. '+str(exc)
        store.update(item['id'], payload=payload)
        _announce({'title':item['title'],'payload':payload})
        return message


def finish(key=''):
    global _recording_id
    with _lock:
        key = key or _recording_id
        if not key:
            raise ValueError('No teaching session is active.')
        item = _recipe(key)
        if item['status'] not in ('recording', 'interrupted'):
            raise ValueError('This workflow is already saved.')
        if not item['payload']['steps']:
            raise ValueError('No supported steps were recorded. Teach a supported action first, or discard this session.')
        item = store.update(key, status='ready')
        if key == _recording_id:
            _recording_id = None
            _announce()
        return item


def discard(key=''):
    global _recording_id
    with _lock:
        key = key or _recording_id
        if not key:
            raise ValueError('Choose a workflow to discard.')
        _recipe(key)
        if _run_lock.locked():
            raise ValueError('Stop the running workflow before discarding.')
        result = store.update(key, status='discarded', payload={'steps': [], 'skipped': [], 'version': 1})
        if key == _recording_id:
            _recording_id = None
            _announce()
        return result


def workflows():
    return [x for x in store.records('taught_workflow') if x['status'] != 'discarded']


def recover_interrupted():
    """At application startup, preserve interrupted work without replaying it."""
    with _lock:
        if _recording_id or _run_lock.locked():
            return
        for kind, state in (('taught_workflow','recording'), ('taught_run','running')):
            for item in store.records(kind,state):
                store.update(item['id'],status='interrupted')


def preview(key):
    item = _recipe(key)
    return {'id': item['id'], 'name':item['title'], 'status':item['status'], **deepcopy(item['payload']),
            'notice':'Replays the saved arguments in order. Review file paths and queries before every run. No automatic schedules or background capture.'}


def edit_step(key, index, args):
    with _lock:
        if _run_lock.locked():
            raise ValueError('Do not edit a running workflow.')
        item = _recipe(key)
        if item['status'] != 'ready':
            raise ValueError('Finish teaching before editing steps.')
        p = item['payload']
        if not 0 <= int(index) < len(p['steps']):
            raise ValueError('Step index is out of range.')
        old = p['steps'][int(index)]
        p['steps'][int(index)] = validate(old['tool'], args)
        if len(json.dumps(p['steps'],ensure_ascii=False)) > 16000:
            raise ValueError('Routine is too large to review in full.')
        return store.update(key, payload=p)


def remove_step(key, index):
    with _lock:
        if _run_lock.locked():
            raise ValueError('Do not edit a running workflow.')
        item = _recipe(key)
        if item['status'] != 'ready' or not 0 <= int(index) < len(item['payload']['steps']):
            raise ValueError('Select a step in a saved workflow.')
        p = item['payload']
        if len(p['steps']) == 1:
            raise ValueError('A workflow needs at least one step. Discard it to remove everything.')
        del p['steps'][int(index)]
        return store.update(key, payload=p)


def request_stop():
    _stop.set()
    return 'Stop requested. The current operation may finish; no subsequent step will start.'


def _perform(step):
    tool, args = step['tool'], step['args']
    if tool == 'open_app':
        from actions.open_app import open_app
        from core import appidentity
        import time
        result = open_app(args)
        if 'status=started' in result:
            # Launches reuse tray processes. Wait for a real matched window rather
            # than racing the next step immediately after the request was accepted.
            deadline = time.monotonic()+13
            while time.monotonic() < deadline and not _stop.is_set():
                for item in appidentity.running(args['app_name'], include_self=True):
                    if appidentity.focus(item):
                        return {'status':'done', 'focused':True}
                time.sleep(0.4)
            raise ValueError('App opening was not verified. Inspect the app before running again.')
        if 'status=done' not in result:
            raise ValueError('App opening failed or was not verified.')
        return {'status':'done', 'focused':True}
    if tool == 'file_controller':
        from actions.file_controller import file_controller
        result = file_controller(args)
        if any(x in result.lower() for x in ('not found', 'error:', 'failed', 'could not', 'nothing opened')):
            raise ValueError('File operation did not complete. Check the saved path.')
        return {'status':'done', 'result':result[:4000]}
    if tool == 'web_search':
        from actions.web_search import web_search
        result = web_search(args)
        if any(x in result.lower() for x in ('search failed', 'please provide', 'no results')):
            raise ValueError('Search did not return a usable result.')
        return {'status':'done', 'result':result[:6000]}
    from core import document_archive as docs, excel_adapter, life_connectors, safe_backup
    op = args['operation']
    if op == 'document_read': return docs.extract(args['path'], args.get('language','eng+ben'))
    if op == 'document_index': return docs.index(args['path'], args.get('language','eng+ben'))
    if op == 'archive_search': return docs.search(args.get('query',''))
    if op == 'excel_read': return excel_adapter.read(args['path'], args.get('sheet',''), args.get('cell_range') or 'A1:T50')
    if op == 'translate': return life_connectors.translate(args['text'], args['source'], args['target'])
    if op == 'backup': return safe_backup.backup(args['path'], args['destination'])
    raise ValueError('Unsupported replay operation')


def fingerprint(data):
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run_reviewed(snapshot, notify=None):
    if not _run_lock.acquire(blocking=False):
        raise ValueError('Another taught workflow is running.')
    run = None
    try:
        with _lock:
            if _recording_id:
                raise ValueError('Finish teaching before replaying.')
            current = preview(snapshot['id'])
            if current['status'] != 'ready' or fingerprint(current) != fingerprint(snapshot):
                raise ValueError('The workflow changed after review. Review it again before running.')
            steps = [validate(s['tool'], s['args']) for s in snapshot['steps']]
            if not 1 <= len(steps) <= MAX_STEPS:
                raise ValueError('Workflow has an invalid step count.')
        _stop.clear()
        p = {'workflow_id':snapshot['id'], 'workflow_fingerprint':fingerprint(snapshot), 'results':[]}
        run = store.add('taught_run', snapshot['name'], p, 'running')
        for i, step in enumerate(steps):
            if _stop.is_set():
                return store.update(run['id'], status='stopped', payload=p)
            if notify: notify(f'Teach mode: step {i+1}/{len(steps)} — {step["tool"]}')
            p['current_step'] = i+1
            store.update(run['id'], payload=p)
            result = _perform(step)
            encoded = json.dumps(result, ensure_ascii=False, default=str)
            if len(encoded) > 20000:
                result = {'truncated':True, 'preview':encoded[:16000], 'notice':'Large result preview only; use the original tool for the full content.'}
            p['results'].append({'step':i+1,'status':'done','result':result})
            store.update(run['id'], payload=p)
        store.activity('taught_workflow', snapshot['name'], snapshot['id'], f'Completed {len(steps)} reviewed steps')
        return store.update(run['id'], status='done', payload=p)
    except Exception as exc:
        if run:
            p['error'] = str(exc)[:500] if isinstance(exc, ValueError) else type(exc).__name__
            return store.update(run['id'], status='failed', payload=p)
        raise
    finally:
        _run_lock.release()

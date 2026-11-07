"""Optional account/model adapters. Nothing authenticates or downloads on import."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
import json
import re
import uuid
from core import life_store as store

CONFIG = store.ROOT / 'config/life_connectors.json'
CAL_TOKEN = store.ROOT / 'config/calendar_token.json'
SPOTIFY_TOKEN = store.ROOT / 'config/spotify_token.json'
CAL_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
_calendar_lock = Lock()


def settings():
    return json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}


def save_spotify(client_id, client_secret, redirect='http://127.0.0.1:8888/callback'):
    if not client_id.strip() or not client_secret.strip():
        raise ValueError('Spotify client ID and secret are required in this local settings window.')
    if redirect != 'http://127.0.0.1:8888/callback':
        raise ValueError('Register http://127.0.0.1:8888/callback in the Spotify app dashboard.')
    data = settings()
    new = dict(client_id=client_id.strip(), client_secret=client_secret.strip(), redirect_uri=redirect)
    if data.get('spotify') != new:
        SPOTIFY_TOKEN.unlink(missing_ok=True)
    data['spotify'] = new
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data), encoding='utf-8')


def spotify(interactive=False):
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    cfg = settings().get('spotify', {})
    if not cfg:
        raise ValueError('Set up Spotify in Work & documents → Connections.')
    auth = SpotifyOAuth(**cfg, scope='user-read-playback-state user-modify-playback-state',
                        cache_path=str(SPOTIFY_TOKEN), requests_timeout=15, open_browser=interactive)
    if interactive:
        auth.get_access_token(as_dict=False)
    elif not auth.get_cached_token():
        raise ValueError('Spotify is not connected; connect in the native settings window.')
    return spotipy.Spotify(auth_manager=auth, requests_timeout=15, retries=0, status_retries=0)


def music(operation, query='', device_id='', volume=50):
    api = spotify()
    if operation == 'status':
        return {'playback': api.current_playback(), 'devices': api.devices()}
    if operation == 'search':
        return api.search(q=query, type='track', limit=5)
    if operation == 'play':
        if query and not query.startswith('spotify:track:'):
            raise ValueError('Search first, then use the exact spotify:track: URI to play.')
        api.start_playback(device_id=device_id or None, **({'uris': [query]} if query else {}))
    elif operation == 'pause':
        api.pause_playback(device_id=device_id or None)
    elif operation == 'next':
        api.next_track(device_id=device_id or None)
    elif operation == 'previous':
        api.previous_track(device_id=device_id or None)
    elif operation == 'volume':
        api.volume(max(0, min(int(volume), 100)), device_id=device_id or None)
    else:
        raise ValueError('Unknown Spotify operation')
    return {'request_accepted': True, 'operation': operation, 'note': 'Spotify Premium and an active player are required for playback control.'}


def calendar(interactive=False):
    from core.gmail_service import CLIENT
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    with _calendar_lock:
        try:
            creds = Credentials.from_authorized_user_file(str(CAL_TOKEN), CAL_SCOPES) if CAL_TOKEN.exists() else None
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception:
            if not interactive:
                raise ValueError('Calendar authorization expired. Connect Calendar again.') from None
            creds = None
        if not creds or not creds.valid or not creds.has_scopes(CAL_SCOPES):
            if not interactive:
                raise ValueError('Connect Calendar in Work & documents → Connections first.')
            if not CLIENT.exists():
                raise ValueError('Import the Google Desktop OAuth JSON using Gmail setup first, and enable Google Calendar API.')
            creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT), CAL_SCOPES).run_local_server(
                port=0, timeout_seconds=180, access_type='offline', prompt='consent')
        CAL_TOKEN.write_text(creds.to_json(), encoding='utf-8')
    return build('calendar', 'v3', http=AuthorizedHttp(creds, http=httplib2.Http(timeout=20)), cache_discovery=False)


def timestamp(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Include the timezone, e.g. 2026-10-28T10:00:00+06:00.')
    return dt


def calendar_events(query=''):
    now = datetime.now(timezone.utc)
    return calendar().events().list(calendarId='primary', timeMin=now.isoformat(),
        timeMax=(now+timedelta(days=30)).isoformat(), singleEvents=True, orderBy='startTime', maxResults=30, q=query).execute().get('items', [])


def event_payload(title, start, end, description=''):
    a, b = timestamp(start), timestamp(end)
    if not title.strip() or b <= a:
        raise ValueError('Provide a title and an end time after the start time.')
    return {'id': uuid.uuid4().hex, 'summary': title[:200], 'description': description[:4000],
            'start': {'dateTime': a.isoformat()}, 'end': {'dateTime': b.isoformat()}}


def create_event(payload):
    # Persist the chosen Google event ID before sending; a timeout is not proof of failure.
    receipt = store.add('calendar_request', payload['summary'], {'event': payload}, 'submitting')
    try:
        result = calendar().events().insert(calendarId='primary', body=payload, sendUpdates='none').execute()
        store.update(receipt['id'], status='done', payload={'event': payload, 'google_id': result['id']})
        return {'id': result['id'], 'link': result.get('htmlLink'), 'created': True}
    except Exception:
        store.update(receipt['id'], status='unknown')
        raise ValueError('Calendar request outcome is unknown. Check Calendar before creating another event; request saved locally.') from None


def offline_languages():
    root = store.DATA / 'translation_models'
    result = []
    if root.exists():
        for path in root.glob('*/metadata.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            result.append({'source': data['from_code'], 'target': data['to_code'], 'path': str(path.parent)})
    return result


def translate(text, source, target):
    import re
    import ctranslate2
    import sentencepiece
    if not text or len(text) > 20000:
        raise ValueError('Translation text must contain 1–20000 characters.')
    pair = next((x for x in offline_languages() if x['source'] == source and x['target'] == target), None)
    if not pair:
        raise ValueError('This offline language pair is not installed. Import the matching .argosmodel package in settings.')
    path = Path(pair['path'])
    tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(path/'sentencepiece.model'))
    model = ctranslate2.Translator(str(path/'model'), device='cpu', compute_type='int8', intra_threads=2)
    metadata = json.loads((path/'metadata.json').read_text(encoding='utf-8'))
    # Local punctuation splitting avoids hidden sentence-model downloads and loading
    # a second language pipeline. Long paragraphs use bounded 200-token chunks.
    sentences = re.split(r'(?<=[.!?।])\s+|\n+', text)
    batches = []
    for sentence in sentences:
        tokens = tokenizer.encode(sentence, out_type=str)
        batches.extend(tokens[i:i+200] for i in range(0, len(tokens), 200))
    prefix = metadata.get('target_prefix', '')
    result = model.translate_batch(batches, target_prefix=[[prefix]]*len(batches) if prefix else None,
        beam_size=4, max_decoding_length=512, replace_unknowns=True)
    translated = ' '.join(tokenizer.decode(x.hypotheses[0]).removeprefix(prefix).strip() for x in result)
    return {'text': translated, 'source': source, 'target': target, 'offline': True,
            'notice': 'Local Argos/CTranslate2 model; machine translation should be reviewed.'}


def install_translation_model(path):
    from pathlib import PurePosixPath
    import shutil
    import tempfile
    import zipfile
    p = Path(path).expanduser().resolve()
    if not p.is_file() or p.stat().st_size > 1024**3 or p.suffix.lower() != '.argosmodel':
        raise ValueError('Select an official Argos .argosmodel package.')
    root = store.DATA/'translation_models'
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p) as archive, tempfile.TemporaryDirectory(dir=root) as temp:
        infos = archive.infolist()
        if len(infos) > 3000 or sum(i.file_size for i in infos) > 1024**3:
            raise ValueError('Translation model archive is too large.')
        for info in infos:
            name = info.filename
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or ':' in name or '\\' in name or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe model archive path.')
        archive.extractall(temp)
        metadata = list(Path(temp).glob('*/metadata.json'))
        if len(metadata) != 1:
            raise ValueError('Expected one model metadata.json inside the package.')
        folder = metadata[0].parent
        data = json.loads(metadata[0].read_text(encoding='utf-8'))
        if not all(re.fullmatch('[a-z]{2,3}', data.get(k, '')) for k in ('from_code', 'to_code')):
            raise ValueError('Invalid model language codes.')
        if not (folder/'model/model.bin').exists() or not (folder/'sentencepiece.model').exists():
            raise ValueError('This adapter requires an Argos CTranslate2 + SentencePiece model.')
        target = root/(data['from_code']+'-'+data['to_code'])
        if target.exists():
            return offline_languages()
        shutil.move(str(folder), str(target))
    return offline_languages()


def download_bengali_models():
    import tempfile
    import urllib.request
    for pair in ('en_bn', 'bn_en'):
        url = 'https://data.argosopentech.com/argospm/v1/translate-'+pair+'-1_9.argosmodel'
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/'model.argosmodel'
            with urllib.request.urlopen(url, timeout=60) as response, target.open('wb') as stream:
                total = 0
                while chunk := response.read(1024*1024):
                    total += len(chunk)
                    if total > 200*1024*1024:
                        raise ValueError('Model download exceeds 200 MB.')
                    stream.write(chunk)
            install_translation_model(target)
    return offline_languages()


def transcribe(path):
    from core.document_archive import selected_file
    from faster_whisper import WhisperModel
    p = selected_file(path)
    if p.suffix.lower() not in ('.wav', '.mp3', '.m4a', '.ogg', '.flac', '.mp4'):
        raise ValueError('Select a supported meeting audio/video file.')
    # local_files_only prevents a surprise multi-GB model download during a voice turn.
    model = WhisperModel('small', device='cpu', compute_type='int8', local_files_only=True)
    segments, info = model.transcribe(str(p), vad_filter=True)
    if info.duration > 3600:
        raise ValueError('Select a recording of at most one hour.')
    lines = [f'[{s.start:.1f}–{s.end:.1f}] {s.text}' for s in segments]
    return {'text': '\n'.join(lines)[:200000], 'language': info.language, 'duration': info.duration}

from contextlib import contextmanager
"""Gmail desktop OAuth and local contacts. Sending is gated by the plugin UI."""
import base64
import json
import re
import sqlite3
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / 'config/gmail_client.json'
TOKEN = ROOT / 'config/gmail_token.json'
DB = ROOT / 'memory/gmail.sqlite3'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
LOCK = Lock()


def import_client(source):
    data = json.loads(Path(source).read_text(encoding='utf-8-sig'))
    installed = data.get('installed', {})
    if not all(installed.get(k) for k in ('client_id','client_secret','auth_uri','token_uri')):
        raise ValueError('Google Cloud থেকে Desktop app OAuth JSON দিন। Gemini API key বা Web client JSON নয়।')
    if installed['auth_uri'] != 'https://accounts.google.com/o/oauth2/auth' or installed['token_uri'] != 'https://oauth2.googleapis.com/token':
        raise ValueError('Google OAuth endpoint সঠিক নয়। Google Cloud থেকে নতুন JSON ডাউনলোড করুন।')
    CLIENT.parent.mkdir(parents=True, exist_ok=True)
    # Changing clients requires a fresh account authorization.
    if CLIENT.exists() and json.loads(CLIENT.read_text(encoding='utf-8')) != data:
        TOKEN.unlink(missing_ok=True)
    CLIENT.write_text(json.dumps(data), encoding='utf-8')


@contextmanager
def store():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute('CREATE TABLE IF NOT EXISTS contacts(name TEXT PRIMARY KEY COLLATE NOCASE,email TEXT NOT NULL)')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def address(value):
    if any(c in value for c in '\r\n'):
        raise ValueError('Invalid email address')
    parsed = parseaddr(value)[1]
    if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', parsed):
        raise ValueError('A single valid email address is required')
    return parsed


def save_contact(name, email):
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError('Contact name is required (maximum 100 characters)')
    email = address(email)
    with store() as conn:
        conn.execute('INSERT INTO contacts VALUES (?,?) ON CONFLICT(name) DO UPDATE SET email=excluded.email', (name, email))
    return {'name': name, 'email': email}


def contacts():
    with store() as conn:
        return [dict(name=n, email=e) for n, e in conn.execute('SELECT name,email FROM contacts ORDER BY name')]


def resolve(value):
    if '@' in value:
        return address(value)
    with store() as conn:
        row = conn.execute('SELECT email FROM contacts WHERE name=?', (value.strip(),)).fetchone()
    if not row:
        raise ValueError('Recipient address is unknown. Ask the user; never guess it.')
    return row[0]


def service(interactive=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    with LOCK:
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception:
            if not interactive:
                raise ValueError('Gmail authorization expired. Gmail setup থেকে আবার connect করুন।') from None
        if not creds or not creds.valid or not creds.has_scopes(SCOPES):
            if not interactive:
                raise ValueError('Gmail is not connected. Use Settings > Gmail connect.')
            if not CLIENT.exists():
                raise ValueError('Place your Google Desktop OAuth client JSON at config/gmail_client.json first.')
            creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES).run_local_server(port=0, timeout_seconds=180, access_type='offline', prompt='consent')
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json(), encoding='utf-8')
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    return build('gmail', 'v1', http=AuthorizedHttp(creds, http=httplib2.Http(timeout=20)), cache_discovery=False)


def connect():
    return service(True).users().getProfile(userId='me').execute().get('emailAddress')


def inbox(query='is:unread in:inbox', limit=5):
    api = service()
    result = api.users().messages().list(userId='me', q=query, maxResults=max(1, min(int(limit), 10))).execute()
    messages = []
    for entry in result.get('messages', []):
        item = api.users().messages().get(userId='me', id=entry['id'], format='metadata', metadataHeaders=['From','Subject','Date','Message-ID']).execute()
        headers = {h['name'].lower(): h['value'] for h in item.get('payload', {}).get('headers', [])}
        messages.append({'id': item['id'], 'from': headers.get('from',''), 'subject': headers.get('subject',''), 'date': headers.get('date',''), 'snippet': item.get('snippet','')[:1500]})
    return messages


def read(message_id):
    item = service().users().messages().get(userId='me', id=message_id, format='full').execute()
    headers = {h['name'].lower(): h['value'] for h in item.get('payload',{}).get('headers',[])}
    chunks = []
    def walk(part):
        if part.get('mimeType') == 'text/plain' and part.get('body',{}).get('data'):
            data = part['body']['data']
            chunks.append(base64.urlsafe_b64decode(data + '='*(-len(data)%4)).decode('utf-8',errors='replace'))
        for child in part.get('parts',[]):
            walk(child)
    walk(item.get('payload',{}))
    return {'id': item['id'], 'threadId': item.get('threadId'), 'from': headers.get('from',''), 'reply_to': headers.get('reply-to',headers.get('from','')), 'subject': headers.get('subject',''), 'message_id': headers.get('message-id',''), 'body': ('\n'.join(chunks) or item.get('snippet',''))[:20000]}


def send(recipient, subject, body, reply=None):
    recipient = address(recipient)
    if not subject.strip() or not body.strip() or '\n' in subject or '\r' in subject:
        raise ValueError('Valid subject and body are required')
    msg = EmailMessage()
    msg['To'] = recipient
    msg['Subject'] = subject
    if reply and reply.get('message_id'):
        msg['In-Reply-To'] = reply['message_id']
        msg['References'] = reply['message_id']
    msg.set_content(body)
    payload = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')}
    if reply and reply.get('threadId'):
        payload['threadId'] = reply['threadId']
    result = service().users().messages().send(userId='me', body=payload).execute()
    if not isinstance(result.get('id'), str) or not result['id']:
        raise ValueError('Gmail did not return a message ID. Check Sent before retrying; do not automatically resend.')
    return {'sent': True, 'id': result.get('id'), 'recipient': recipient}


def disconnect():
    # Local disconnect; Google Account permissions can separately be revoked.
    TOKEN.unlink(missing_ok=True)

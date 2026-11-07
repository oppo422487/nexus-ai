"""Opt-in public HTTPS change monitors, bounded and DNS-pinned per request."""
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlsplit, urljoin
import difflib
import http.client
import ipaddress
import socket
import ssl
from core import life_store as store


def public_target(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('Only public HTTPS URLs on port 443 without embedded credentials are supported.')
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
        raise ValueError('Private/local network monitoring is not supported.')
    # create_connection accepts a host/port pair even for an IPv6 address.
    return parts, (addresses[0][4][0], 443)


def fetch(url, redirects=0):
    parts, address = public_target(url)
    class PinnedHTTPS(http.client.HTTPSConnection):
        def connect(self):
            raw = socket.create_connection(address, timeout=self.timeout)
            try:
                self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
            except Exception:
                raw.close()
                raise
    conn = PinnedHTTPS(parts.hostname, timeout=10, context=ssl.create_default_context())
    try:
        conn.request('GET', (parts.path or '/') + ('?'+parts.query if parts.query else ''),
                     headers={'User-Agent': 'NexaPersonalMonitor/1.0', 'Accept': 'text/html,text/plain', 'Accept-Encoding': 'identity'})
        response = conn.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            if redirects >= 3:
                raise ValueError('Too many redirects')
            return fetch(urljoin(url, response.getheader('Location', '')), redirects+1)
        if response.status != 200:
            raise ValueError('Site returned HTTP ' + str(response.status))
        content_type = response.getheader('Content-Type', '').lower()
        if not content_type.startswith(('text/html', 'text/plain')):
            raise ValueError('Only text/HTML pages are supported; login pages and JavaScript apps may not expose their data.')
        raw = response.read(1024*1024+1)
        if len(raw) > 1024*1024:
            raise ValueError('Page exceeds 1 MB.')
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
            tag.decompose()
        return ' '.join(soup.get_text(' ', strip=True).split())[:200000]
    finally:
        conn.close()


def add(title, url, keyword='', interval_minutes=60):
    public_target(url)
    return store.add('monitor', title, {'url': url, 'keyword': keyword[:300],
        'interval_minutes': max(5, min(int(interval_minutes), 10080)), 'checked': '', 'hash': '', 'text': ''}, 'active')


def check(key):
    item = store.get(key)
    if item['kind'] != 'monitor':
        raise ValueError('Not a monitor')
    p = item['payload']
    try:
        text = fetch(p['url'])
        digest = sha256(text.encode()).hexdigest()
        changed = bool(p['hash']) and p['hash'] != digest
        relevant = not p['keyword'] or p['keyword'].casefold() in text.casefold()
        result = {'url': p['url'], 'baseline': not bool(p['hash']), 'changed': changed,
                  'relevant': relevant, 'checked': store.now(), 'sha256': digest}
        if changed and relevant:
            result['diff'] = '\n'.join(difflib.unified_diff(p.get('text', '').split('. '), text.split('. '), lineterm=''))[:6000]
            store.add('change', item['title'], result, 'new')
        p.update(hash=digest, text=text, checked=result['checked'], error='')
        store.update(key, payload=p)
        return result
    except Exception as exc:
        p.update(checked=store.now(), error=type(exc).__name__)
        store.update(key, payload=p)
        raise


def poll_due(notify):
    now = datetime.now(timezone.utc)
    for item in store.records('monitor', 'active', 100):
        p = item['payload']
        if p.get('checked') and (now-datetime.fromisoformat(p['checked'])).total_seconds() < p['interval_minutes']*60:
            continue
        try:
            result = check(item['id'])
            if result['changed'] and result['relevant']:
                notify('নজরদারিতে পরিবর্তন পাওয়া গেছে: ' + item['title'] + ' — ' + p['url'])
        except Exception:
            # Report once per failure streak; unchanged pages remain quiet.
            if not p.get('error'):
                notify('নজরদারি পরীক্ষা হয়নি: ' + item['title'] + '। কাজ ও ডকুমেন্ট থেকে অবস্থা দেখুন।')

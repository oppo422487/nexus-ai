"""Verified ZIP backups and non-overwriting restore to a new destination."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
from datetime import datetime
import json
import os
import zipfile
from core import life_store as store

MAX_BYTES = 500 * 1024 * 1024
MAX_FILES = 3000
SKIP = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache'}


def backup(source, destination):
    from actions.file_controller import _resolve_path
    if not str(source).strip() or not str(destination).strip():
        raise ValueError('Explicit source and destination paths are required.')
    if _resolve_path(str(source)).is_symlink():
        raise ValueError('Select the original source, not a symlink.')
    src = _resolve_path(str(source)).resolve()
    dest = _resolve_path(str(destination)).resolve()
    if not src.exists() or src.is_symlink():
        raise ValueError('Source missing or symlink; select an existing file/folder.')
    if src.is_dir() and dest.is_relative_to(src):
        raise ValueError('Backup destination cannot be inside its source.')
    dest.mkdir(parents=True, exist_ok=True)
    name = src.name + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.nexa.zip'
    target = dest / name
    files = []
    total = 0
    for p in ([src] if src.is_file() else src.rglob('*')):
        if not p.is_file() or (src.is_dir() and any(part in SKIP for part in p.relative_to(src).parts)):
            continue
        files.append(p)
        total += p.stat().st_size
        if len(files) > MAX_FILES or total > MAX_BYTES:
            raise ValueError('Backup limit: 3000 files / 500 MB. Select a smaller folder.')
    if any(p.is_symlink() or not p.resolve().is_relative_to(src if src.is_dir() else src.parent) for p in files):
        raise ValueError('Symlink/outside-source path found; no backup created.')
    if len(files) > MAX_FILES or sum(p.stat().st_size for p in files) > MAX_BYTES:
        raise ValueError('Backup limit: 3000 files / 500 MB. Select a smaller folder.')
    entries = []
    try:
        with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
            for p in files:
                relative = str(p.relative_to(src) if src.is_dir() else Path(p.name)).replace('\\','/')
                data = p.read_bytes()
                archive.writestr('files/' + relative, data)
                entries.append({'path': relative, 'sha256': sha256(data).hexdigest(), 'size': len(data)})
            archive.writestr('manifest.json', json.dumps({'version': 1, 'source': str(src), 'files': entries}))
        inspect(target)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    receipt = {'archive': str(target), 'sha256': sha256(target.read_bytes()).hexdigest(), 'files': len(entries), 'encrypted': False}
    store.add('backup', src.name, receipt, 'verified')
    store.activity('backup', src.name, str(target), json.dumps(receipt))
    return receipt


def inspect(path):
    p = Path(path).expanduser().resolve()
    with zipfile.ZipFile(p) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES+1 or sum(i.file_size for i in infos) > MAX_BYTES+1024*1024:
            raise ValueError('Archive exceeds restore limits.')
        names = [i.filename for i in infos]
        if len(set(n.casefold() for n in names)) != len(names):
            raise ValueError('Duplicate archive paths.')
        if 'manifest.json' not in names:
            raise ValueError('Not a Nexa backup: missing manifest.')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('version') != 1 or not isinstance(manifest.get('files'), list):
            raise ValueError('Unsupported backup manifest.')
        expected = {'manifest.json'}
        for entry in manifest.get('files', []):
            raw = entry['path']
            rel = PurePosixPath(raw)
            if rel.is_absolute() or any(part in ('..', '.', '') for part in raw.split('/')) or '\\' in raw or ':' in raw:
                raise ValueError('Unsafe archive path.')
            name = 'files/' + raw
            if name in expected:
                raise ValueError('Duplicate manifest entry.')
            expected.add(name)
            data = archive.read(name)
            if len(data) != entry['size'] or sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Backup checksum mismatch.')
        if expected != set(names):
            raise ValueError('Unlisted archive entries.')
    return manifest


def restore(archive_path, destination):
    from actions.file_controller import _resolve_path
    if not str(archive_path).strip() or not str(destination).strip():
        raise ValueError('Explicit archive and new destination paths are required.')
    src = _resolve_path(str(archive_path)).resolve()
    manifest = inspect(src)
    dest = _resolve_path(str(destination)).resolve()
    if dest.exists():
        raise ValueError('Restore requires a NEW destination folder. Existing files are never overwritten.')
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(src) as archive:
        for entry in manifest['files']:
            target = dest / entry['path']
            if not target.resolve().is_relative_to(dest):
                raise ValueError('Restore path escaped destination.')
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read('files/'+entry['path'])
            if len(data) != entry['size'] or sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Archive changed during restore; destination may be partial.')
            with target.open('xb') as stream:
                stream.write(data)
    store.activity('restore', dest.name, str(dest), f"Restored {len(manifest['files'])} verified files")
    return {'destination': str(dest), 'files': len(manifest['files']), 'verified': True}

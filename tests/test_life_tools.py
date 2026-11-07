import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import life_store as store, document_archive as docs, safe_backup, excel_adapter
from core import life_workflows as work, life_monitor as monitor, life_connectors as accounts


class LifeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = patch.object(store, 'DB', self.root/'life.sqlite3'); self.db.start()
        self.data = patch.object(store, 'DATA', self.root/'private'); self.data.start()

    def tearDown(self):
        self.data.stop(); self.db.stop(); self.temp.cleanup()

    def test_archive_search_tracks_changed_and_missing_original(self):
        path = self.root/'facts.txt'; path.write_text('Uniqueproject has a deadline of 30 October. No other dates were agreed.', encoding='utf8')
        result = docs.index(path)
        self.assertEqual(docs.index(path)['document_id'], result['document_id'])
        hits = docs.search('Uniqueproject')
        self.assertEqual(hits[0]['source_status'], 'unchanged')
        self.assertIn('chars', hits[0]['location'])
        path.write_text('Changed original', encoding='utf8')
        self.assertEqual(docs.search('Uniqueproject')[0]['source_status'], 'changed_since_index')
        path.unlink()
        self.assertEqual(docs.search('Uniqueproject')[0]['source_status'], 'missing')
        docs.remove(result['document_id'])
        self.assertEqual(docs.search('Uniqueproject'), [])

    def test_invalid_ai_citation_returns_evidence_not_unverified_answer(self):
        path = self.root/'facts.txt'; path.write_text('Uniqueproject deadline is October.', encoding='utf8'); docs.index(path)
        with patch('core.gemini.text', return_value='{"answer":"made up","citations":["unknown"]}'):
            result = docs.answer('Uniqueproject')
        self.assertNotEqual(result['answer'], 'made up')
        self.assertTrue(result['sources'])

    def test_scanned_pdf_uses_rendered_page_for_ocr(self):
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (800, 300), 'white'); ImageDraw.Draw(image).text((40, 60), 'NEXA SCANNED PAGE 2468', fill='black')
        path = self.root/'scanned.pdf'; image.save(path, 'PDF')
        dimensions = []
        def ocr(image, language):
            dimensions.append(image.size)
            return 'NEXA SCANNED PAGE 2468'
        with patch.object(docs, 'ocr_image', side_effect=ocr):
            result = docs.extract(path)
        self.assertIn('2468', result['pages'][0]['text'])
        self.assertEqual(result['metadata']['ocr_pages'], [1])
        self.assertGreater(dimensions[0][0], 800)

    def test_missing_ocr_engine_is_actionable(self):
        with patch.object(docs, 'tesseract_path', return_value=''):
            with self.assertRaisesRegex(ValueError, 'OCR engine missing'):
                docs.ocr_image(None)

    def test_backup_restore_hashes_and_never_overwrites(self):
        source = self.root/'source'; source.mkdir(); (source/'file.txt').write_text('sensitive sample', encoding='utf8')
        result = safe_backup.backup(str(source), str(self.root/'backups'))
        target = self.root/'restored'
        restored = safe_backup.restore(result['archive'], str(target))
        self.assertTrue(restored['verified'])
        self.assertEqual((target/'file.txt').read_text(), 'sensitive sample')
        with self.assertRaisesRegex(ValueError, 'NEW'):
            safe_backup.restore(result['archive'], str(target))
        with self.assertRaises(ValueError):
            safe_backup.backup(str(source), str(source/'nested'))

    def test_bad_backup_manifest_rejected_before_destination_created(self):
        path = self.root/'evil.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('manifest.json', json.dumps({'version': 1, 'files': [{'path': '../escape', 'size': 1, 'sha256': 'bad'}]}))
            z.writestr('files/../escape', 'x')
        target = self.root/'target'
        with self.assertRaises(ValueError):
            safe_backup.restore(path, str(target))
        self.assertFalse(target.exists())

    def test_excel_formula_is_read_as_text_and_limits_apply(self):
        from openpyxl import Workbook
        path = self.root/'book.xlsx'; book = Workbook(); book.active['A1'] = 'sample'; book.active['B1'] = '=1+2'; book.save(path); book.close()
        data = excel_adapter.read(path)
        self.assertTrue(data['read_only'])
        self.assertTrue(any(x.get('formula') == '=1+2' for x in data['cells']))
        with self.assertRaises(ValueError):
            excel_adapter.read(path, cell_range='A1:ZZ9999')

    def test_job_resumes_only_unfinished_steps(self):
        job = work.make_job('two steps', [{'operation': 'archive_search', 'args': {'query': 'a'}}, {'operation': 'archive_search', 'args': {'query': 'b'}}])
        with patch.object(work, '_step', side_effect=[{'receipt': 1}, ValueError('temporary')]) as runner:
            with self.assertRaises(ValueError):
                work.run_job(job['id'])
            self.assertEqual(runner.call_count, 2)
        with patch.object(work, '_step', return_value={'receipt': 2}) as runner:
            result = work.run_job(job['id'])
            self.assertEqual(runner.call_count, 1)
            self.assertEqual(result['status'], 'done')
        with patch.object(work, '_step') as runner:
            work.run_job(job['id']); runner.assert_not_called()

    def test_interrupted_mutating_step_is_not_replayed(self):
        job = work.make_job('backup', [{'operation': 'backup', 'args': {'source': 'x', 'destination': 'y'}}])
        payload = job['payload']; payload['steps'][0]['status'] = 'running'
        store.update(job['id'], status='running', payload=payload)
        work.recover_jobs()
        with patch.object(work, '_step') as runner:
            with self.assertRaisesRegex(ValueError, 'not repeated'):
                work.run_job(job['id'])
            runner.assert_not_called()

    def test_meeting_quotes_verified_acceptance_idempotent(self):
        raw = {'summary': 'sample', 'tasks': [{'title': 'Send file', 'owner': 'Ali', 'quote': 'Ali will send the file.', 'due': ''}, {'title': 'Invented', 'quote': 'not in transcript'}]}
        with patch('core.gemini.text', return_value=json.dumps(raw)):
            result = work.meeting_preview('Ali will send the file.', 'synthetic')
        self.assertEqual(len(result['payload']['tasks']), 1)
        first = work.accept_meeting(result['id']); second = work.accept_meeting(result['id'])
        self.assertEqual(first, second); self.assertEqual(len(store.records('followup')), 1)

    def test_due_followup_notifies_once_and_survives_reload(self):
        due = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        result = work.followup('Sample promise', due, 'Ali', 'sample', 'exact quote')
        messages = []
        work.tick(messages.append); work.tick(messages.append)
        self.assertEqual(len(messages), 1)
        self.assertTrue(store.get(result['id'])['payload']['notified'])

    def test_private_monitor_urls_rejected(self):
        for url in ['http://example.com', 'https://user:pass@example.com', 'https://example.com:8443']:
            with self.assertRaises(ValueError):
                monitor.public_target(url)
        with patch.object(socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(ValueError, 'Private'):
                monitor.public_target('https://example.com')

    def test_monitor_baseline_changes_and_silent_unchanged(self):
        with patch.object(monitor, 'public_target'):
            item = monitor.add('Scholarship', 'https://example.com', 'deadline')
        with patch.object(monitor, 'fetch', side_effect=['deadline October.', 'deadline October.', 'deadline November.', 'deadline November.']):
            self.assertTrue(monitor.check(item['id'])['baseline'])
            self.assertFalse(monitor.check(item['id'])['changed'])
            self.assertTrue(monitor.check(item['id'])['changed'])
            self.assertFalse(monitor.check(item['id'])['changed'])
        self.assertEqual(len(store.records('change')), 1)

    def test_calendar_time_and_unknown_outcome_saved(self):
        with self.assertRaises(ValueError):
            accounts.event_payload('sample', '2026-10-28T10:00:00', '2026-10-28T11:00:00')
        payload = accounts.event_payload('sample', '2026-10-28T10:00:00+06:00', '2026-10-28T11:00:00+06:00')
        with patch.object(accounts, 'calendar', side_effect=TimeoutError()):
            with self.assertRaisesRegex(ValueError, 'unknown'):
                accounts.create_event(payload)
        self.assertEqual(store.records('calendar_request')[0]['status'], 'unknown')

    def test_calendar_create_is_behind_physical_confirmation(self):
        from plugins import nexa_life
        args = dict(operation='calendar_create', title='sample', start='2026-10-28T10:00:00+06:00', end='2026-10-28T11:00:00+06:00')
        with patch('core.confirm.request', return_value='pending') as confirm, patch.object(accounts, 'create_event') as send:
            self.assertEqual(nexa_life.run(args), 'pending')
            send.assert_not_called(); self.assertIn('sample', confirm.call_args.args[2])

    def test_spotify_controls_use_exact_track_uri(self):
        api = Mock()
        with patch.object(accounts, 'spotify', return_value=api):
            with self.assertRaises(ValueError):
                accounts.music('play', 'a song title')
            accounts.music('play', 'spotify:track:sample')
        api.start_playback.assert_called_once_with(device_id=None, uris=['spotify:track:sample'])


class ExcelMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_server_lists_tool_and_restricts_roots(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root/'sample.xlsx'; book = Workbook(); book.active['A1'] = 'MCP sample'; book.save(path); book.close()
            params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'excel_mcp_server.py')], env={**os.environ, 'NEXA_EXCEL_ROOTS': str(root)})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertIn('read_excel', [x.name for x in tools.tools])
                    result = await asyncio.wait_for(session.call_tool('read_excel', {'path': str(path)}), 20)
                    self.assertFalse(result.isError)
                    self.assertIn('MCP sample', str(result.content))
                    result = await asyncio.wait_for(session.call_tool('read_excel', {'path': str(ROOT/'outside.xlsx')}), 20)
                    self.assertTrue(result.isError)


if __name__ == '__main__':
    unittest.main()

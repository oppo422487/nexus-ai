"""Startup context is factual, local, bounded and read-only."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from unittest.mock import Mock, AsyncMock
import asyncio
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.startup_briefing import context, instruction


class BriefingTests(unittest.TestCase):
    def test_interests_projects_and_only_unfinished_work(self):
        memory = {'preferences':{'interest':{'value':'Robotics'}}, 'projects':{'nexa':{'value':'Improve the desktop assistant'}}}
        rows = [
            {'id':'1','title':'Finish report','kind':'followup','status':'open','payload':{'due':'2026-10-28T10:00:00+06:00'}},
            {'id':'2','title':'Already completed','kind':'followup','status':'done','payload':{}},
            {'id':'3','title':'Cancelled','kind':'followup','status':'cancelled','payload':{}},
        ]
        with patch('core.life_store.records', side_effect=lambda kind, **kw: rows if kind=='followup' else []):
            result=context(memory)
        self.assertEqual(result['remembered_context']['preferences'][0]['detail'],'Robotics')
        self.assertEqual([x['title'] for x in result['unfinished_work']],['Finish report'])
        self.assertEqual(result['timezone'],'Asia/Dhaka')
        self.assertIn('never invent',instruction(result))
        self.assertIn('Do not run or resume any task',instruction(result))

    def test_empty_memory_does_not_invent_interests_or_tasks(self):
        with patch('core.life_store.records', return_value=[]):
            result=context({})
        self.assertEqual(result['remembered_context'],{})
        self.assertEqual(result['unfinished_work'],[])

    def test_task_read_failure_is_not_reported_as_no_tasks(self):
        with patch('core.life_store.records', side_effect=OSError('offline')):
            result=context({})
        self.assertIn('unavailable',result['remembered_context']['task_status'])


class EnglishUITests(unittest.TestCase):
    def test_native_ui_literals_are_english_without_changing_conversation_prompt(self):
        import ast
        for name in ('ui.py','core/qt_settings.py','core/qt_chat_theme.py','core/life_tools_ui.py','core/gmail_setup_ui.py'):
            tree=ast.parse((ROOT/name).read_text(encoding='utf8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str):
                    self.assertFalse(any('\u0980'<=c<='\u09ff' for c in node.value),f'{name}:{node.lineno}')
        from core.nexa_identity import language_instruction
        self.assertIn('Bengali',language_instruction())


class StartupFlowTests(unittest.IsolatedAsyncioTestCase):
    async def check_flow(self, interrupt=False):
        import main
        engine=main.JarvisLive.__new__(main.JarvisLive)
        engine.ui=Mock()
        engine._turn_done_event=asyncio.Event()
        engine._startup_brief_done=asyncio.Event()
        engine._user_started_chat=False
        engine.session=Mock()
        async def send(**kwargs):
            engine._turn_done_event.set()
            if interrupt:
                engine._user_started_chat=True
        engine.session.send_client_content=AsyncMock(side_effect=send)
        fixture={'local_time':'Tuesday, 27 October 2026, 22:00','timezone':'Asia/Dhaka',
                 'remembered_context':{'projects':[{'topic':'sample','detail':'Robotics project'}]},
                 'unfinished_work':[{'title':'Sample unfinished report','status':'open'}]}
        with patch.object(main,'load_memory',return_value={}), \
             patch.object(main,'pop_last_session',return_value=None), \
             patch.object(main,'_fetch_news_sync',return_value='1. Synthetic news headline — example source'), \
             patch('core.startup_briefing.context',return_value=fixture), \
             patch.object(main.asyncio,'sleep',new=AsyncMock()):
            await engine._send_startup_briefing()
        return engine

    async def test_greeting_includes_factual_context_then_news(self):
        engine=await self.check_flow()
        self.assertEqual(engine.session.send_client_content.await_count,2)
        greeting=engine.session.send_client_content.call_args_list[0].kwargs['turns']['parts'][0]['text']
        self.assertIn('Asia/Dhaka',greeting)
        self.assertIn('Robotics project',greeting)
        self.assertIn('Sample unfinished report',greeting)
        self.assertIn('Bengali',greeting)
        self.assertTrue(engine._startup_brief_done.is_set())

    async def test_user_conversation_suppresses_late_news_turn(self):
        engine=await self.check_flow(interrupt=True)
        self.assertEqual(engine.session.send_client_content.await_count,1)
        self.assertTrue(engine._startup_brief_done.is_set())


if __name__=='__main__':
    unittest.main()

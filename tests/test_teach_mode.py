import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import teach_mode as teach, life_store as store


class TeachTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.db=patch.object(store,'DB',self.root/'life.sqlite3');self.db.start()
        self.data=patch.object(store,'DATA',self.root/'data');self.data.start()
        teach._recording_id=None;teach._stop.clear();teach.bind_ui(None)

    def tearDown(self):
        teach._recording_id=None;teach._stop.clear();teach.bind_ui(None)
        self.db.stop();self.data.stop();self.temp.cleanup()

    def recipe(self):
        item=teach.start('Synthetic routine')
        teach.observe('nexa_life',{'operation':'archive_search','query':'project'},'[]')
        teach.observe('file_controller',{'action':'list','path':str(self.root)},'File list')
        teach.finish()
        return teach.preview(item['id'])

    def test_nothing_is_captured_unless_user_starts_teaching(self):
        self.assertIsNone(teach.observe('nexa_gmail',{'body':'private'},'sent'))
        self.assertEqual(teach.workflows(),[])

    def test_record_finish_and_load_saved_arguments(self):
        snapshot=self.recipe();teach._recording_id=None
        self.assertEqual(teach.preview(snapshot['id'])['steps'],snapshot['steps'])
        self.assertEqual(len(snapshot['steps']),2)
        self.assertFalse(teach.status()['recording'])

    def test_unsupported_action_never_retains_private_arguments(self):
        item=teach.start('Sample')
        teach.observe('nexa_gmail',{'operation':'send','body':'PRIVATE MAIL BODY'},'pending')
        text=json.dumps(store.get(item['id']))
        self.assertNotIn('PRIVATE MAIL BODY',text)
        self.assertEqual(len(store.get(item['id'])['payload']['skipped']),1)

    def test_failed_action_and_credentials_are_not_saved(self):
        item=teach.start('Sample')
        teach.observe('open_app',{'app_name':'missing'},'status=failed')
        teach.observe('file_controller',{'action':'read','path':'config/api_keys.json'},'text')
        self.assertEqual(store.get(item['id'])['payload']['steps'],[])

    def test_plain_text_file_failure_is_not_recorded_as_success(self):
        item=teach.start('Missing file sample')
        teach.observe('file_controller',{'action':'read','path':'C:/Demo/missing.txt'},'File or folder not found. Nothing opened.')
        self.assertEqual(store.get(item['id'])['payload']['steps'],[])

    def test_injection_and_mutating_file_actions_are_rejected(self):
        for tool,args in [('open_app',{'app_name':'notepad & powershell'}),('file_controller',{'action':'delete','path':'x'}),
                          ('nexa_life',{'operation':'calendar_create'}),('nexa_life',{'operation':'translate','password':'x'}),
                          ('file_controller',{'action':'read','path':'C:/sample/.env'})]:
            with self.assertRaises(ValueError):teach.validate(tool,args)

    def test_changed_plan_cannot_use_previous_review(self):
        snapshot=self.recipe()
        teach.edit_step(snapshot['id'],0,{'operation':'archive_search','query':'changed'})
        with patch.object(teach,'_perform') as perform:
            with self.assertRaisesRegex(ValueError,'changed after review'):teach.run_reviewed(snapshot)
            perform.assert_not_called()

    def test_replay_stops_on_failure_and_does_not_retry(self):
        snapshot=self.recipe()
        with patch.object(teach,'_perform',side_effect=ValueError('synthetic failure')) as perform:
            result=teach.run_reviewed(snapshot)
        self.assertEqual(result['status'],'failed');self.assertEqual(perform.call_count,1)

    def test_stop_prevents_subsequent_steps(self):
        snapshot=self.recipe()
        def first(step):teach.request_stop();return {'done':True}
        with patch.object(teach,'_perform',side_effect=first) as perform:result=teach.run_reviewed(snapshot)
        self.assertEqual(result['status'],'stopped');self.assertEqual(perform.call_count,1)

    def test_real_excel_and_backup_replay_on_synthetic_files(self):
        from openpyxl import Workbook
        from core.safe_backup import inspect
        source=self.root/'book.xlsx';book=Workbook();book.active['A1']='Teaching sample';book.save(source);book.close()
        item=teach.start('Read and back up sample')
        teach.observe('nexa_life',{'operation':'excel_read','path':str(source),'cell_range':'A1:B2'},'completed')
        teach.observe('nexa_life',{'operation':'backup','path':str(source),'destination':str(self.root/'backups')},'completed')
        teach.finish();result=teach.run_reviewed(teach.preview(item['id']))
        self.assertEqual(result['status'],'done')
        self.assertEqual(result['payload']['results'][0]['result']['cells'][0]['value'],'Teaching sample')
        archive=result['payload']['results'][1]['result']['archive']
        self.assertEqual(len(inspect(archive)['files']),1)

    def test_plugin_replay_requires_physical_review(self):
        from plugins import nexa_teach
        snapshot=self.recipe()
        with patch('core.confirm.request',return_value='pending') as gate,patch.object(teach,'run_reviewed') as runner:
            self.assertEqual(nexa_teach.run({'operation':'run','id':snapshot['id']}),'pending')
            runner.assert_not_called()
            self.assertIn(str(self.root),gate.call_args.args[2])

    def test_sidebar_recording_indicator_resets_after_save(self):
        notify=Mock();teach.bind_ui(notify);self.recipe()
        self.assertTrue(any('REC:' in x.args[0] for x in notify.call_args_list))
        self.assertEqual(notify.call_args.args[0],'Teach mode')

    def test_downloads_open_is_saved_as_folder_action(self):
        self.assertEqual(teach.validate('open_app',{'app_name':'Downloads'}),{'tool':'file_controller','args':{'action':'open','path':'Downloads'}})

    def test_restart_preserves_but_does_not_resume_interrupted_sessions(self):
        item=teach.start('Interrupted sample')
        teach.observe('file_controller',{'action':'list','path':str(self.root)},'File list')
        teach._recording_id=None
        run=store.add('taught_run','Interrupted run',{'workflow_id':item['id']},'running')
        with patch.object(teach,'_perform') as perform:
            teach.recover_interrupted();perform.assert_not_called()
        self.assertEqual(store.get(item['id'])['status'],'interrupted')
        self.assertEqual(store.get(run['id'])['status'],'interrupted')
        self.assertEqual(teach.finish(item['id'])['status'],'ready')

    def test_too_large_plan_cannot_be_hidden_in_confirmation(self):
        item=teach.start('Long text sample')
        teach.observe('nexa_life',{'operation':'translate','text':'x'*15900,'source':'en','target':'bn'},'text')
        teach.observe('nexa_life',{'operation':'translate','text':'y'*1000,'source':'en','target':'bn'},'text')
        record=store.get(item['id'])
        self.assertLessEqual(len(record['payload']['steps']),1)
        self.assertTrue(record['payload']['skipped'])


class EngineTeachTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_engine_tool_execution_is_observed(self):
        import main
        from google.genai import types
        with tempfile.TemporaryDirectory() as temp,patch.object(store,'DB',Path(temp)/'teach.sqlite3'):
            teach._recording_id=None;teach.bind_ui(None)
            item=teach.start('Engine hook sample')
            engine=main.JarvisLive.__new__(main.JarvisLive);engine.ui=Mock();engine.speak=Mock()
            engine._action_registry=Mock();engine._action_registry.has.return_value=True
            engine._action_registry.run.return_value='Synthetic folder listing'
            engine._action_registry.scheduling.return_value=None
            engine._plugin_registry=Mock();engine._plugin_registry.scheduling.return_value=None
            response=await engine._execute_tool(types.FunctionCall(id='sample',name='file_controller',args={'action':'list','path':temp}))
            self.assertIn('Synthetic',response.response['result'])
            self.assertEqual(teach.finish()['payload']['steps'][0]['tool'],'file_controller')
            teach._recording_id=None


if __name__=='__main__':unittest.main()

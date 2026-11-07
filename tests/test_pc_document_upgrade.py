import tempfile,unittest
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from unittest.mock import patch,Mock
from actions import file_controller as fc,file_processor as fp
class Checks(unittest.TestCase):
 def test_text_read_no_side_effect(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'qa.txt';p.write_text('Budget 1200. Deadline October 30. Code QA731.',encoding='utf-8')
   r=fp.file_processor({'file_path':str(p),'action':'extract_text','save':False})
   self.assertIn('QA731',r);self.assertEqual(len(list(Path(d).iterdir())),1)
 def test_docx_read(self):
  from docx import Document
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'qa.docx';doc=Document();doc.add_paragraph('Document code DOC731');doc.save(p)
   r=fp.file_processor({'file_path':str(p),'action':'extract_text'})
   self.assertIn('DOC731',r);self.assertEqual(len(list(Path(d).iterdir())),1)
 def test_bengali_summary_prompt_and_no_export(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'qa.txt';p.write_text('Budget 1200',encoding='utf-8');model=Mock();model.generate_content.return_value.text='বাংলা '*200
   with patch.object(fp,'_gemini_client',return_value=model):
    r=fp.file_processor({'file_path':str(p),'action':'summarize','instruction':'keep the budget'})
   self.assertIn('Answer in Bengali',model.generate_content.call_args.args[0]);self.assertIn('keep the budget',model.generate_content.call_args.args[0]);self.assertEqual(len(list(Path(d).iterdir())),1)
 def test_folder_open_and_alias(self):
  with tempfile.TemporaryDirectory() as d,patch.object(fc,'_get_downloads',return_value=Path(d)),patch.object(fc.os,'startfile') as launch:
   r=fc.file_controller({'action':'open','path':'ডাউনলোড'})
   launch.assert_called_once_with(str(Path(d).resolve()));self.assertIn('not verified',r)
 def test_missing_folder_not_opened(self):
  with patch.object(fc.os,'startfile') as launch:
   r=fc.file_controller({'action':'open','path':'Z:/nexa-nonexistent-qa731'})
   launch.assert_not_called();self.assertIn('not found',r)
 def test_search_source_preserved(self):
  from actions import web_search as ws
  with patch.object(ws,'_search',return_value='Source: https://www.python.org/doc/'):
   self.assertIn('https://www.python.org/doc/',ws.web_search({'query':'python docs'}))
if __name__ == "__main__":
 unittest.main()

"""No real desktop input, private capture, notifications or outbound messages."""
import json
from pathlib import Path
import tempfile
import time
import threading
import unittest
from unittest.mock import patch, Mock
import numpy as np
from PIL import Image
from core.plugin_loader import discover_plugins
from core import confirm
from plugins import youtube_control as yt, screen_recorder as rec
from plugins import screenshot_annotate as shot, notification_reader as notices
from plugins import discord_messenger as discord, magi_system as magi


class CommunityTests(unittest.TestCase):
    def test_all_plugins_load_without_new_threads(self):
        before = {t.ident for t in threading.enumerate()}
        registry = discover_plugins(Path('plugins'),set(),logger=lambda _:None)
        records = registry.list_for_ui()
        names = {r['name'] for r in records if r['valid']}
        self.assertTrue({'youtube_controller','screen_recorder','screenshot_annotate','notification_reader','discord_messenger','magi_system'} <= names)
        self.assertEqual(before,{t.ident for t in threading.enumerate()})

    def test_youtube_shortcut_does_not_touch_desktop(self):
        import pyautogui
        with patch.object(yt,'_find_youtube_window',return_value=(Mock(),None)), patch.object(yt,'_focus_window',return_value=None), patch.object(pyautogui,'press') as press:
            result=yt.run({'action':'captions'})
        press.assert_called_once_with('c');self.assertIn('captions',result)

    def test_video_file_created_from_synthetic_frames(self):
        import mss,cv2
        class Screen:
            monitors=[{'width':160,'height':120}]*2
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def grab(self,monitor):return np.zeros((120,160,4),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as folder, patch.object(mss,'mss',Screen), patch.object(rec,'_output_dir',return_value=Path(folder)), patch.object(rec,'_open_file',return_value=False):
            rec.run({'action':'start','filename':'synthetic-qa'})
            try:
                time.sleep(.4)
                self.assertIn('paused',rec.run({'action':'pause'}).lower())
                rec.run({'action':'resume'});time.sleep(.2)
            finally:rec.run({'action':'stop'})
            files=list(Path(folder).glob('*.mp4'));self.assertEqual(len(files),1)
            video=cv2.VideoCapture(str(files[0]));ok,frame=video.read();video.release()
            self.assertTrue(ok);self.assertEqual(frame.shape[:2],(120,160))

    def test_annotation_pixels_on_synthetic_image(self):
        original=Image.new('RGB',(400,300),'white')
        result=shot._draw_annotations(original,[{'_px_box':(100,100,220,180),'instruction':'QA'}])
        image=result[0] if isinstance(result,tuple) else result
        self.assertNotEqual(image.tobytes(),original.tobytes())

    def test_notifications_mocked_and_wrapped(self):
        async def fake():return [{'id':731,'app':'QA','title':'Hello','body':'Synthetic notification'}],'ALLOWED'
        with patch.object(notices,'_ensure_winsdk',return_value=True),patch.object(notices,'_get_notifications',fake):
            result=notices.run({'action':'list'})
        self.assertIn('UNTRUSTED',result);self.assertIn('Synthetic notification',result)

    def test_discord_prepares_but_does_not_send_without_approval(self):
        import pyautogui
        spec={'contact':'QA recipient','segments':[{'text':'Synthetic test'}]}
        confirm.bind(lambda *a:None,lambda:None)
        self.addCleanup(lambda:confirm.bind(None,None))
        with patch.object(discord,'_get_gemini_key',return_value='test'),patch.object(discord,'_load_pending',return_value=None),patch.object(discord,'_parse_request',return_value=spec),patch.object(discord,'_flatten_segments',return_value='Synthetic test'),patch.object(discord,'_navigate_discord_destination',return_value=(True,None,'QA recipient')),patch.object(discord,'_type_segments'),patch.object(discord,'_verify_before_send',return_value={'ok':True}),patch.object(discord.time,'sleep'),patch.object(pyautogui,'press') as press:
            result=discord.run({'action':'send','request':'message QA recipient Synthetic test'})
            self.assertIn('CONFIRMATION_PENDING',result)
            self.assertNotIn(unittest.mock.call('enter'),press.call_args_list)
            confirm.resolve(False)

    def test_magi_quick_with_mocked_model_and_isolated_state(self):
        from core.community_plugin_client import Client
        from core import gemini
        with tempfile.TemporaryDirectory() as folder, patch.object(magi,'STATE_PATH',Path(folder)/'state.json'),patch.object(magi,'_get_gemini_key',return_value='test'),patch.object(gemini,'call',return_value=Mock(text=json.dumps({'verdict':'APPROVE','reasoning':'Synthetic reasoning'}))) as call:
            magi.run({'action':'activate'})
            result=magi.run({'action':'ask','question':'Synthetic QA decision','mode':'quick'})
            self.assertGreaterEqual(call.call_count,3)
            self.assertIn('APPROVE',result)


if __name__=='__main__':unittest.main()

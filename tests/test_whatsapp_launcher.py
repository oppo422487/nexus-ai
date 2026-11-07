import unittest
from unittest.mock import patch, Mock
from core import windows_whatsapp as wa, appidentity
from actions import open_app as app


class WhatsAppLauncherTests(unittest.TestCase):
    def test_browser_whatsapp_titles_are_not_desktop_matches(self):
        entries=[appidentity.Match(1,'msedge.exe',110,False,['WhatsApp - Search']),
                 appidentity.Match(2,'WhatsApp.Root.exe',100,False,['WhatsApp']),
                 appidentity.Match(3,'msedgewebview2.exe',100,False,['WhatsApp'])]
        with patch.object(appidentity,'running',return_value=entries):
            self.assertEqual([x.pid for x in wa.matches()],[2])

    def test_running_foreground_app_does_not_launch_again(self):
        with patch.object(wa,'matches',return_value=[Mock(pid=2)]), patch.object(wa,'foreground_pid',return_value=2), patch.object(wa,'request_launch') as launch:
            self.assertTrue(wa.open_desktop()['verified']); launch.assert_not_called()

    def test_store_launch_uses_exact_app_id_without_search(self):
        app_id='5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App'
        with patch.object(wa,'installed_id',return_value=app_id),patch.object(wa.subprocess,'Popen') as launch:
            self.assertTrue(wa.request_launch())
            self.assertEqual(launch.call_args.args[0][1],'shell:AppsFolder\\'+app_id)

    def test_open_action_bypasses_windows_search(self):
        with patch.object(app,'_SYSTEM','Windows'),patch.object(wa,'open_desktop',return_value={'opened':True,'verified':True}),patch.object(app,'_desktop_search') as search:
            result=app.open_app({'app_name':'WhatsApp'})
            self.assertIn('verified',result);search.assert_not_called()

    def test_failed_activation_does_not_fall_back_to_bing(self):
        with patch.object(app,'_SYSTEM','Windows'),patch.object(wa,'open_desktop',return_value={'opened':False,'reason':'not installed'}),patch.object(app,'_desktop_search') as search:
            self.assertIn('not installed',app.open_app({'app_name':'WhatsApp'})); search.assert_not_called()

    def test_activation_can_reuse_existing_tray_process(self):
        with patch.object(wa,'focus_existing',side_effect=[False,True]),patch.object(wa,'request_launch',return_value=True):
            self.assertTrue(wa.open_desktop()['opened'])

    def test_messaging_launcher_uses_same_verified_path_without_typing(self):
        from actions import send_message as messaging
        with patch.object(messaging,'_require_pyautogui'),patch.object(messaging,'_get_os',return_value='windows'),patch.object(wa,'open_desktop',return_value={'verified':True}),patch.object(messaging,'_paste_text') as paste:
            self.assertTrue(messaging._open_app('WhatsApp'))
            paste.assert_not_called()

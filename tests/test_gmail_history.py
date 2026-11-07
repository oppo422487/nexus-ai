import base64
from email import policy
from email.parser import BytesParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from core import gmail_service as g, conversation_archive as archive, confirm
from plugins import nexa_gmail as plugin


class GmailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = patch.object(g, 'DB', Path(self.temp.name)/'gmail.sqlite3')
        self.db.start(); self.addCleanup(self.db.stop)

    def test_contact_persistence_and_unknown(self):
        g.save_contact('teacher', 'teacher@example.com')
        self.assertEqual(g.resolve('TEACHER'), 'teacher@example.com')
        with self.assertRaises(ValueError): g.resolve('boss')

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError): g.address('a@example.com\r\nBcc:b@example.com')

    def test_send_is_not_called_until_physical_confirmation(self):
        confirm.bind(lambda *args:None, lambda:None)
        self.addCleanup(lambda:confirm.bind(None,None))
        with patch.object(g,'send',return_value={'sent':True}) as send:
            result=plugin.run({'operation':'send','recipient':'teacher@example.com','subject':'Leave','body':'I am ill.'})
            self.assertIn('CONFIRMATION_PENDING',result)
            send.assert_not_called()
            confirm.resolve(False)
            send.assert_not_called()

    def test_approved_payload_is_frozen(self):
        confirm.bind(lambda *args:None, lambda:None)
        self.addCleanup(lambda:confirm.bind(None,None))
        p={'operation':'send','recipient':'teacher@example.com','subject':'Leave','body':'Reviewed body'}
        with patch.object(g,'send',return_value={'sent':True}) as send:
            plugin.run(p);p['body']='Changed';confirm.resolve(True)
            send.assert_called_once_with('teacher@example.com','Leave','Reviewed body',None)

    def test_mime_reply_thread(self):
        api=Mock();api.users.return_value.messages.return_value.send.return_value.execute.return_value={'id':'sent1'}
        with patch.object(g,'service',return_value=api):
            result=g.send('teacher@example.com','Re: Class','বাংলা reply',{'threadId':'t1','message_id':'<m1@example.com>'})
        payload=api.users.return_value.messages.return_value.send.call_args.kwargs['body']
        msg=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(payload['raw']))
        self.assertEqual(msg['To'],'teacher@example.com');self.assertEqual(payload['threadId'],'t1')
        self.assertEqual(msg['In-Reply-To'],'<m1@example.com>');self.assertTrue(result['sent'])

    def test_history_survives_new_connection(self):
        with patch.object(archive,'PATH',Path(self.temp.name)/'archive.sqlite3'):
            archive.record('You: Remember project QA731')
            archive.record('SYS: not a conversation')
            self.assertEqual(len(archive.recall('QA731')),1)
            archive.clear();self.assertEqual(archive.recall(),[])

    def test_read_only_inbox(self):
        api=Mock();messages=api.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value={'messages':[{'id':'m1'}]}
        messages.get.return_value.execute.return_value={'id':'m1','snippet':'Hello','payload':{'headers':[{'name':'Subject','value':'QA'}]}}
        with patch.object(g,'service',return_value=api): result=g.inbox()
        self.assertEqual(result[0]['subject'],'QA');messages.modify.assert_not_called()

    def test_read_accepts_query_without_message_id(self):
        with patch.object(g,'inbox',return_value=[{'id':'m1'}]) as search, patch.object(g,'read',return_value={'id':'m1','body':'reply text'}) as read:
            result=plugin.run({'operation':'read','query':'from:teacher@example.com'})
        search.assert_called_once_with('from:teacher@example.com',limit=5)
        read.assert_called_once_with('m1')
        self.assertIn('reply text',result)

    def test_empty_search_is_not_connection_error(self):
        with patch.object(g,'inbox',return_value=[]):
            result=plugin.run({'operation':'read','query':'from:teacher@example.com'})
        self.assertIn('no mail found',result)
        self.assertNotIn('did not complete',result)

    def test_read_missing_arguments_gives_guidance(self):
        with patch.object(g,'read') as read:
            result=plugin.run({'operation':'read'})
        read.assert_not_called();self.assertIn('provide message_id',result)

    def test_success_after_confirmation_reaches_chat_and_live_model(self):
        player=Mock()
        with patch.object(g,'send',return_value={'sent':True,'id':'synthetic-receipt'}):
            plugin._send_reviewed(player,'teacher@example.com','Sample','Synthetic body',None)
        self.assertIn('Email sent successfully',player.write_log.call_args.args[0])
        self.assertIn('Do not ask for confirmation again',player.request_say.call_args.args[0])

    def test_uncertain_send_is_reported_without_retry(self):
        player=Mock()
        with patch.object(g,'send',side_effect=TimeoutError()) as send:
            result=plugin._send_reviewed(player,'teacher@example.com','Sample','Synthetic body',None)
        self.assertIn('unknown',result);send.assert_called_once()
        self.assertIn('uncertain',player.write_log.call_args.args[0])

    def test_notification_failure_cannot_turn_sent_mail_into_send_error(self):
        player=Mock();player.write_log.side_effect=RuntimeError();player.request_say.side_effect=RuntimeError()
        with patch.object(g,'send',return_value={'sent':True,'id':'synthetic-receipt'}) as send:
            result=plugin._send_reviewed(player,'teacher@example.com','Sample','Synthetic body',None)
        self.assertIn('"sent": true',result);send.assert_called_once()

    def test_missing_gmail_receipt_is_not_claimed_as_success(self):
        api=Mock();api.users.return_value.messages.return_value.send.return_value.execute.return_value={}
        with patch.object(g,'service',return_value=api):
            with self.assertRaisesRegex(ValueError,'Check Sent'):
                g.send('teacher@example.com','Sample','Synthetic body')


if __name__=='__main__': unittest.main()

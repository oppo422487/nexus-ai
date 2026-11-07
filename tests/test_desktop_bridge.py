"""Native-to-original-UI bridge regression tests without live APIs or actions."""
from pathlib import Path
import json
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.desktop_bridge import DesktopBridge
from core import confirm


def fake_ui():
    return SimpleNamespace(assistant_name="Nexa AI", muted=False,
        _win=SimpleNamespace(_ready=True, hud=SimpleNamespace(_amp_disp=.4)),
        write_log=Mock(), set_state=Mock(), show_content=Mock(), show_review=Mock(),
        show_confirm=Mock(), hide_confirm=Mock(), show_camera_frame=Mock())


class DesktopBridgeTests(unittest.TestCase):
    def setUp(self):
        self.ui = fake_ui()
        self.bridge = DesktopBridge(self.ui, token="private-test-token")
        self.bridge.on_qt = lambda callback: callback()

    def tearDown(self):
        confirm.resolve(False)
        confirm.bind(None, None)

    def test_transcripts_and_tool_context_keep_sequence(self):
        self.ui.write_log("You: আমার নাম কী?")
        self.ui.write_log("Nexa AI: আপনার নাম জানা নেই।")
        self.ui.show_content("Search", "A source-backed result")
        events = self.bridge.snapshot()["events"]
        self.assertEqual([e["kind"] for e in events], ["user", "assistant", "context"])
        self.assertEqual(len(self.bridge.snapshot(after=2)["events"]), 1)
        self.ui.set_state("SPEAKING")
        self.assertEqual(self.bridge.snapshot()["state"], "SPEAKING")

    def test_replaced_confirmation_cannot_authorize_new_action(self):
        completed = threading.Event()
        confirm.bind(self.ui.show_confirm, self.ui.hide_confirm)
        confirm.request("first", "First", "A", lambda: "first")
        old_id = self.bridge.pending["id"]
        confirm.request("second", "Second", "B", lambda: completed.set() or "second")
        with self.assertRaises(ValueError):
            self.bridge.command({"action": "confirm", "id": old_id, "accepted": True})
        self.assertFalse(completed.is_set())
        new_id = self.bridge.pending["id"]
        self.bridge.command({"action": "confirm", "id": new_id, "accepted": True})
        self.assertTrue(completed.wait(2))
        self.assertIsNone(self.bridge.pending)
        with self.assertRaises(ValueError):
            self.bridge.command({"action": "confirm", "id": new_id, "accepted": True})

    def test_text_goes_to_existing_engine(self):
        engine = SimpleNamespace(session=object(), _loop=object(), _is_speaking=False,
                                 _awake=True, wake=Mock(), _on_text_command=Mock())
        self.bridge.engine = engine
        self.bridge.command({"action": "text", "text": "গুগল খোলো"})
        engine._on_text_command.assert_called_once_with("গুগল খোলো")
        self.assertEqual(self.bridge.snapshot()["events"][-1]["kind"], "user")

    def test_disconnected_engine_does_not_silently_drop_text(self):
        self.bridge.engine = SimpleNamespace(session=None, _loop=None)
        with self.assertRaises(ValueError):
            self.bridge.command({"action": "text", "text": "Hello"})

    def test_http_requires_private_token(self):
        self.bridge.serve(port=0)
        base = "http://127.0.0.1:" + str(self.bridge.server.server_address[1])
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/state", timeout=2)
            self.assertEqual(error.exception.code, 403)
            request = Request(base + "/state", headers={"X-Nexa-Bridge": "private-test-token"})
            with urlopen(request, timeout=2) as response:
                self.assertEqual(json.load(response)["mode"], "native")
        finally:
            self.bridge.server.shutdown()
            self.bridge.server.server_close()

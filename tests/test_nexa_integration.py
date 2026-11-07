"""Regression checks for the optional integration, no paid services required."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.nexa_identity import language_instruction
from core import confirm, nexa_suite
from memory.config_manager import get_assistant_name

spec = importlib.util.spec_from_file_location("nexa_plugin_test", ROOT / "plugins/nexa_productivity.py")
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class IntegrationTests(unittest.TestCase):
    def tearDown(self):
        confirm.bind(None, None)
        confirm.resolve(False)

    def test_fresh_identity(self):
        with patch("memory.config_manager.load_api_keys", return_value={}):
            self.assertEqual(get_assistant_name(), "Nexa AI")
        self.assertIn("Bengali", language_instruction())

    def test_reads_do_not_write(self):
        with patch.object(nexa_suite, "read", return_value={"status": "ok"}) as read, patch.object(nexa_suite, "write") as write:
            result = plugin.run({"operation": "dashboard"})
            self.assertEqual(json.loads(result)["status"], "ok")
            read.assert_called_once_with("dashboard")
            write.assert_not_called()

    def test_model_cannot_self_confirm(self):
        displayed = []
        confirm.bind(lambda title, detail: displayed.append(detail), lambda: None)
        with patch.object(nexa_suite, "write") as write:
            result = plugin.run({"operation": "email", "recipient": "a@example.com", "title": "Hello", "text": "Body", "user_confirmed": True})
            self.assertIn("CONFIRMATION_PENDING", result)
            self.assertIn("a@example.com", displayed[0])
            write.assert_not_called()
            confirm.resolve(False)
            write.assert_not_called()

    def test_missing_ui_refuses_write(self):
        confirm.bind(None, None)
        with patch.object(nexa_suite, "write") as write:
            self.assertIn("not available", plugin.run({"operation": "note", "text": "test"}))
            write.assert_not_called()

    def test_human_confirmation_executes_reviewed_payload_once(self):
        completed = threading.Event()
        received = []
        confirm.bind(lambda title, detail: None, lambda: None)
        def write(operation, payload):
            received.append((operation, payload))
            completed.set()
            return {"status": "completed"}
        with patch.object(nexa_suite, "write", side_effect=write):
            arguments = {"operation": "note", "text": "আমার নোট"}
            plugin.run(arguments)
            arguments["text"] = "changed after review"
            confirm.resolve(True)
            self.assertTrue(completed.wait(timeout=2))
            confirm.resolve(True)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][1]["text"], "আমার নোট")

    def test_unknown_operation_does_not_start_backend(self):
        with patch.object(nexa_suite, "ensure_started") as start:
            with self.assertRaises(KeyError):
                nexa_suite.read("http://example.com")
            start.assert_not_called()

    def test_dashboard_crypto_salt_unchanged(self):
        self.assertIn("JARVIS-DASHBOARD-v1", (ROOT / "dashboard/static/app.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

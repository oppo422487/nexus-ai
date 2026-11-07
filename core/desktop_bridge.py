"""Private loopback bridge from the native engine to the original Nexa UI."""
from __future__ import annotations

from collections import deque
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import threading
import time
import uuid

from PyQt6.QtCore import QObject, pyqtSignal


class Dispatcher(QObject):
    invoke = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.invoke.connect(lambda callback: callback())


class DesktopBridge:
    def __init__(self, ui, token=None):
        self.ui = ui
        self.engine = None
        self.token = token or os.environ.get("NEXA_ENGINE_BRIDGE_TOKEN") or secrets.token_urlsafe(32)
        self.dispatcher = Dispatcher()
        self.events = deque(maxlen=800)
        self.lock = threading.RLock()
        self.sequence = 0
        self.generation = uuid.uuid4().hex
        self.pending = None
        self.state = "INITIALISING"
        self.camera_frame = None
        self._instrument()

    def publish(self, kind, text="", **extra):
        with self.lock:
            self.sequence += 1
            self.events.append({"id": self.sequence, "kind": kind,
                                "text": str(text)[:20000], "at": time.time(), **extra})

    def _instrument(self):
        original_log = self.ui.write_log
        def write_log(text):
            text = str(text)
            prefix, separator, body = text.partition(":")
            if prefix.lower() in {"you", "user"}:
                kind = "user"
            elif prefix.lower() in {"nexa ai", "nexa", "jarvis", self.ui.assistant_name.lower()}:
                kind = "assistant"
            else:
                kind = "context"
            self.publish(kind, body.strip() if separator else text,
                         label=prefix if kind == "context" else "")
            original_log(text)
        self.ui.write_log = write_log
        original_state = self.ui.set_state
        def set_state(state):
            self.state = str(state)
            original_state(state)
        self.ui.set_state = set_state
        original_content = self.ui.show_content
        def show_content(title, text):
            self.publish("context", text, label=str(title))
            original_content(title, text)
        self.ui.show_content = show_content
        original_review = self.ui.show_review
        def show_review(title, summary, findings, unclear=None):
            self.publish("context", json.dumps({"summary": summary, "findings": findings,
                                                "unclear": unclear}, ensure_ascii=False, default=str), label=str(title))
            original_review(title, summary, findings, unclear)
        self.ui.show_review = show_review
        self.ui.show_confirm = self.show_confirm
        self.ui.hide_confirm = self.hide_confirm
        original_frame = self.ui.show_camera_frame
        def camera_frame(data):
            self.camera_frame = bytes(data)
            original_frame(data)
        self.ui.show_camera_frame = camera_frame
        original_stop_camera = getattr(self.ui, "stop_camera_stream", None)
        if original_stop_camera:
            def stop_camera():
                self.camera_frame = None
                original_stop_camera()
            self.ui.stop_camera_stream = stop_camera
        original_quiz = getattr(self.ui, "show_quiz", None)
        if original_quiz:
            def show_quiz(topic, questions, grade=None):
                self.publish("context", "কুইজ শুরু হয়েছে। নিচের chat থেকে উত্তর দিন।", label=str(topic))
                original_quiz(topic, questions, grade)
            self.ui.show_quiz = show_quiz

    def show_confirm(self, title, detail):
        with self.lock:
            self.pending = {"id": uuid.uuid4().hex, "title": str(title),
                            "detail": str(detail), "expires_at": time.time() + 90}
            self.publish("confirmation", detail, confirmation=dict(self.pending))

    def hide_confirm(self):
        with self.lock:
            self.pending = None
            self.publish("confirmation_closed")

    def snapshot(self, after=0):
        with self.lock:
            pending = self.pending
            if pending and pending["expires_at"] < time.time():
                pending = None
            engine = self.engine
            quiz = getattr(self.ui._win, "_quiz", None)
            quiz_view = None
            if quiz and quiz.get("questions"):
                question = quiz["questions"][quiz["i"]]
                result = (quiz.get("results") or [{}])[-1] if quiz.get("answered") else {}
                quiz_view = {"topic": quiz["topic"], "index": quiz["i"],
                    "total": len(quiz["questions"]), "question": question.get("question", ""),
                    "options": question.get("options") or [], "answered": quiz["answered"],
                    "feedback": ("সঠিক উত্তর।" if result.get("correct") is True else
                                 "উত্তর নথিভুক্ত হয়েছে।" if result.get("correct") is None else
                                 "সঠিক উত্তর: " + str(result.get("answer", ""))) if result else ""}
            return {
                "mode": "native", "generation": self.generation, "cursor": self.sequence,
                "events": [event for event in self.events if event["id"] > after],
                "connected": bool(engine and engine.session),
                "configured": bool(self.ui._win._ready), "state": self.state,
                "speaking": bool(engine and engine._is_speaking),
                "level": min(1.0, max(0.0, float(self.ui._win.hud._amp_disp))),
                "muted": bool(self.ui.muted),
                "awake": bool(engine and engine._awake),
                "confirmation": pending,
                "camera": self.camera_frame is not None, "quiz": quiz_view,
            }

    def on_qt(self, callback):
        done = threading.Event()
        result = []
        def execute():
            try:
                result.append((True, callback()))
            except Exception as exc:
                result.append((False, str(exc)))
            finally:
                done.set()
        self.dispatcher.invoke.emit(execute)
        if not done.wait(5):
            raise RuntimeError("The desktop engine did not respond.")
        if not result[0][0]:
            raise RuntimeError(result[0][1])
        return result[0][1]

    def command(self, data):
        action = data.get("action")
        engine = self.engine
        if action == "configure":
            key = str(data.get("key", "")).strip()
            if not 16 <= len(key) <= 300:
                raise ValueError("একটি সঠিক Gemini API key দিন।")
            def configure():
                from memory.config_manager import save_api_keys
                save_api_keys(key)
                self.ui._win._ready = True
                overlay = getattr(self.ui._win, "_overlay", None)
                if overlay:
                    overlay.hide()
                if engine:
                    engine.request_reconnect(reason="provider key")
            self.on_qt(configure)
            return {"accepted": True, "message": "ইঞ্জিনের key সংরক্ষিত হয়েছে।"}
        if action == "shutdown":
            self.dispatcher.invoke.emit(self.ui._app.quit)
            return {"accepted": True}
        if action in {"quiz_answer", "quiz_next", "quiz_close"}:
            def quiz_action():
                quiz = getattr(self.ui._win, "_quiz", None)
                if quiz is None:
                    raise ValueError("এই কুইজ আর সক্রিয় নেই।")
                if action == "quiz_answer":
                    self.ui._win._quiz_submit(str(data.get("text", ""))[:3000])
                elif action == "quiz_next":
                    if not quiz.get("answered"):
                        raise ValueError("আগে বর্তমান প্রশ্নের উত্তর দিন।")
                    self.ui._win._quiz_next()
                else:
                    self.ui._win._hide_quiz()
            self.on_qt(quiz_action)
            return {"accepted": True}
        if action == "advanced_settings":
            self.on_qt(lambda: (self.ui._win.show(), self.ui._win.raise_(),
                                self.ui._win._toggle_drawer(True)))
            return {"accepted": True}
        if action == "confirm":
            from core import confirm
            with self.lock:
                if not self.pending or data.get("id") != self.pending["id"]:
                    raise ValueError("এই confirmation আর সক্রিয় নেই।")
                if self.pending["expires_at"] < time.time():
                    raise ValueError("Confirmation-এর সময় শেষ হয়েছে।")
                confirm.resolve(data.get("accepted") is True)
            return {"accepted": True}
        if engine is None:
            raise ValueError("Settings থেকে voice engine সেটআপ করুন।")
        if action == "text":
            text = str(data.get("text", "")).strip()
            if not text or len(text) > 20000:
                raise ValueError("কমান্ড খালি বা অতিরিক্ত বড়।")
            if not engine.session or not engine._loop:
                raise ValueError("ইঞ্জিন এখনও সংযোগ করছে। সংযুক্ত হলে আবার পাঠান।")
            def send():
                engine.wake(reason="typed command")
                self.ui.write_log("You: " + text)
                engine._on_text_command(text)
            self.on_qt(send)
        elif action == "mute":
            self.on_qt(lambda: setattr(self.ui, "muted", not self.ui.muted))
        elif action == "interrupt":
            engine.interrupt()
        elif action == "wake":
            engine.wake(reason="Nexa UI")
        elif action == "sleep":
            engine.sleep(reason="Nexa UI")
        elif action == "ptt_down":
            if not engine._ptt_enabled:
                self.on_qt(lambda: engine.set_push_to_talk(True))
            engine._on_ptt(True)
        elif action == "ptt_up":
            engine._on_ptt(False)
        else:
            raise ValueError("Unsupported engine action.")
        return {"accepted": True}

    def serve(self, port=8767):
        bridge = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def authorized(self):
                return hmac.compare_digest(self.headers.get("X-Nexa-Bridge", ""), bridge.token)

            def reply(self, code, value):
                body = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if not self.authorized():
                    return self.reply(403, {"error": "Forbidden"})
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                if parsed.path == "/frame":
                    frame = bridge.camera_frame
                    if frame is None:
                        return self.reply(404, {"error": "Camera is closed"})
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    return
                if parsed.path != "/state":
                    return self.reply(404, {"error": "Not found"})
                try:
                    cursor = max(0, int(parse_qs(parsed.query).get("after", ["0"])[0]))
                    self.reply(200, bridge.snapshot(cursor))
                except ValueError:
                    self.reply(400, {"error": "Invalid cursor"})

            def do_POST(self):
                if not self.authorized():
                    return self.reply(403, {"error": "Forbidden"})
                if self.path != "/command":
                    return self.reply(404, {"error": "Not found"})
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 100000:
                        return self.reply(413, {"error": "Invalid request size"})
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise ValueError("Expected an object")
                    self.reply(200, bridge.command(data))
                except (ValueError, RuntimeError) as exc:
                    self.reply(409, {"error": str(exc)})
        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True,
                         name="nexa-engine-bridge").start()

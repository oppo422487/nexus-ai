"""Isolated browser QA: no live API calls, contacts, or user browser data."""
import json
import os
import re
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        cached_shells = sorted((Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright").glob(
            "chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"))
        browser = playwright.chromium.launch(headless=True,
            **({"executable_path": str(cached_shells[-1])} if cached_shells else {}))
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        context.add_init_script("""localStorage.setItem('nexa-ai-mark-plus:user-profile', JSON.stringify({
          userName:'UI Test',addressingPreference:'Neutral',languageMode:'Bangla',
          voicePreference:'System default',hasCompletedOnboarding:true,
          createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()}));
          localStorage.setItem('nexa.background',JSON.stringify({enabled:false,quality:'low'}));""")
        pending = {"id": "qa-confirmation", "title": "পরীক্ষার নোট", "detail": "এটি শুধু UI পরীক্ষা।", "expires_at": time.time() + 300}
        quiz = None
        calls = []
        old_chat_calls = []
        errors = []
        events = [
            {"id": 1, "kind": "user", "text": "পরীক্ষার প্রশ্ন", "at": time.time()},
            {"id": 2, "kind": "assistant", "text": "পরীক্ষার উত্তর", "at": time.time()},
            {"id": 3, "kind": "context", "text": "পরীক্ষার context", "label": "Context", "at": time.time()},
            {"id": 4, "kind": "tool", "text": "পরীক্ষার tool result", "label": "Tool", "at": time.time()},
        ]

        def event_response(route):
            from urllib.parse import urlparse, parse_qs
            cursor = int(parse_qs(urlparse(route.request.url).query).get("after", [0])[0])
            route.fulfill(json={"generation": "isolated-ui-qa", "cursor": events[-1]["id"],
                "events": [event for event in events if event["id"] > cursor],
                "configured": True, "connected": True, "speaking": False,
                "state": "LISTENING", "level": 0, "muted": False, "awake": True,
                "confirmation": pending, "camera": False, "quiz": quiz})

        def command_response(route):
            nonlocal pending, quiz
            body = route.request.post_data_json
            calls.append(body)
            if body["action"] == "confirm":
                pending = None
            if body["action"] == "quiz_answer" and quiz:
                quiz = {**quiz, "answered": True, "feedback": "সঠিক উত্তর।"}
            route.fulfill(json={"accepted": True})

        context.route("**/api/engine/events*", event_response)
        context.route("**/api/engine/command", command_response)
        context.route("**/api/chat/**", lambda route: (old_chat_calls.append(route.request.url), route.abort()))
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8766/suite/?engine=native", wait_until="domcontentloaded")
        expect(page.locator(".nx-shell")).to_be_visible(timeout=30000)
        expect(page.locator(".nx-sidebar")).to_be_visible()
        for text in ("পরীক্ষার প্রশ্ন", "পরীক্ষার উত্তর", "পরীক্ষার context", "পরীক্ষার tool result"):
            expect(page.get_by_text(text, exact=True)).to_be_visible(timeout=15000)
        expect(page.locator(".nx-native-particles")).to_have_count(1)
        expect(page.get_by_text("Start Always Listening", exact=True)).to_have_count(0)
        page.get_by_role("button", name="নিশ্চিত করুন", exact=True).click()
        expect(page.get_by_role("button", name="নিশ্চিত করুন", exact=True)).to_have_count(0)
        assert any(call["action"] == "confirm" and call["id"] == "qa-confirmation" for call in calls)
        page.locator('.dashboard-chat-card input[placeholder^="Ask Nexa"]').fill("নতুন পরীক্ষার প্রশ্ন")
        page.get_by_title("Send to Nexa", exact=True).click()
        page.wait_for_timeout(500)
        assert any(call["action"] == "text" and call["text"] == "নতুন পরীক্ষার প্রশ্ন" for call in calls)
        assert not old_chat_calls, "Native chat must not execute the old backend chat pipeline as well."
        quiz = {"topic": "পরীক্ষার কুইজ", "index": 0, "total": 1, "question": "কোনটি ভাষা?",
                "options": ["বাংলা", "নীল"], "answered": False, "feedback": ""}
        page.get_by_role("button", name="বাংলা", exact=True).click(timeout=10000)
        expect(page.get_by_text("সঠিক উত্তর।", exact=True)).to_be_visible()
        page.screenshot(path=str(ROOT / "nexa_suite/runtime/phase2-chat-qa.png"))
        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Clear", exact=True).click()
        page.wait_for_timeout(800)
        expect(page.get_by_text("পরীক্ষার উত্তর", exact=True)).to_have_count(0)
        page.get_by_role("button", name=re.compile("^সেটিংস")).click()
        expect(page.get_by_text("নেক্সা Live Engine", exact=True)).to_be_visible()
        page.get_by_role("button", name=re.compile("^ড্যাশবোর্ড")).click()
        page.wait_for_timeout(800)
        expect(page.get_by_text("পরীক্ষার উত্তর", exact=True)).to_have_count(0)
        page.reload(wait_until="domcontentloaded")
        expect(page.locator(".nx-shell")).to_be_visible(timeout=30000)
        page.wait_for_timeout(800)
        expect(page.get_by_text("পরীক্ষার উত্তর", exact=True)).to_have_count(0)
        events.append({"id": 5, "kind": "assistant", "text": "পরীক্ষার নতুন উত্তর", "at": time.time()})
        expect(page.get_by_text("পরীক্ষার নতুন উত্তর", exact=True)).to_be_visible()
        assert not errors, errors
        print("PASS: original shell, native transcript/context/tool bubbles, chat confirmation, native text routing, no duplicate chat pipeline, inline quiz, cleared-history cursor and particle layer.")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()

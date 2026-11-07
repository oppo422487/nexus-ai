"""Explicit live QA of harmless search/document prompts through native chat UI."""
import json
import os
from pathlib import Path
import time
from urllib.request import Request, build_opener, ProxyHandler
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTTP = build_opener(ProxyHandler({}))


def state(after=0):
    with HTTP.open(f"http://127.0.0.1:8766/api/engine/events?after={after}", timeout=10) as response:
        return json.load(response)


def main():
    fixture = ROOT / "nexa_suite/runtime/feature-qa.txt"
    prompts = [
        ("web_search", "QA পরীক্ষা: web_search টুল দিয়ে Python programming language খুঁজে একটি উৎসের লিংকসহ সংক্ষেপে বলো। ব্রাউজার বা অন্য অ্যাপ খুলো না।"),
        ("document_read", f'QA পরীক্ষা: file_processor টুল দিয়ে এই ফাইলটি পড়ো: "{fixture}"। action extract_text ব্যবহার করো। শুধু verification code বলো। ফাইল পরিবর্তন করবে না।'),
        ("document_summary", f'QA পরীক্ষা: file_processor টুল দিয়ে এই ফাইলটির summarize করো: "{fixture}"। বাংলায় বাজেট, শেষ তারিখ ও কয়টি কাজ বাকি বলো। save=false দিও, ফাইল পরিবর্তন করবে না।'),
    ]
    results = []
    with sync_playwright() as p:
        shells = sorted((Path(os.environ["LOCALAPPDATA"]) / "ms-playwright").glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"))
        browser = p.chromium.launch(headless=True, executable_path=str(shells[-1]))
        ctx = browser.new_context(reduced_motion="reduce")
        ctx.add_init_script("""localStorage.setItem('nexa-ai-mark-plus:user-profile',JSON.stringify({userName:'QA',addressingPreference:'Neutral',languageMode:'Bangla',voicePreference:'System default',hasCompletedOnboarding:true,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()}));localStorage.setItem('nexa.background',JSON.stringify({enabled:false,quality:'low'}));""")
        page = ctx.new_page()
        page.goto("http://127.0.0.1:8766/suite/?engine=native", wait_until="domcontentloaded")
        field = page.locator('.dashboard-chat-card input[placeholder^="Ask Nexa"]')
        field.wait_for(timeout=45000)
        for name, prompt in prompts:
            baseline = state()["cursor"]
            field.fill(prompt)
            with page.expect_response(lambda r: "/api/engine/command" in r.url and r.request.method == "POST", timeout=15000) as sent:
                page.get_by_title("Send to Nexa", exact=True).click()
            code = sent.value.status
            start = time.monotonic()
            events = []
            last_count = 0
            last_change = start
            while time.monotonic() - start < 100:
                time.sleep(1)
                snapshot = state(baseline)
                events = snapshot.get("events", [])
                if len(events) != last_count:
                    last_count = len(events)
                    last_change = time.monotonic()
                assistant = any(e["kind"] == "assistant" for e in events)
                tool = any(e["kind"] == "tool" for e in events)
                if assistant and tool and not snapshot.get("speaking") and time.monotonic() - last_change > 4:
                    break
                if assistant and time.monotonic() - last_change > 15:
                    break
            # Keep only events after our own exact prompt, excluding older history.
            own = next((i for i, e in enumerate(events) if e["kind"] == "user" and e.get("text") == prompt), None)
            relevant = events[own:] if own is not None else []
            rendered = []
            for e in relevant:
                text = e.get("text", "")
                if e["kind"] in ("assistant", "tool") and text:
                    rendered.append({"id": e["id"], "visible": page.get_by_text(text, exact=True).count() > 0})
            result = {"test": name, "http_status": code, "elapsed_seconds": round(time.monotonic()-start, 1), "events": relevant, "rendered": rendered}
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
        ctx.close()
        browser.close()
    (ROOT / "nexa_suite/runtime/live-feature-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

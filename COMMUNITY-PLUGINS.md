# Reviewed community plugins — 27 October 2026

Source: https://github.com/upgraderguy777/jarvis-plugins (MIT).
Upstream states compatibility testing with Mark 54, not this modified Nexa.
Six source files were fetched, read, and adapted for the native Mark-LVI loader.
Original sources and SHA-256 hashes: `plugin_review/upgraderguy777/`.
Upstream MIT license retained in `plugins/COMMUNITY-LICENSE.txt`.

## Installed tools

| Tool | Example request | Requirements and limits |
| --- | --- | --- |
| youtube_controller | “YouTube captions চালু করো”, “ভিডিও ১০ সেকেন্ড এগিয়ে দাও” | Existing YouTube browser window/tab; uses foreground shortcuts. Pause/resume is a toggle and does not verify playback state. Does not search/open videos. |
| screen_recorder | “স্ক্রিন রেকর্ড শুরু করো”, “pause করো”, “রেকর্ডিং বন্ধ করো” | Saves MP4 to Downloads. Optional microphone audio needs permission/device; FFmpeg needed to merge audio, otherwise separate WAV. No recording begins at startup. Global hotkeys deliberately disabled; use text/voice. |
| screenshot_annotate | “স্ক্রিনে export button কোথায় circle করে দেখাও” | Captures screen on request, sends image to configured AI model for localization, saves/opens an annotated image. AI localization can be inaccurate. |
| notification_reader | “নতুন Windows notification দেখাও”, “Discord notification দেখাও” | Installed winsdk; Windows notification access permission required. Some unpackaged Python/Windows combinations may deny access. Watch mode is explicit only. Content is wrapped as untrusted data. |
| discord_messenger | “Discord-এ [নাম]-কে [হুবহু মেসেজ] লেখো” | Logged-in Discord desktop app; navigation/vision verification plus on-screen confirmation before Enter. Delivery is not independently verified. Voice-only approval of a legacy pending message is disabled. Autonomous chat takeover is unavailable in this adaptation; single-message sending is supported. |
| magi_system | “MAGI activate করো”, “MAGI quick mode-এ এই সিদ্ধান্ত বিবেচনা করো…” | Three AI persona calls per quick request; thinking/max can make many calls and be slow/cost quota. Not three independent AI products. Must explicitly activate before asking. No background deliberation at startup. |

The user's Python/Qt interface and existing Mark voice engine are retained.
No Electron/React runtime was installed.

## Adaptations

- All six use tier `extra`, allowing small-model tool budgeting to omit them.
- Screenshot, MAGI and single-message Discord one-shot calls use Mark's configured model fallback and 30-second per-call timeout via `core/community_plugin_client.py`.
- Removed import-time recorder global-hotkey thread creation.
- Notification plugin no longer runs pip automatically; missing dependency is an actionable error. Thread timeout is explicit rather than returning None.
- Discord single-message final send requires native physical confirmation and rechecks recipient/composer before submitting; no claim of verified delivery. Automatic takeover is blocked and its declaration updated accordingly.
- No external communication was performed during testing.

## Verification

Seven isolated integration/regression tests passed:
1. All six discovered, no import-time new threads.
2. YouTube captions -> expected key with desktop input mocked.
3. Start/pause/resume/stop -> actual decodable 160x120 MP4 from synthetic frames (no private desktop capture).
4. Annotation drawing changes synthetic image pixels.
5. Synthetic Windows notifications -> untrusted-content wrapper.
6. Discord preparation stops at on-screen confirmation; no Enter before approval; cancelled in test.
7. MAGI activation/quick voting with isolated state and mocked model responses.

These do not establish live YouTube focus reliability, microphone/video mux, AI visual accuracy, actual Windows notification permission, Discord delivery, or model/quota availability. Those require user-specific live tests. Existing Gmail is separate and retained.

Additional dependencies installed in this project's .venv: winsdk 1.0.0b10 and soundfile 0.14.0. For another computer, install `requirements.txt`, optional Nexa backend requirements, then `requirements-community.txt` with Python 3.12 on Windows. FFmpeg was not installed automatically.

Disable any plugin through Settings > Plugins. Remove its matching new .py file to uninstall after closing the app. Original Gmail/Productivity files were not replaced. Newly created runtime plugin state lives in `state/` and is ignored by Git.

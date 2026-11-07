# Native Mark interface restored

25 October 2026: the user's requested default is the existing modified Mark engine with its native Qt interface. `start_nexa.cmd` now runs `.venv/Scripts/python.exe -u main.py`, without `--modern-ui`.

The native UI now uses a static Qt chat theme: a central transcript, bottom composer and file picker, with settings and voice controls in a sidebar. Existing engine callbacks, content panels, media, quizzes and native confirmations remain. Nexa branding, Bangla defaults and registered extra tools are retained. No engine source was rolled back.

The chat theme is implemented in `core/qt_chat_theme.py`. It allocates no particle/avatar renderers, runs no HUD animation, stops the attachment animation, and stops hidden metrics/clock polling. Messages render directly without the former per-character typing timer. No Electron, Chromium, React or 3D renderer is part of this interface. `../backups/ui-before-qt-chat-20261025.py` preserves the preceding Qt layout.

Electron, the React shell, its globe and the old Nexa conversation pipeline are no longer part of normal startup. Extra productivity tools can start their supporting API on demand; that service is not a second conversation engine. The optional Nexa panel can still be opened explicitly. Its source is retained for recovery.

Before the switch, a source/config backup was saved to:
`../backups/Nexa-AI-before-native-ui-restore-20261025-164408.zip`

553 files; ZIP integrity checked. SHA-256:
`9c2b4cf85c34d814ccb301ef20a41f75221007deaaeca69baa118c18538c1b86`

Reinstallable dependencies, generated builds, caches and runtime history are excluded from this archive. Existing runtime data remains in place. The earlier Phase 1 backup also remains unchanged.

Switching the interface does not by itself fix the document-extraction issue recorded in FEATURE-TEST-REPORT.md. No claim is made that the Downloads command or every tool has passed a live test as part of this UI change.

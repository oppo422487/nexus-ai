# Native Settings UI — 27 October 2026

The Settings and Voice Controls sidebar buttons now open one non-modal native Qt settings window. Its navigation shows General, Assistant/Voice, Audio Devices, Voice Controls, Engine/Providers, Plugins, Plugin Settings, Memory, Gmail, Work/Documents and the existing Remote Access panel. Gmail and Work/Documents sidebar shortcuts open their matching page in the same window.

The cause of the old mismatch was that the new chat sidebar still called the old fixed-position green overlay drawers. Those were positioned for the original HUD and could obscure the chat, clip controls, and leave unrelated panels open. The new host uses stacked, scrollable pages and consistent charcoal/lavender styling. Provider cards wrap, forms remain usable at 800×580, dynamic legacy style refreshes are restyled, and reopening a previously closed form shows its contents again.

The existing form classes and their callbacks are reused. Assistant Save calls the original identity/voice callback; Audio Apply and Provider Apply retain their original callbacks; plugin switches retain their handlers. Opening settings does not change configuration or reconnect the engine. Explicitly saving engine/audio changes still reconnects through the existing implementation. OAuth/background work prevents accidental settings-window closure while busy. No new UI framework, renderer, animation loop or engine was introduced.

Implementation: `core/qt_settings.py` and the sidebar wiring in `core/qt_chat_theme.py`. The original `ui.py`, `main.py`, action implementations, account connectors and data stores were not edited for this UI task. `.gitignore` additionally excludes private runtime screenshots/logs and SQLite sidecar files from future commits.

Validation: **64 automated tests passed**, including eight new native UI tests. These check every settings category, real MainWindow sidebar wiring, small-width provider cards, original save callback, close/reopen behavior, busy account-work protection and dynamic restyling. Synthetic screenshots were visually inspected for general, identity, audio, provider, plugin and work/document pages. UI tests use fake account/configuration/device data and did not send mail, create events, record microphone audio or modify the user's engine settings. The test suite covers existing functionality with its documented mock/live boundaries; this UI change is not a new live end-to-end test of every external integration.

Recovery:

- Private source repository: https://github.com/oppo422487/Nexa-AI
- Working version **before UI changes**: commit `38679e464cbdb625cdb29e846fc6625185bca347`, tag `working-before-settings-ui-20261027`.
- Local source/config ZIP: `..\backups\before-settings-ui-20261027-213110.zip`.
- ZIP SHA256: `9ebd93d4aa0eaf7e56302046d7afe6a12ba40320c4ce31fa71095d2482964730`.

The local ZIP contains private configuration and must stay private. The GitHub repository is a separate sanitized source snapshot: it excludes API keys, OAuth credentials/tokens, conversation databases, model data, runtime screenshots/logs, virtual environments and build output. Personal mailbox identifiers in exported source/documentation samples are replaced with `user@example.com`. It retains the upstream MIT license. The original project's Git remote/history has not been repointed or rewritten. Reinstall dependencies and connect accounts when restoring a source-only checkout on another computer.

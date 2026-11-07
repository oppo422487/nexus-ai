# Startup briefing and English interface — 27 October 2026

The native interface now uses English throughout Chat, Settings, Voice Controls, Gmail setup, Work & Documents, file dialogs, status labels and tooltips. The remote dashboard assistant label is English too. Stored user text, message history, document contents and the conversation language are not translated. The existing Bengali-first assistant instructions remain unchanged.

Startup briefing is enabled on this PC by setting only `morning_brief_enabled` to true. The switch is shown as **STARTUP BRIEFING** under **Settings → Voice controls**. It runs once per app launch after the engine connects. Existing wake-word sleep behavior is preserved: an asleep assistant does not start speaking.

The greeting includes the current Asia/Dhaka date/time, a brief reference to remembered interests/projects and important unfinished work if those records exist. It uses saved preferences/projects/wishes, the previous session summary and local follow-up/job records. Completed and cancelled tasks are excluded. If no personal context is stored, the assistant is instructed to omit it rather than invent it. A task-store error is distinguished from having no tasks. The briefing does not execute/resume jobs or send messages.

News is fetched in parallel with the greeting and delivered afterwards, with up to two important headlines. Network failures are reported instead of fabricated news. If the user starts speaking/typing, the late news turn is suppressed. Gmail's startup summary waits behind the greeting/news to avoid sending overlapping startup turns.

Validation: 70 regression tests passed, including synthetic startup greeting/news sequencing, interruption suppression, factual context extraction, completed-task filtering, missing-store behavior, English UI literal coverage and the existing native settings/callback checks. Settings previews were inspected in English. These automated startup flow tests mock the external news/model service; launch diagnostics are separate from a guarantee that each spoken sentence was heard.

Before changing these files, a local source/config snapshot was saved as `..\backups\before-english-ui-briefing-20261027-220022.zip`. Keep this ZIP private because it includes configuration. GitHub source copies exclude private configuration, tokens, databases and runtime artifacts.

# Teach mode — Nexa-led demonstrations

This first version implements the user's selected method: **ask Nexa to perform each step, save those actual tool calls, then review and replay the routine**. It is a structured reusable workflow, not retraining the language model or recording arbitrary mouse/keyboard activity.

## Using the native interface

1. Open **Teach mode** in the sidebar, or **Settings → Teach mode**.
2. Enter a routine name such as **Weekly report review**, then click **Start teaching**.
3. Return to chat and ask Nexa to perform the demonstration one step at a time. The actions execute normally during teaching. The sidebar shows **REC**, the routine name and recorded step count.
4. Use **Refresh** in Teach mode to inspect the recorded steps and any skipped actions.
5. Click **Finish & save**, or ask Nexa to finish teaching.
6. Select the routine. Use **Edit selected step** to change a saved path/query, or remove a step. At least one supported step is required.
7. Click **Review & run** and inspect the complete plan before **Run these steps**. A voice/chat run request uses the existing physical confirmation banner.
8. Use **Stop running routine**, the main chat **Stop** button or Escape in the main chat to prevent subsequent steps. A current file/network operation may finish before stopping.
9. Use **Show last run results** to inspect saved receipts and failures.

### Example spoken commands

- “Nexa, ‘সকালের রিপোর্ট’ নামে একটা কাজ শেখা শুরু করো।”
- “Downloads ফোল্ডারে কী কী ফাইল আছে দেখাও।”
- “এই Excel ফাইলের প্রথম শিট থেকে A1:F30 পড়ো।”
- “এই ফাইলটার ব্যাকআপ ওই আলাদা ফোল্ডারে রাখো।”
- “শেখা শেষ, কাজটা সেভ করো।”
- Later: “‘সকালের রিপোর্ট’ কাজটার ধাপগুলো দেখাও, তারপর চালাও।”

Use the actual paths of selected files. Demonstrating a backup creates a real backup at teaching time; replaying it explicitly creates another timestamped archive. The name of a routine is not a new schedule.

## Supported steps

| Tool | Recorded/replayed operations |
|---|---|
| `open_app` | Application names; Downloads/Desktop/Documents and other known folder aliases normalize to file-open steps. Existing launch verification remains active. |
| `file_controller` | open, list, read, find, info, disk_usage |
| `web_search` | search and news queries |
| `nexa_life` | document_read, document_index, archive_search, excel_read, translate, backup |

During teaching, Nexa is instructed to prefer `nexa_life` for supported document/Excel/translation/backup actions. Unsupported calls are reported as **Not recorded** and their arguments/results are not retained in the teaching record. They may still execute through the ordinary app when the user asks, including existing approvals, but they are not saved for replay. In particular, this version does not replay mail/messages, arbitrary typing/clicking, code/shell commands, deletion, calendar writes or unlisted plugins. Existing Gmail confirmation behavior is unchanged.

## Replay behavior and limits

- Up to 24 steps and a bounded plan size so the entire approval can be displayed.
- Saved paths, queries and text are literal arguments. New files/dates are not guessed. Edit the step before a new run if its input changed.
- A run executes the reviewed snapshot through a fixed allowlist. Edited plans invalidate an earlier review.
- Each explicit run starts from the first step. It is not automatic resume; prior completed steps may execute again when the user chooses another run. Inspect a failed run before repeating, especially a backup.
- Exceptions stop the run; later steps are not executed and no automatic retry occurs. Stop requests are checked between operations.
- Restart marks abandoned teaching sessions/runs as interrupted. It never replays them automatically. An interrupted teaching session with recorded steps can be selected and finished/saved.
- Large output receipts are truncated explicitly to a preview to bound local history size. Use the normal original tool for full document content.
- There are no global input hooks, screenshots, new microphone recording, always-on scheduler or additional UI framework. Teaching is off by default and only actual supported Nexa calls are observed while explicitly active.
- Basic credential-pattern and known-account-file exclusions apply. This is not a universal secret detector. Saved arguments and receipts are private local data in `memory/life.sqlite3`, not encrypted at rest; discard routines you no longer want.

## Verification

Synthetic checks cover engine hook → record/save → persisted recipe → replay, actual Excel reading and SHA256-verified backup creation, unsupported-action exclusion, failed actions, review cancellation, edit-after-review rejection, run failure, stop between steps, interrupted-session handling, bounded review size and the native Start/Finish buttons. Native Qt preview uses synthetic paths and no desktop actions. No real email/message was sent, user file deleted or user mouse activity captured in these tests. External websites and every possible installed application are not all live-tested.

Source/configuration backup before implementation: `..\backups\before-teach-mode-20261028-195855.zip`. The private GitHub source repository also preserves the preceding working version. Runtime records, model files, credentials and screenshots are excluded from source pushes.

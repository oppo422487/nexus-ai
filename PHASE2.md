# Phase 2 — original Nexa interface, existing native engine

Start with `start_nexa.cmd`, or `.venv/Scripts/python.exe modern_desktop.py`.
The default application is now the original React/Electron Nexa interface.
`main.py` without `--modern-ui` remains the native compatibility interface.

## Connections

- The native engine owns its original microphone, speaker, live/local provider,
  memory, tool and plugin runtime. Its Qt window stays hidden during normal use.
- The original Nexa sidebar, dashboard, chat, settings and animated globe remain.
  A subdued particle layer responds to the native speaker level behind the UI.
- Typed chat goes to the native engine. It does not also run Nexa's old chat
  pipeline or start a second automatic text-to-speech request.
- Voice transcripts, assistant responses, context and tool outcomes flow into
  chat through cursor-based events. Restarted engines use a new generation ID.
- Native confirmations appear in the chat card. Each pending confirmation has
  a fresh ID; an older or repeated button cannot approve a replacement action.
- Camera preview and interactive quiz controls are available inside chat.
- Gemini key entry is in Settings. Existing native credentials are retained.
  Advanced provider/device settings still open the native compatibility surface.
- The original Nexa feature panels and their backend permissions remain usable.
  Their permission toggles govern the added Nexa tools; the native engine keeps
  its original action and confirmation policies.

## History behavior

Clear removes the displayed chat history, not the model's native conversation
or saved memory. A browser-stored generation/cursor prevents old engine events
from reappearing after page navigation or reload. New events remain visible.

## Phase 1 recovery

Before Phase 2 edits, 556 files were archived and individually SHA-256 verified:

`../backups/Nexa-AI-phase-1-before-original-ui-20261024-143957.zip`

`../backups/restore-phase-1.ps1` verifies the archive checksum and extracts into
a new folder. It refuses to overwrite an existing project. The archive includes
local configuration and data; reinstallable dependencies/caches are excluded.
`BACKUP-PYTHON-DEPENDENCIES.txt` records the frozen Python dependency versions.
Run `python setup_nexa.py` in a restored folder before launching the old phase.

The original `../nexaai` checkout has not been edited by this integration.

## Verification scope

Automated browser checks use a separate, temporary browser context and fake
engine events/commands; they never send an email or execute a desktop action.
Native bridge tests cover real HTTP authentication and dispatch boundaries.
The backend test suite covers persistence, validation and tool behavior with
isolated test data. Live external-provider readiness and actual output are
reported separately in `VERIFICATION.md` when checked.

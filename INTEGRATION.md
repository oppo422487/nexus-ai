# Nexa AI integration

The native Mark-LVI runtime remains the base. Original actions, providers, avatar,
vision, plugin loader, wake-word detector and confirmation flow are retained.
The original license and upstream attribution remain applicable.

## Added connections

- `core/nexa_identity.py`: Bengali-first conversation policy, including initial greeting.
- Native display name and default identity: Nexa AI / নেক্সা আই.
- `plugins/nexa_productivity.py`: discovered by the existing plugin loader;
  notes, tasks, shopping, calendar, voice preferences, SMTP email, content export,
  queued images, image history, audit statistics, permission status and diagnostics.
- Every plugin write goes through the existing physical HUD confirmation gate.
  Model-supplied confirmation flags cannot authorize it.
- `core/nexa_suite.py`: starts the independent service on demand on loopback port
  8766, stores data under `nexa_suite/runtime`, and stops its owned process at exit.
- HUD button opens the bundled React panel at `http://127.0.0.1:8766/suite/`.
  The companion panel retains the existing Nexa feature pages and backend checks.
- Bengali default profile, Bengali primary navigation and Bengali primary HUD controls.
- Optional API keys and permissions are still required by their respective providers.

Only source files were copied from Nexa. Existing credentials, models, local data,
virtual environments and dependencies were excluded. The original Nexa checkout
is unchanged. Install with `python setup_nexa.py` and run `.venv/Scripts/python.exe main.py`.
The suite panel uses a browser; the original voice and avatar interface remains native Qt.

## Boundaries and remaining limitations

- This is an additive plugin/service integration, not a rewrite into one UI framework.
- Deep settings, provider errors and some secondary UI labels remain English.
  Bengali-first does not mean complete translation of every inherited screen.
- The original optional wake-word model still detects “Hey Jarvis”; renaming the
  application does not retrain that audio model. Push-to-talk and the Wake button remain available.
- The suite's voice screen is independent of the native Gemini Live session;
  opening it does not migrate microphone state, model settings or conversation history.
- Existing Nexa automation workflow templates remain previews, not new executable agents.
- Existing skills retain their original semantics; additions do not impose Nexa's
  restrictive desktop permissions on Mark's original desktop actions.
- Live Gemini audio, SMTP delivery, provider image generation, webcam and actual
  desktop automation require a configured interactive run and are not proved by unit tests.

## Verification

- Seven integration tests: fresh identity, read-only dispatch, missing-UI refusal,
  model confirmation bypass prevention, reviewed payload immutability and single
  execution, invalid operation rejection, and unchanged dashboard crypto salt.
- Twenty-two selected inherited backend tests passed (email, productivity,
  extended features and architecture boundaries).
- Frontend TypeScript checks, production build and 41 source contract checks passed.
- FastAPI smoke verification passed: fork identity endpoint, Bengali panel and
  built assets, confirmed note persistence, analytics and refusal of unconfirmed email.
- The production build retains the inherited large globe bundle warning.

For browser automation, the upstream browser installation still applies:
`.venv/Scripts/python.exe -m playwright install chromium firefox`.
For offline voice, install and configure the upstream optional Whisper/Piper
providers through the engine settings; this integration does not download voice models.

- Native Qt window rendered successfully with registered Windows Bengali fallback fonts.
- Actual isolated service process startup/read requests/static panel/shutdown passed.
- Upstream provider self-tests: 99 passed, 0 failed after supplying an empty temporary
  config expected by that test harness; the original config state was restored.
  Optional Piper-specific checks were skipped because Piper is not installed.
- Dedicated environment dependency consistency check passed (`pip check`).

On this machine dependencies and the panel have already been prepared.
Double-click `start_nexa.cmd` to start the native application. No API credentials
were added or copied. The setup screen will ask for provider configuration.

## Dark particle visual

The default central visual is now a dark organic particle volume, replacing
human facial rendering. `core/particle_blob.py` consumes the existing scheduled
playback envelope; speech accelerates internal flow and softly deforms the
volume. Microphone activity does not activate the speaking deformation, and
muting/ending speech lets it settle. Old `face` preferences migrate to
`particles`; the alternate reactor remains available in the visual toggle.
The prompt no longer tells the assistant it has a human face.

Synthetic speaker/microphone/mute checks and finite projection checks passed;
the seven integration tests and Python compilation passed. Offscreen render
averaged approximately 28 ms per particle frame at 640 x 640 on this machine.
This is renderer verification, not an end-to-end live voice latency measurement.

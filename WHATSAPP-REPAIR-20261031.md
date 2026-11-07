# WhatsApp repair report — 2026-10-31

## Evidence
- The open native settings panel did not refresh after a chat update, and routing saves could overwrite the stored message from a stale form.
- Recent production calls completed the greeting; the subsequent stereo capture logged 15.1 seconds with peak=0 and RMS=0. Existing notes contain no recoverable caller transcript. The latest version left those calls open for takeover.
- Per-contact replies were not implemented, despite conversational acknowledgements claiming they were saved.

## Changes
- One atomic config writer; live settings refresh, stale-message conflict protection, routing saves preserve existing message/deadline.
- Separate exact-contact rules, exact aliases/full phone numbers, independent expiry, native settings table and chat tools. Verified incoming identity selects the rule; a fresh identity/message/expiry check runs before acceptance. No fuzzy or guessed caller match.
- Dedicated return-speaker WASAPI loopback bypasses the previously silent cable recording pin. Bounded callback reads avoid blocking indefinitely. It never selects the default speaker mix or room microphone.
- No-signal/error notes are truthful. Captured WAVs remain private; transcription produces stored original-language notes and a ready notification. Caller contents cannot authorize actions. Only captured speech enables normal end-call cleanup.

## Validation and limits
- Automated tests cover exact selection, independent timers, caller change/expiry before accept, settings conflicts, quiet right-channel speech, dedicated loopback selection/callback lifecycle, note storage and transcription.
- The actual dedicated loopback opened at 44100 Hz stereo with start=False, then closed: no call or live audio recording was performed.
- Live remote-call capture, exact caller recognition on this WhatsApp build, and remote hearing still require user verification. An unrecognized caller can use only a live default rule.
- Backup: ../backups/before-contact-call-rules-20261031-004712.zip (private source/config/consistent databases).

Loopback implementation reference: [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch).

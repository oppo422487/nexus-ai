# Incoming call assistant setup

The assistant introduces itself using Settings > Profile user name, speaks the exact saved reply, invites a short caller message, saves it privately, then requests hangup. It does not impersonate the user.

## Two independent routes

| Purpose | Sender/output | Receiver/input |
|---|---|---|
| Nexa speaks to caller | Nexa: CABLE Input | WhatsApp microphone: CABLE Output |
| Caller speaks to Nexa | WhatsApp speaker: Hi-Fi Cable Input | Nexa caller recorder: Hi-Fi Cable Output |

Keep Nexa's normal microphone/speaker on physical devices. The caller recorder never uses the room microphone or default desktop loopback.

## Driver and app settings

1. Install the official VB-Audio Hi-Fi Cable package downloaded under runtime/hifi-cable-installer. Its installer signature was verified before use. Windows requires administrator approval and the vendor requires a restart. No driver security settings should be changed or bypassed.
2. Set Hi-Fi Cable playback and recording endpoints to the same sample rate (e.g. 44100 Hz), as required by the vendor. Do not enable ASIO Bridge passthrough.
3. WhatsApp > Settings > Audio: microphone CABLE Output; speaker Hi-Fi Cable Input.
4. Nexa > Settings > WhatsApp calls: enable profile introduction; choose Hi-Fi Cable Output as the dedicated caller recording input; confirm WhatsApp speaker routing; enable caller-note mode. Save.
5. Enable a timed call rule through chat with your exact message and duration. Changing the profile name changes the introduction; names are never hardcoded.

A two-second initial wait is used. If the caller speaks, recording ends after two seconds of silence or thirty seconds maximum. Audio/transcripts stay in the private local memory store; transcription uses the configured Gemini Live API. The caller is told their message will be noted. Unread notes are available through list_call_notes and startup context. Pending transcription resumes after restart.

Call acceptance and hangup can still depend on readable WhatsApp controls or available vision service. A hangup request is not claimed as verified remote termination. Actual calls and remote hearing must be tested by the user.

Official source: https://vb-audio.com/Cable/index.htm#DownloadASIOBridge

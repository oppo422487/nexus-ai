# WhatsApp Desktop calls — initial integration

## Scope

Ported the call-control / virtual-audio-routing approach from BitCrush777/Jarvis-Ai-Assistant (plugins/whatsapp_desktop_call.py and plugins/whatsapp_voice_bridge.py). Upstream MIT copyright 2026 Saidarshan.K is retained in licenses/whatsapp-calls-MIT.txt. Upstream source was reviewed privately under plugin_review/; it is not imported/executed or published.

The original full conversation bridge assumes player.stt/player.tts and mutates core.tts.TTS_OUTPUT_DEVICE. Those interfaces do not match Nexa's Gemini Live engine. This integration instead provides compatible desktop controls and explicit one-way outgoing call-message playback. It does NOT claim to port the entire two-way conversational bridge.

Available commands through whatsapp_desktop_call:
- voice_call + exact contact_name: search by accessible named input, select an exact unique recipient, verify recipient near voice-call button, request voice call.
- answer_call / reject_call / end_call: explicit user commands; no background automatic answer.
- status: inspect current readable call controls/state.
- call_and_say + contact_name + message: check virtual routing, generate exact user-supplied Bangla/English message, request call, wait up to 45 seconds for a non-zero call timer beside end-call control, then play once to the selected virtual playback endpoint. Leaves call open; no redial or automatic repeat.
- stop_speaking: cancel the call-message operation/playback, without stopping normal assistant audio or hanging up.

The initial phase did not add incoming auto-reply rules. The automatic incoming exact-message phase is described below; autonomous caller conversation, transcription/recording, video-call controls and Messenger integration remain out of scope. Existing WhatsApp messaging code is unchanged.

## Setup

Settings > WhatsApp calls explains routing and lists only supported virtual playback endpoints. The audio output must be configured there, and the user must confirm WhatsApp's microphone uses the matching recording endpoint. The setting is not an automatic verification of WhatsApp's selected microphone.

VB-CABLE official source: https://vb-audio.com/Cable/
Its CABLE Input is the Windows playback endpoint Nexa writes to; CABLE Output is the recording/microphone endpoint WhatsApp reads. This is software routing and needs no physical cable. The signed driver requires administrator installation and a restart according to its author; it is not silently installed by this feature.

Supported cable outputs are discovered at runtime; missing configuration fails before dialing. Manual call controls do not require the cable. Do not route the normal Nexa microphone/speaker through the cable.

## Verification

133 full-suite tests passed before a small separate-call-window compatibility change; final validation is reported in chat. New tests mock controls and audio; no real contact called, no message sent and no private call recorded. No live WhatsApp call/remote hearing has been verified.

English accessible control names are currently supported. WhatsApp UI versions/languages may expose different names or layouts. Missing/ambiguous recipient, call control, or timer fails explicitly; no fixed coordinate fallback or blind Enter. A readable timer is evidence of connected UI, not proof remote hearing. Virtual playback completion is not recipient delivery proof.

## Backup / restore

Private pre-change ZIP path and SHA256 are in runtime/whatsapp_call_backup.json. Backup was integrity checked and includes source, configuration and consistent SQLite snapshots, excluding dependencies/caches and files over 80 MB. Close Nexa before restoring; copy consistent-databases snapshots to memory. Never publish the private archive.


## Log fixes after first user test
Installed and declared missing miniaudio (1.71). Exact already-open recipient headers now bypass chat search. WebView/call descendants of verified WhatsApp process roots participate in window and foreground identity; browser title matches remain excluded. Added support for Search input textbox and Unicode paste into an identified search field when ValuePattern is unavailable. Saved cable output device 6 was resolved successfully. Real Edge speech synthesis and MP3 decode succeeded at 44100 Hz using a synthetic test phrase; no playback or call performed. 135 tests passed. A real WhatsApp call and remote hearing remain unverified.

## Call pipeline repair

Current WhatsApp builds may expose an empty WebView accessibility tree. The call controller now falls back to a foreground, process-verified WhatsApp-window image sent to the existing Gemini VISION provider. No image is saved. This can be disabled in WhatsApp calls settings. It needs available vision quota/network; unavailable or ambiguous results stop the action. It does not create another browser or UI runtime.

Before each visual call click, two fresh observations must agree on the requested control, call state and partner. Search-result names must match the requested name. A failed/uncertain call click is never retried through another method. Fixed screen positions and browser title matches are not used.

speak_in_call plays the exact authorized message in an already connected call, without dialing or accepting; answer_and_say accepts an explicitly requested incoming call and waits for connected UI before playback. call_and_say retains outgoing operation. These require the configured cable and WhatsApp microphone routing. A connected UI does not prove remote hearing. Automatic incoming monitoring and two-way conversational replies remain unimplemented.

An asynchronous job reserves the operation before reporting started, preventing duplicate jobs. Errors identify the failing stage and are written to both terminal and chat. Speech uses its own explicit virtual output stream; it never changes the normal voice engine output or globally stops audio. A cloud call is not made per playback chunk. During playback cancellation and call-window existence are monitored; inaccessible call-end state cannot be independently detected in every audio chunk.

Private backup and SHA256: runtime/call_pipeline_backup.json. Verification uses fake windows, providers and audio streams; no live contact calls or message delivery tests are performed by the coding agent.

## Follow-up log repair
User tests reported unusable vision responses and loss of focus. Exact-window activation now verifies process ownership, restores the target window, uses the foreground thread input queue when Windows refuses background activation, detaches it immediately, and waits for the exact HWND rather than checking only a process ID. Focus lost after an observation still stops the click.

Vision now requests a strict response schema, accepts the SDK parsed dictionary or non-thought response parts, and reports finish reason / response length without logging private screenshot text. Empty VISION responses continue to the next existing REST vision model instead of terminating the ladder. This does not retry a call click. A synthetic blank-image cloud request checks the schema/parser without capturing WhatsApp or contacting anyone. Real call control remains for the user to verify.

## Automatic incoming exact-message reply

User-configured auto-answer is now supported. Settings > WhatsApp calls has an enable checkbox, exact-message field and watcher status. Chat actions enable_auto_reply (requires exact message), disable_auto_reply and auto_reply_status manage the persistent rule.

A daemon polls local WhatsApp accessibility/windows and already-permitted Windows toast notifications. It never requests notification permission in the background. Only fresh voice-call notifications, verified incoming accessibility controls or a new WhatsApp window trigger inspection; old/missed/video notifications are excluded. A hint alone never accepts a call: the existing answer control independently requires a current incoming call. No continuous screenshot/model polling. Configured message audio is prepared before answering. The exact message is played once after connection verification. The call is left open, with no recording or conversation.

Incoming attempts use event deduplication and a short three-second debounce. Fresh call hints during debounce are retained instead of dropped. An accepted call with failed playback is left for manual takeover until its capture session ends. WhatsApp must be open and expose either an incoming window/control or fresh notification. With inaccessible UI, successful vision service remains necessary; known provider failures are not solved by enabling this watcher. Cable routing still requires the correct WhatsApp microphone setting. Disable cancels active auto-reply playback, but does not hang up.

## Nexa voice and timed rules
Call speech uses a short isolated Gemini Live session with the same selected voice and model as Nexa (Aoede on this installation), with no microphone, tools or conversation history. It renders only the saved message; complete PCM and matching output transcript are required before playback. Only brand-script normalization and punctuation are allowed in transcript comparison. No Edge/male voice fallback. Audio is resampled once to the selected virtual endpoint and buffered before answering.

Playback no longer traverses UIA on the audio thread: those synchronous window-tree queries could block PCM writes and cause stuttering. Cancellation and inexpensive window-liveness checks remain; stream underflow is now an explicit error. The connected UI is verified before playback. Remote hearing still requires user testing.

Chat enable_auto_reply now accepts duration_minutes (1–10080); next one hour is 60. Expiry is persisted as a UTC epoch and returned with Asia/Dhaka (+06:00) display time. A timer disables the rule/cancels its active playback; restarting after expiry does not reactivate it. Settings has a duration field (0 = no expiry). Updating the message invalidates cached speech and cancels stale active auto-reply playback. These are incoming-call rules, not text-message auto-replies.

## Accepted-call silence repair

User logs showed a successful incoming accept followed by connection_verification failure because every Gemini vision model was unavailable/out of quota. answer_and_say now verifies Windows capture-session metadata twice after the accept action: a WhatsApp-owned process must actively read the recording endpoint corresponding to the selected playback cable, with endpoint/session unmuted. It does not record audio or change Windows devices. This proves local microphone routing/readiness, not remote hearing or remote connection state. Wrong microphone, muted route and no active capture are reported distinctly. This incoming path performs no cloud vision request after accepting. UIA/vision may still be needed to identify and accept the incoming call itself.

Transient COM accessibility failures before a click can fall back to a process-owned native window and visual controls. A call click with uncertain outcome is never repeated. The watcher retains last_call_status/last_call_detail when it returns to watching; watching is not evidence that a prior call/audio failure was fixed. The model is instructed to retain the user's original message language instead of translating Bengali into English.

Incoming-call playback also avoids retaining the closed incoming popup as a liveness requirement. WhatsApp can replace that popup with another window after accepting. A separate capture-session metadata monitor now stops the PCM stream when WhatsApp releases the cable reader, without running UIA or Core Audio polling on the audio-writing thread.

## Personal introduction, caller reply note, then hangup
The current user-name profile supplies the owner name; there is no hardcoded owner. The optional personal introduction says Nexa AI is that user's desktop assistant, followed by the exact configured message. Caller-note mode also invites a short message and discloses that it will be noted. Name/voice/message changes invalidate prepared audio.

Caller-note mode requires a second, independent virtual cable: keep Nexa playback -> CABLE Input -> WhatsApp microphone CABLE Output; route WhatsApp speaker -> Hi-Fi Cable Input -> Nexa recording Hi-Fi Cable Output. Confirm the return route in Settings > WhatsApp calls. Never select the room microphone, default speaker loopback or the existing outbound cable as the return recording source. Hi-Fi Cable's playback and recording formats must use the same sample rate per its author. No Windows global device settings are changed automatically.

After playback, the dedicated return speaker is captured through WASAPI loopback (PyAudioWPatch), rather than the silent Hi-Fi recording pin observed in production. This is only the selected independent virtual return speaker, never the Windows default mix or room microphone. The recorder waits up to fifteen seconds for speech, then until two seconds of silence (maximum sixty seconds). It stores a private short WAV and note in memory/life_data/call_notes and life.sqlite3. An isolated Gemini Live input-transcription session writes the original-language transcript; no tools are exposed, output speech is ignored, and caller text is untrusted data. Transcription does not hold the call open. Missing/error/no-reply statuses remain explicit.

Hangup cleanup is armed only after the spoken message finishes. A failure before completed playback leaves the accepted call open for manual takeover; a later note-capture failure or no-signal result leaves the call open for manual takeover. Losing capture confirms local capture ended; this is not proof of remote hearing. UIA/vision availability can still affect the final end-call click. list_call_notes and mark_call_note_read expose unread notes; startup context includes unread caller messages, and returning users are instructed to receive a factual summary rather than execute caller requests.

## Instant hangup and missed next-call repair
The old cleanup ran after acceptance even if routing/playback failed, which could terminate a call before any greeting. Cleanup is now registered after completed playback. Prepared speech is copied by an owned PortAudio callback stream with high latency buffering; an initial output-underflow flag is counted instead of immediately throwing and ending the call. No UI/provider work runs in that callback. Cancellation and capture-reader loss stop the owned stream.

Structured stage events persist to runtime/whatsapp-events.jsonl even for pythonw/desktop shortcut launches; message content and caller transcripts are not included. Completed playback, interrupted playback, manual takeover, note errors and hangup status remain distinct. Windows Hi-Fi playback and recording mix rates on this PC were both verified as 44100 Hz without playing or recording audio. Real-call/remote-hearing verification remains with the user.

## Device-unavailable (-9985) repair
Runtime audit identified accepted calls failing to open MME device 6 (CABLE Input) at playback. The same physical cable opens through Windows WASAPI shared mode at its native 48000 Hz stereo format. Logical cable aliases are now resolved to a unique WASAPI endpoint first, then DirectSound, without selecting a default speaker or different cable. Mono speech is duplicated into stereo channels without changing duration. WASAPI explicitly uses non-exclusive mode with engine conversion.

Before requesting a call/accept action, the actual callback output is opened without starting or writing any audio, retained throughout acceptance/verification, and then started without reopening. Device-open failures therefore occur before accepting the caller. Actual product preflight was verified on this PC both normally and in the call worker's UIA/COM context; no call, recording or audio playback was performed. A fresh incoming hint can also clear manual-takeover gating even if WhatsApp leaves a microphone session active. Audit origin now uses the running command rather than imported unittest modules, so production calls are not mislabeled as tests.

## Retain the exact callback stream across acceptance
A later production trace showed device 19 passed preflight and then failed with -9996 on the second OpenStream after acceptance. Prepared callback playback is now opened before the call and retained as one owned stream. Only StartStream runs after routing verification; there is no second OutputStream constructor. Speech synthesis and endpoint/sample-rate checks also complete before accepting an incoming call. A regression verifies the exact order open -> accept -> start -> close with exactly one constructor.

An actual callback stream was opened and retained across the worker UIA/COM context and capture-readiness queries without starting it; the separate caller input was also opened and closed without recording. These are device-lifecycle checks, not remote call/hearing verification.

## Caller rules and settings synchronization (2026-10-31)
Chat and the native settings page share one atomically written config. The page refreshes unedited default text from chat; unsaved local edits are preserved, and conflicting stale saves are rejected. Routing-only saves do not renew deadlines or overwrite the default message. Per-contact replies appear in a native table with exact names, optional exact aliases/full phone numbers, exact text, independent expiry and disable controls. Chat tools: set_caller_reply, disable_caller_reply, list_caller_replies. A rule is selected only from the verified incoming caller identity, and both identity and current unexpired message are checked again before acceptance. Unknown callers may use only an active default; no default means no automatic answer. Expiry of the default does not disable another contact's still-live rule. Spoken audio for live rules is prepared before watching; generated speech must pass exact transcript validation.

Production traces showed both return channels had peak=0 and RMS=0 for 15.1 seconds, so previous notes contained no caller transcript. The new loopback path bypasses the cable recording pin and uses bounded callback queues (silent endpoints cannot hang a blocking ReadStream forever). No-signal is not reported as proof the caller said nothing. Capture errors are stored as unread error notes and leave the call open. Completed captures save private WAVs, asynchronously transcribe into notes, and announce a ready note in chat. Pending/no-signal/error notes must never be summarized as caller words.

Loopback reference: https://github.com/s0d3s/PyAudioWPatch . Device opening without starting the stream and synthetic tests validate lifecycle and data handling; remote-call recording still requires user live verification.

## Literal No Name caller repair
The existing Bengali rule name নো নেম now canonicalizes to the literal English contact No Name, with whitespace and emoji decorations ignored. Bengali vowel marks are preserved for other names; this is not a generic unknown-caller category. Identity reading first tries accessibility text in a separate current incoming-call window, then local Windows OCR of that same window with incoming-voice-call evidence. It never reads a sidebar/chat contact as the caller. Verified online vision remains a fallback. If identity cannot be verified while personal rules are active, leave the call unanswered instead of silently speaking the default. The selected reply is exposed in watcher status; diagnostic events record source/mode/message fingerprint without message contents. The saved No Name message is preserved.

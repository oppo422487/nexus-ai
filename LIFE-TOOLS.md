# Nexa personal tools — 27 October 2026

Phone control is excluded at the user's request. The existing Mark engine and native Python/Qt interface remain the app entry point. No Electron, React, Chromium, 3D or continuous screen recording is added.

Open `start_nexa.cmd`, then **কাজ ও ডকুমেন্ট** in the sidebar. Tools are also exposed to the voice/chat engine as `nexa_life`. Restart an older running app to load the new plugin.

## What is available

| Feature | Implementation and practical boundary |
|---|---|
| PDF/image OCR | Selected PDF pages with little embedded text are rendered through PDFium and read with Tesseract. Default `eng+ben`; both language files are required. PDF limit 30 pages; document limit 50 MB. Normal PDFs, DOCX, TXT, MD and CSV can be archived. |
| Personal archive | Local SQLite/FTS search stores extracted text, source path, SHA256 and page/character locations. Originals are not moved. Changed/missing originals are identified. Removing an archive entry leaves the original intact. |
| Evidence-backed answers | Retrieved passages and their exact IDs are given to the existing AI provider. Invalid/missing citations produce evidence-only output. Citations establish provenance, not a guarantee that every AI interpretation is correct. Keyword search is used, not semantic embeddings. Selected evidence is sent to the configured AI when requesting an AI answer. |
| Read-only Excel | `.xlsx`/`.xlsm` sheets and ranges, up to 5000 cells. Formula strings and cached values are separate. No macros/formulas are executed; no workbook is written. `.xls` needs conversion. |
| Backup/restore | New timestamped ZIP, per-file SHA256 manifest and verification. Up to 500 MB / 3000 files; `.venv`, `.git`, caches and node_modules skipped. Restore only to a new folder, never overwrite. ZIPs are **not encrypted** and may contain private data. Partial restore failures leave the destination for inspection. |
| Offline translation | Local Argos model data + CTranslate2/SentencePiece on CPU. Bengali ↔ English models installed and tested here. No cloud fallback or sentence-model download. Punctuation splitting and bounded chunks are used; review machine translations. Models load on demand. |
| Spotify | Search, playback status/devices, exact track URI play, pause, next/previous, volume. Requires Spotify developer credentials, allowed account, OAuth, Premium and an active player. No account was connected by this implementation task. |
| Calendar | List next 30 days and create timed events on the primary calendar after a native confirmation showing the full event. Separate Calendar OAuth token; Gmail authorization alone does not grant Calendar access. No attendee invitations are sent. Unknown API outcomes are recorded instead of silently retrying. |
| Durable jobs | Save up to 12 explicit steps: document index, archive search, Excel read, offline translate, backup. Run/resume by ID after reviewing the plan. Completed steps retain receipts and are not repeated. Interrupted read steps can resume; interrupted/failed backup steps require inspecting their destination and creating a new job. No arbitrary command/code execution or general autonomous agent. |
| Promises/follow-ups | Title, owner, due time with timezone, source/quote, open/waiting/done/cancelled state. Overdue open items notify once while Nexa runs, including at next launch. Completion is explicit; the assistant does not guess that another person finished a task. |
| Meeting → tasks | Analyze a selected transcript with the existing AI. Only tasks with exact quotes present in the transcript are retained. Preview first, then physically accept to create follow-ups; repeated acceptance does not duplicate them. Audio transcription uses a separately downloaded Whisper small CPU model. No ambient microphone recording added. |
| Opportunity/change monitor | User-selected public HTTPS text pages, optional keyword and interval (minimum 5 minutes). First fetch establishes baseline; relevant content changes store a diff/source/time and notify. Private/local URLs are rejected and DNS resolution is pinned per request. No login scraping, JavaScript browser, automatic applications, financial recommendations or background purchases. |
| Work memory | Find selected indexed sources, backup/restore receipts and completed jobs. Explicit `screen_remember` takes one screenshot after native confirmation and OCR-indexes it locally. This is not continuous Screenpipe-style capture. Existing conversation recall stays in `nexa_gmail`. |

Reminders and monitors run only **while Nexa is open**. There is no Windows service or always-on scheduler. Jobs do not silently restart mutations after a crash. Site content, mail, documents and transcripts are untrusted data; their instructions should not be executed.

## Setup

Use Python 3.12 and the project virtual environment. On another PC, rebuild `.venv`; never copy an environment from a different Python version.

```powershell
cd "C:\NexaAI"
.\setup_life_tools.cmd
.\start_nexa.cmd
```

Light adapters are in `requirements-life.txt`. Optional local inference dependencies are in `requirements-life-models.txt`; they are not imported at app startup. Translation model files are in `memory/life_data/translation_models`; the UI can import an official `.argosmodel` or download Bengali ↔ English models (about 140 MB). Existing model folders are not overwritten.

### OCR engine — still needs setup on this PC

The Windows Tesseract installer was cancelled, so real OCR is not yet operational here. Install **UB Mannheim Tesseract OCR** and English plus Bengali trained data. Default engine paths include `C:\Program Files\Tesseract-OCR\tesseract.exe` and the per-user Programs folder. `tesseract --list-langs` must include `eng` and `ben`. If needed, get `ben.traineddata` from the official [Tesseract tessdata_fast repository](https://github.com/tesseract-ocr/tessdata_fast) and place it in that installation's `tessdata` directory. The UI/package check distinguishes the Python wrapper from the actual OCR engine.

### Spotify

Create an application in the [Spotify developer dashboard](https://developer.spotify.com/dashboard), register **http://127.0.0.1:8888/callback**, then enter client ID/secret only in **কাজ ও ডকুমেন্ট → সংযোগ** and connect. Never paste secrets in chat. Spotify development-mode eligibility, permitted users and Premium requirements apply. Playback requests report API acceptance, not a claim that sound was heard.

### Calendar

Enable Google Calendar API in the same Google Cloud project as the Desktop OAuth JSON already imported through Gmail setup. Add the intended Google account to test users if the project is in testing. Click **Google Calendar কানেক্ট** and grant Calendar access in the browser. Token is separate from Gmail. Give explicit timezone-aware dates, for example `2026-10-28T10:00:00+06:00`. Calendar creation displays a native approval; testing did not create real events.

### Meeting audio

In **অফলাইন মডেল**, explicitly download **Whisper small** (about 500 MB). Then choose a meeting audio file. Transcription refuses surprise downloads and currently accepts supported audio/video up to the selected-file 50 MB limit and one hour. Pass the transcript to meeting analysis, review the extracted quotes and accept the tasks. No meeting audio or transcript was captured from this user for testing.

## Example chat requests

- “এই PDF-টা পড়ো এবং আমার আর্কাইভে রাখো।”
- “আমার ডকুমেন্টে scholarship deadline কোথায় আছে? পৃষ্ঠা ও প্রমাণ দেখাও।”
- “এই Excel-এর Sheet1 থেকে A1:F30 পড়ো।”
- “এই ফোল্ডারের ব্যাকআপ এই আলাদা ফোল্ডারে রাখো, তারপর যাচাই করো।”
- “এই লেখাটা অফলাইনে ইংরেজি থেকে বাংলায় অনুবাদ করো।”
- “কাল সকাল দশটা থেকে এগারোটা মিটিং Calendar-এ যোগ করো।”
- “আমি আলীকে রিপোর্ট দেব বলেছি—কাল সকাল দশটায় ফলো-আপ রেখো।”
- “এই মিটিং transcript থেকে কার কী কাজ আছে আগে দেখাও।”
- “এই scholarship পাতায় deadline-সংক্রান্ত পরিবর্তন হলে জানিও।”
- “এই ডকুমেন্টটা আগে কোথায় দেখেছিলাম, স্মৃতিতে খুঁজে দাও।”

## Excel MCP server (optional, external MCP clients)

The native Nexa tool uses the adapter directly; it does not need an MCP client running. A standalone stdio server is included for compatible external clients. Configure its executable to the absolute `.venv\Scripts\python.exe`, arguments to the absolute `excel_mcp_server.py`, and environment `NEXA_EXCEL_ROOTS` to explicitly allowed folders separated by `;` on Windows. Without this setting all reads are denied. Do not grant entire drives unless intended.

```json
{
  "mcpServers": {
    "nexa-excel-readonly": {
      "command": "C:\\NexaAI\\.venv\\Scripts\\python.exe",
      "args": ["C:\\NexaAI\\excel_mcp_server.py"],
      "env": {"NEXA_EXCEL_ROOTS": "C:\\Users\\YourName\\Documents\\Spreadsheets"}
    }
  }
}
```

## Validation and current limits

- 56 automated regression tests passed, including 17 new life-tool tests. Real MCP stdio handshake, tool listing, workbook read and denied outside-root read passed.
- Synthetic image-only PDF rendering/OCR dispatch passed with a mocked recognizer; **actual Tesseract recognition is not live-tested** because engine installation was cancelled.
- Bengali→English and English→Bengali model inference passed with synthetic text and socket network connections blocked (`tests/verify_offline_translation.py`).
- Native Qt panel rendered and Bengali fonts visually checked. Plugin discovery and Gemini declaration validation passed. `pip check` reported no broken requirements.
- Spotify and Calendar behavior tested with mocks; real OAuth/playback/event creation still require user setup. Meeting task extraction tested with synthetic AI responses and quote verification; audio recognition requires the optional model.
- Existing YouTube shortcut, synthetic screen recorder output, annotation, notification reader mocks, Discord approval and MAGI mock tests pass. This does not mean Discord messages were sent, real notifications were read, or all screen-recording formats/audio codecs are installed. See COMMUNITY-PLUGINS.md.
- This is a small native implementation of selected workflows, not an installation of Temporal, Graphiti, Screenpipe, Paperless or a community plugin claiming compatibility without adaptation.

Backup before these changes: `..\backups\before-life-tools-20261027-204336.zip`; SHA256 `9655820e3636372eb40196c8dfad3a1dde0a1b91d7817994112b020e4d3db838`. Contains private configuration; keep local. Source backup excludes `.venv` and runtime. Current source plus setup/model dependencies must be kept together when moving PCs.

Local private state: `memory/life.sqlite3`, `memory/life_data/`, `config/life_connectors.json`, `config/spotify_token.json`, `config/calendar_token.json`. These are ignored by Git and are not encrypted at rest. Keep them private and use a separate source-only copy when sharing the project.

Primary references: [Spotify playback API](https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback), [Google Calendar Python quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python), [official Argos model directory](https://data.argosopentech.com/argospm/v1/), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

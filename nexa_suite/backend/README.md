# Nexa AI Backend

## Optional Feature Configuration

Advanced YouTube control uses Selenium with an installed Google Chrome. It is
permission-gated through `youtube_skill` and `youtube_control`; every player
command must come from a confirmed chat action or an explicit control-panel
click.

AI image generation is disabled by default. To enable it, set these values in
`backend/.env`, then enable **AI Image Generation** in Security Center:

```env
HUGGINGFACE_API_KEY=your_token_here
HUGGINGFACE_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell
```

Generated images are stored only under `backend/data/generated_images` and
served through safe opaque IDs. Windows volume/whitelisted app-close controls
are also disabled by default and never allow arbitrary process names.

Online Edge neural TTS is enabled for the voice workflow and remains
permission-gated (`edge_tts`). Other optional extensions remain disabled by
default: safe Markdown/TXT content export (`content_export`) and image
generation (`image_generation`). Audit statistics/export and reminder
editing remain local. Search uses the configured provider first and retains
free DuckDuckGo/Wikipedia fallbacks.

The Nexa AI backend is a local FastAPI service for the desktop frontend. It exposes health checks, permissions, safe action execution, voice/STT/TTS status, web answers, real safe chat, document preview, reminders, audit events, and database readiness/status.

The Windows release uses `nexa_backend.spec` to produce a standalone PyInstaller
one-folder executable. Electron owns its lifecycle and supplies writable
`NEXA_DATA_DIR`, `NEXA_MODELS_DIR`, and `NEXA_ENV_FILE` paths under app data.

This backend is no longer only a skeleton, but it is still an MVP foundation. Some routes perform real permission-gated work, while others are preview/status-only.

## Runtime

- Python 3.11+ recommended.
- FastAPI served by Uvicorn.
- Default URL: `http://127.0.0.1:8000`.
- No paid API is required for MVP features; hosted LLM/search providers are optional and configured only through local `.env`.
- Voice STT uses an online recognition service and does not download a local model.

## Windows Setup

From the project root:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\backend"
```

Check Python:

```powershell
python --version
```

If needed:

```powershell
py --version
```

Create a fresh virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the backend:

```powershell
python run_backend.py
```

Open:

```text
http://127.0.0.1:8000/api/health
```

## Troubleshooting

| Problem | Meaning | Fix |
|---|---|---|
| `python` is not recognized | Python is missing from PATH | Install Python 3.11+ and select "Add python.exe to PATH", or use the Python launcher if available. |
| `py` is not recognized | Python launcher is not installed | Install Python from python.org or repair the installation. |
| `.venv\Scripts\python.exe` references an old path | The virtual environment was moved/copied or its base Python was removed | Recreate `.venv` with the currently installed Python. Do not depend on copied `.venv` folders. |
| `pip` says "Unable to create process" | Pip launcher inside `.venv` points to a missing Python | Use `python -m pip ...` after recreating `.venv`. |
| PowerShell blocks `Activate.ps1` | Execution policy blocks local scripts | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then reopen PowerShell. |
| Frontend says backend offline | FastAPI is not running | Keep `python run_backend.py` open in a backend terminal. |

## Smoke Test

Start the backend first, then run:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\backend"
.\.venv\Scripts\Activate.ps1
python scripts\smoke_test_backend.py
```

The smoke script checks:

- `/api/health`
- `/api/permissions`
- locked permission cannot be enabled
- dangerous commands are blocked even with confirmation
- unknown app and website targets are blocked
- whitelisted dry-run action stays preview-only and does not execute
- audit recent endpoint is available and shows recent action events when recorded

## Pytest Route Tests

Run the in-process route/safety test suite:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\backend"
.\.venv\Scripts\Activate.ps1
python -m pytest
```

These tests cover the same safety-critical route behavior as the smoke script without requiring a running server.

## API Status

| Feature | Status | Notes |
|---|---|---|
| Health | Working / Wired | Used by frontend backend status checks. |
| Command preview | Preview only | No broad command execution engine yet. |
| Safe website/app open | Working / Wired | Whitelist plus confirmation; unknown targets blocked. |
| File search | Working / Wired | Read-only metadata search in safe folders. |
| Document preview | Working / Wired | Read-only PDF/TXT/MD text preview. |
| Permissions | Working / Wired | Toggleable safe features, locked dangerous features. |
| Voice STT | Backend + internet required | Online Bangla push-to-talk; no local model. |
| TTS | Backend + internet required | Edge neural Bangla/English voice, permission-gated. |
| Web answers | Working / Wired | DuckDuckGo/Wikipedia style safe-source answers. |
| Chat | Working / Wired | `/api/chat/message` detects weather, web search, normal chat, action previews, and dangerous requests. |
| Smart task router | Working / Wired | Routes local persona, weather/time, search, LLM, YouTube, WhatsApp drafts, contacts, calculator, and safety blocks. |
| Hosted LLM router | Optional / Wired | Gemini primary with Groq/OpenRouter/Cloudflare/Mistral/Cerebras fallback when local keys are configured. |
| Reminders | Working / Wired | Local reminder records. |
| Audit events | Working / Wired | Recent action events endpoint plus preview audit route. |
| Database | Preview/status only | Readiness/status; not full memory system. |
| AI Chat | Working / Wired | Weather uses Open-Meteo; web answers reuse safe public answer logic; chat never executes actions. |
| Workflow automation | Missing / Future | No workflow executor. |
| WhatsApp drafts | Working / Wired | Local contacts, aliases, relationship/tone, safe `wa.me` draft URLs only. Nexa never clicks Send. |
| Email automation | Missing / Future | Not implemented. |

## Optional Providers

Copy `.env.example` to `.env` and set only local keys you want to use. Do not commit real keys.

```env
NEXA_SEARCH_PROVIDER=serper
SERPER_API_KEY=your_serper_api_key_here

NEXA_LLM_ROUTER_ENABLED=true
NEXA_LLM_PRIMARY=gemini
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=
OPENROUTER_API_KEY=
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
MISTRAL_API_KEY=
CEREBRAS_API_KEY=
```

Weather and time never need LLM. Live/current data uses search first; LLM may only summarize source data.

## WhatsApp Contacts

Local WhatsApp contacts are stored under backend local data and support:

- `name`
- `phone_number`
- `aliases`
- `relationship`: `boss`, `client`, `friend`, `family`, or `unknown`
- `default_tone`: `formal`, `friendly`, or `normal`

Trusted WhatsApp draft auto-open may open `https://wa.me/<phone>?text=<draft>`, but Nexa never clicks Send or reads chats.
| Smart home | Future | Not implemented. |

## Safety Rules

- Unknown apps and websites are blocked.
- Dangerous text such as delete, format, shutdown, registry, system32, cmd, and powershell is blocked by backend safety checks.
- File write operations are intentionally not implemented.
- TTS and other capabilities can be disabled through backend permissions.
- Messages are not auto-sent.
- WhatsApp messages are draft-only; the user manually presses Send.
- The microphone flow is push-to-talk, not always-on.

## Useful Commands

```powershell
# Import/bytecode compile check
python -m compileall app scripts

# Run backend
python run_backend.py

# Smoke-test a running backend
python scripts\smoke_test_backend.py
```

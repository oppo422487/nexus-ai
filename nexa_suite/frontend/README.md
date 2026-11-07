# Nexa AI Frontend

The Nexa AI frontend is a React/Electron/Vite desktop UI. It talks to the FastAPI backend at `http://127.0.0.1:8000` for backend-backed features. It is beyond the original skeleton phase, but not every screen is fully wired.

## Stack

- React 19
- Vite
- TypeScript
- Electron shell
- Framer Motion
- Lucide React
- Custom dark assistant UI styles

## Setup on Windows

From the frontend folder:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\frontend"
npm.cmd install
```

Use `npm.cmd` in PowerShell if plain `npm` is blocked by script execution policy.

## Run

Start the backend first in another terminal:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\backend"
.\.venv\Scripts\Activate.ps1
python run_backend.py
```

Then start the desktop frontend:

```powershell
cd "C:\Users\Abdur Rahman\Desktop\nexaai\nexaai\nexaai\frontend"
npm.cmd run dev
```

For browser-only frontend development:

```powershell
npm.cmd run web:dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

Backend URL expected by the UI:

```text
http://127.0.0.1:8000
```

## Checks

```powershell
npm.cmd run test
npm.cmd run build
```

`npm.cmd run test` currently runs the TypeScript project check (`tsc -b`). It is a real automated check, but it is not a full unit or browser test suite yet.

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| Dashboard command center | Working / Wired, Backend required | Routes whitelisted launch commands through backend confirmation. |
| Launcher | Working / Wired, Backend required | Opens only backend-whitelisted apps/websites. |
| Web answers | Working / Wired, Backend required | Calls backend safe answer endpoint. |
| Files/document preview | Working / Wired, Backend required | Read-only search and preview only. |
| Reminders | Working / Wired, Backend required | Local backend reminders. |
| Permissions/security center | Working / Wired, Backend required | Uses backend permission endpoints. |
| Voice STT | Backend + internet required | Push-to-talk calls online Bangla STT; no local model is needed. |
| TTS | Backend required | Calls backend TTS status/speak endpoint; permission-gated. |
| Audit/history | Working / Wired, Backend required | Shows local preview history and backend audit events. |
| AI Chat / Dashboard assistant | Working / Wired, Backend required | Smart router with local persona, weather/time, search, optional LLM, safe YouTube actions, WhatsApp draft composer, and blocked dangerous commands. |
| LLM provider chips | Working / Wired, Backend required | Shows provider chip only for LLM-backed answers. Local conversation stays clean. |
| WhatsApp contacts | Working / Wired, Backend required | Settings form supports name, phone, aliases, relationship, and default tone. |
| Automation workflow templates | Preview only | Templates do not execute workflows. |
| Profile settings | Working / Wired locally | Stored in local browser storage; no backend profile route. |
| Windows packaging | Working / Standalone | Bundles Electron plus the PyInstaller backend and manages backend start/stop automatically. |

## Honest Limitations

- Backend-backed pages show errors or offline state unless FastAPI is running.
- Hosted LLM providers are optional and require user-provided backend `.env` keys.
- Search/live data quality depends on configured backend search provider. Serper is optional.
- YouTube trusted open/search and WhatsApp trusted draft auto-open are backend permission settings.
- WhatsApp is draft-only. Nexa never clicks Send, reads chats, or sends silently.
- Workflow automation templates are preview-only.
- Profile settings are local-only.
- File write operations are intentionally disabled.
- Public releases should still be code-signed to reduce Windows SmartScreen warnings.
- Voice STT requires internet access and working microphone permissions.

## Troubleshooting

| Problem | Fix |
|---|---|
| `npm` is blocked by PowerShell | Use `npm.cmd` commands. |
| Frontend says backend offline | Start `python run_backend.py` in the backend folder. |
| Electron window does not launch | Run `npm.cmd run web:dev` first to confirm Vite works, then retry `npm.cmd run dev`. |
| Build fails after dependency changes | Run `npm.cmd install`, then `npm.cmd run build`. |
| Voice features fail | Confirm backend is running, permissions are enabled, microphone access is allowed, and internet works. |

# Nexa AI — Frontend Page Plan

| Page | Purpose | Priority | Expected Backend Dependency |
|---|---|---|---|
| Splash Loading | Show startup progress while checking local backend readiness | MVP | `/api/health`, backend status events |
| Welcome Onboarding | Introduce Nexa AI and first-run flow | MVP | profile state check |
| Profile Setup | Collect name, language, and addressing preferences | MVP | `/api/profile` |
| Voice & Permissions | Guide microphone setup and permission education | MVP | `/api/voice`, permission state |
| Main Dashboard | Show assistant status, reminders, activity, and quick actions | MVP | profile, reminders, command logs, backend status |
| Command Understanding | Display transcript, recognized intent, and clarifications | MVP | `/api/commands`, WebSocket command events |
| App & Website Launcher | Manage and trigger saved apps and websites | MVP | `/api/apps` |
| System Control | Expose supported Windows controls and confirmation dialogs | MVP | `/api/system`, `/api/security` |
| YouTube & Browser Automation | Trigger searches and supported media/browser controls | MVP | `/api/commands`, browser automation services |
| Web Intelligence | Show weather, news, dictionary, and web lookup results | MVP | `/api/web` |
| AI Chat | Provide conversational assistant interactions | V2 | conversation endpoints and command engine |
| Contacts & Drafts | Manage contacts and generate WhatsApp/email drafts | MVP | `/api/contacts`, draft services |
| File Organizer | Search, inspect, and organize local files safely | MVP | `/api/files`, `/api/security` |
| PDF & Documents | Summarize and search supported documents | MVP | document services |
| Reminders & Study | Manage reminders, tasks, and study support | MVP | `/api/reminders`, task services |
| Automation Builder | Create and run reusable workflows | V2 | automation workflow endpoints |
| Security & Permissions | Review action permissions and sensitive history | MVP | `/api/security` |
| Settings | Manage application preferences and feature flags | MVP | profile/preferences endpoints |

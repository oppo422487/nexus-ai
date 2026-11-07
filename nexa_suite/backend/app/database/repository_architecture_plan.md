# Local Database Repository Architecture Plan

## 1. Purpose

This document plans future repository architecture for local database storage on the Nexa AI backend. Phase 22.3 is documentation only — no repository connects to the database, no reads or writes occur, and no storage is enabled.

## 2. Repository Layers

| Layer | Responsibility |
|---|---|
| **Config layer** | Define database path, feature flags, and mode (disabled by default) |
| **Connection layer** | Manage SQLite connection lifecycle and connection pooling |
| **Migration layer** | Track and apply schema migrations via the `schema_migrations` registry |
| **Repository layer** | Provide CRUD operations for each domain entity |
| **Service layer** | Enforce business logic, feature flags, and safety rules before calling repositories |
| **API route layer** | Expose endpoints that call services and return typed responses |

## 3. Planned Repositories

### AuditLogRepository
| Method | Description |
|---|---|
| `insert_audit_log()` | Persist a new audit record |
| `list_audit_logs()` | Retrieve paginated audit records with optional filters |
| `get_audit_log_by_id()` | Fetch a single audit record by its ID |
| `delete_audit_log()` | Remove a single audit record by ID |
| `clear_audit_logs()` | Remove all audit records |

### UserProfileRepository
| Method | Description |
|---|---|
| `save_profile()` | Persist or update the user profile |
| `load_profile()` | Retrieve the stored user profile |
| `update_onboarding_status()` | Update whether onboarding has been completed |
| `update_language_voice_preferences()` | Update language mode and voice settings |

### CommandHistoryRepository
| Method | Description |
|---|---|
| `save_command_preview()` | Persist a command preview/audit entry |
| `list_command_history()` | Retrieve paginated command history |
| `search_command_history()` | Full-text or pattern search across history fields |
| `filter_by_risk_source_status()` | Filter history by risk level, source, or action status |
| `delete_command_history_entry()` | Remove a single history entry by ID |

### SettingsRepository
| Method | Description |
|---|---|
| `save_settings()` | Persist application settings |
| `load_settings()` | Retrieve all stored settings |
| `reset_settings()` | Restore settings to defaults |

## 4. Safety Rules

- Repositories must not execute OS commands.
- Repositories must not launch apps or websites.
- Repositories must not send messages or emails.
- Repositories must only store metadata — never executable payloads.
- Sensitive and blocked command records must remain audit-only and must never be replayed as executable commands.
- Real command execution must be handled by a separate future execution layer that includes explicit user confirmation, not by any repository.

## 5. Repository Interface Pattern

All repositories should follow a consistent method style:

| Method | Signature Pattern |
|---|---|
| `create()` | `(data: CreateModel) -> ResultModel` |
| `get_by_id()` | `(id: str) -> ResultModel \| None` |
| `list()` | `(filters: dict, limit: int, offset: int) -> list[ResultModel]` |
| `update()` | `(id: str, data: UpdateModel) -> ResultModel \| None` |
| `delete()` | `(id: str) -> bool` |
| `clear()` | `() -> bool` |

Design principles:
- All methods should return typed results.
- Errors should be handled safely (no unhandled exceptions escaping the repository layer).
- Storage feature flags (`writes_enabled`, `reads_enabled`) must be checked before any operation.
- If storage is disabled, methods should return a safe disabled response instead of raising.

## 6. Current Phase Status

- Phase 22.3 creates only this architecture plan document.
- No database connection has been made.
- No repository implementation is active.
- No SQL has been executed.
- No storage is enabled.
- `LocalDatabaseConfig` has all feature flags set to `False`.

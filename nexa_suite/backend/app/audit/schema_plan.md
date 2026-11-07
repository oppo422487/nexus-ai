# Audit Storage Schema Plan

## 1. Purpose

This plan defines future audit log storage for the Nexa AI backend. Storage is disabled in Phase 19 — no database writes, no file writes, no command execution occurs. Only preview and audit metadata will be persisted in a future phase once storage is enabled.

## 2. Table Name

```
audit_logs
```

## 3. Proposed Columns

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | Unique audit record identifier |
| `source` | TEXT | NOT NULL | Origin of the audit entry (e.g. `commands_page`, `voice_page`, `backend_preview`, `manual_test`) |
| `original_text` | TEXT | NOT NULL | The raw command text as received |
| `intent` | TEXT | NOT NULL | Detected intent label |
| `language` | TEXT | NOT NULL | Language code or label |
| `confidence` | INTEGER | NOT NULL DEFAULT 0 | Confidence score (0-100) |
| `risk_level` | TEXT | NOT NULL | Risk classification (safe, confirmation_required, sensitive, blocked) |
| `action_status` | TEXT | NULL | Frontend action preview status |
| `backend_status` | TEXT | NULL | Backend preview status |
| `can_execute` | INTEGER | NOT NULL DEFAULT 0 | Must remain 0 (false) until real execution phase |
| `summary` | TEXT | NOT NULL | Human-readable summary of the audit entry |
| `created_at` | TEXT | NOT NULL | Timestamp from the frontend when the entry was created |
| `stored_at` | TEXT | NOT NULL | Timestamp when the record was written to the database |

## 4. Safety Rules

- No OS commands shall be stored as executable jobs.
- No command shall be executed from audit records.
- `can_execute` must remain false until an explicit future execution phase authorizes it.
- Sensitive and blocked commands must remain traceable for safety review.
- Delete, send, move, shutdown, and browser automation actions must require explicit confirmation in future phases before any execution is permitted.

## 5. Future Indexes

| Index Name | Column(s) | Purpose |
|---|---|---|
| `idx_audit_logs_created_at` | `created_at` | Fast time-range queries and sorting |
| `idx_audit_logs_source` | `source` | Filter by source origin |
| `idx_audit_logs_risk_level` | `risk_level` | Filter by risk classification |
| `idx_audit_logs_intent` | `intent` | Filter by intent type |

## 6. Future Repository Methods

| Method | Description |
|---|---|
| `insert_audit_log()` | Insert a new audit record into the `audit_logs` table |
| `list_audit_logs()` | Retrieve paginated audit records with optional filters |
| `get_audit_log_by_id()` | Fetch a single audit record by its `id` |
| `delete_audit_log()` | Remove a single audit record by `id` |
| `clear_audit_logs()` | Remove all audit records |
| `search_audit_logs()` | Full-text or pattern search across audit fields |

## 7. Current Phase Status

- Phase 19.2 only creates this schema plan document.
- No database migration has been written or run.
- No table has been created.
- No persistence is enabled.
- `AuditRepository` remains storage-disabled — `save_preview()` returns a no-op response.
- Storage will be enabled in a future phase after the database connection layer is ready.

# Local Database Migration Registry Plan

## 1. Purpose

This document plans future local database migration tracking for the Nexa AI backend. Phase 22.2 is documentation only — no migration will run, no database file will be created, and no storage will be enabled.

## 2. Migration Registry Table

**Future table name:** `schema_migrations`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | PRIMARY KEY |
| `migration_name` | TEXT | NOT NULL — human-readable name |
| `migration_version` | TEXT | NOT NULL — version string for ordering |
| `applied_at` | TEXT | NOT NULL — timestamp when migration was applied |
| `checksum` | TEXT | NULL — optional file hash for integrity verification |
| `success` | INTEGER | NOT NULL DEFAULT 0 — 1 if migration succeeded |
| `notes` | TEXT | NULL — optional log or error details |

## 3. Planned Migration Files

| File | Purpose |
|---|---|
| `001_create_audit_logs.sql` | Create the `audit_logs` table for command/voice audit records |
| `002_create_user_profile.sql` | Create the `user_profile` table for persistent user settings |
| `003_create_command_history.sql` | Create the `command_history` table for full command history |
| `004_create_settings.sql` | Create the `settings` table for application configuration |

## 4. Safety Rules

- Migrations must be disabled by default in all phases unless explicitly enabled.
- Migrations must never run automatically without explicit future phase approval.
- Migration preview must execute and pass verification before any migration is applied.
- Failed migrations must not be partially trusted — rollback or explicit repair must be required.
- No command execution should depend on migration state until storage is explicitly enabled and verified.

## 5. Future Migration Registry API

| Function | Description |
|---|---|
| `list_available_migrations()` | List all SQL migration files available in the migration directory |
| `preview_migration()` | Preview what a specific migration would do (read-only) |
| `apply_migration()` | Execute a specific migration against the database |
| `get_applied_migrations()` | Retrieve the list of already-applied migrations from `schema_migrations` |
| `mark_migration_applied()` | Record a migration as applied in the registry table |
| `verify_migration_checksum()` | Compare a migration file's checksum against the stored value |

## 6. Current Phase Status

- Phase 22.2 creates only this plan document.
- No database connection has been made.
- No SQL has been executed.
- No table has been created.
- No storage is enabled.
- `LocalDatabaseConfig` has all feature flags set to `False`.

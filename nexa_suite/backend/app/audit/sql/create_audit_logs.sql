-- =============================================================================
-- Audit Logs Table — SQLite DDL
-- Phase 20.1 does NOT execute this script.  It is prepared for future use.
-- can_execute must remain 0 (false) until an explicit future execution phase
-- authorizes real command execution.
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT    PRIMARY KEY,
    source          TEXT    NOT NULL,
    original_text   TEXT    NOT NULL,
    intent          TEXT    NOT NULL,
    language        TEXT    NOT NULL,
    confidence      INTEGER NOT NULL DEFAULT 0,
    risk_level      TEXT    NOT NULL,
    action_status   TEXT,
    backend_status  TEXT,
    can_execute     INTEGER NOT NULL DEFAULT 0,
    summary         TEXT    NOT NULL,
    created_at      TEXT    NOT NULL,
    stored_at       TEXT    NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_source     ON audit_logs(source);
CREATE INDEX IF NOT EXISTS idx_audit_logs_risk_level ON audit_logs(risk_level);
CREATE INDEX IF NOT EXISTS idx_audit_logs_intent     ON audit_logs(intent);

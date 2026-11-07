import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { AuditEventsPanel } from "@/components/history/AuditEventsPanel";
import { Sidebar } from "@/components/shell/Sidebar";
import { PageHero } from "@/components/ui";
import { BackendAuditHealthResponse, BackendAuditMigrationPreviewResponse, BackendAuditPreviewResponse, CommandHistoryEntry, clearCommandHistory, deleteCommandHistoryEntry, getBackendAuditHealth, getBackendAuditMigrationPreview, getLatestCommandHistory, requestBackendAuditPreview } from "@/lib";

export function HistoryPage() {
  const timeline = [
    {
      time: "Now",
      title: "Desktop app opened",
      text: "Nexa AI Electron shell started successfully.",
      status: "success",
    },
    {
      time: "Phase 06",
      title: "Navigation system active",
      text: "Sidebar pages can switch without reload.",
      status: "success",
    },
    {
      time: "Phase 05",
      title: "Backend health watcher added",
      text: "Desktop UI can detect FastAPI backend state.",
      status: "info",
    },
    {
      time: "Future",
      title: "Command audit logs",
      text: "Voice commands and sensitive actions will be logged here.",
      status: "pending",
    },
  ];

  const [commandHistory, setCommandHistory] = useState<CommandHistoryEntry[]>(() =>
    getLatestCommandHistory(),
  );
  const [sourceFilter, setSourceFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedHistoryEntryId, setSelectedHistoryEntryId] = useState<string | null>(null);
  const [auditPreviewResponse, setAuditPreviewResponse] = useState<BackendAuditPreviewResponse | null>(null);
  const [auditPreviewLoading, setAuditPreviewLoading] = useState(false);
  const [auditPreviewError, setAuditPreviewError] = useState<string | null>(null);
  const [auditHealth, setAuditHealth] = useState<BackendAuditHealthResponse | null>(null);
  const [auditHealthLoading, setAuditHealthLoading] = useState(false);
  const [auditHealthError, setAuditHealthError] = useState<string | null>(null);
  const [migrationPreview, setMigrationPreview] = useState<BackendAuditMigrationPreviewResponse | null>(null);
  const [migrationPreviewLoading, setMigrationPreviewLoading] = useState(false);
  const [migrationPreviewError, setMigrationPreviewError] = useState<string | null>(null);

  useEffect(() => {
    handleRefreshAuditHealth();
    handleRefreshMigrationPreview();
  }, []);

  const selectedEntry = selectedHistoryEntryId
    ? commandHistory.find((e) => e.id === selectedHistoryEntryId) ?? null
    : null;

  const filteredHistory = commandHistory.filter((entry) => {
    if (sourceFilter !== "all" && entry.source !== sourceFilter) return false;
    if (riskFilter !== "all" && entry.riskLevel !== riskFilter) return false;
    if (statusFilter !== "all") {
      const entryStatus = entry.actionStatus ?? entry.backendStatus;
      if (entryStatus !== statusFilter) return false;
    }
    const query = searchQuery.trim().toLowerCase();
    if (query) {
      const haystack = [
        entry.originalText,
        entry.intent,
        entry.language,
        entry.riskLevel,
        entry.source,
        entry.actionStatus,
        entry.backendStatus,
        entry.summary,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });

  const hasHistory = commandHistory.length > 0;
  const hasFiltered = filteredHistory.length > 0;
  const totalCount = commandHistory.length;
  const shownCount = filteredHistory.length;

  const handleRefreshHistory = () => {
    setCommandHistory(getLatestCommandHistory());
  };

  const clearFilters = () => {
    setSourceFilter("all");
    setRiskFilter("all");
    setStatusFilter("all");
  };

  const clearAll = () => {
    clearFilters();
    setSearchQuery("");
  };

  const handleClearHistory = () => {
    clearCommandHistory();
    setCommandHistory([]);
    setSelectedHistoryEntryId(null);
  };

  const handleSelectEntry = (id: string) => {
    setSelectedHistoryEntryId((prev) => (prev === id ? null : id));
  };

  const handleCloseDetail = () => {
    setSelectedHistoryEntryId(null);
  };

  const handleDeleteHistoryEntry = (id: string) => {
    const updated = deleteCommandHistoryEntry(id);
    setCommandHistory(updated);
    if (selectedHistoryEntryId === id) {
      setSelectedHistoryEntryId(null);
    }
  };

  const handleRefreshMigrationPreview = async () => {
    setMigrationPreviewLoading(true);
    setMigrationPreviewError(null);
    try {
      const response = await getBackendAuditMigrationPreview();
      setMigrationPreview(response);
    } catch (err) {
      setMigrationPreviewError(err instanceof Error ? err.message : "Failed to reach backend migration preview.");
    } finally {
      setMigrationPreviewLoading(false);
    }
  };

  const handleRefreshAuditHealth = async () => {
    setAuditHealthLoading(true);
    setAuditHealthError(null);
    try {
      const response = await getBackendAuditHealth();
      setAuditHealth(response);
    } catch (err) {
      setAuditHealthError(err instanceof Error ? err.message : "Failed to reach backend audit health.");
    } finally {
      setAuditHealthLoading(false);
    }
  };

  const handleSyncHistoryEntryToAudit = async (entry: CommandHistoryEntry) => {
    setAuditPreviewLoading(true);
    setAuditPreviewError(null);
    setAuditPreviewResponse(null);
    try {
      const response = await requestBackendAuditPreview(entry);
      setAuditPreviewResponse(response);
    } catch (err) {
      setAuditPreviewError(err instanceof Error ? err.message : "Failed to sync with backend audit.");
    } finally {
      setAuditPreviewLoading(false);
    }
  };

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <section className="page-surface system-page">
      <PageHero
        icon={<Clock />}
        eyebrow="Activity & Audit"
        title="History Center"
        description="Command history, automation events, safety confirmations, and assistant activity logs."
      />

      <div className="timeline-panel">
        {timeline.map((item) => (
          <div className="timeline-item" key={item.title}>
            <div className={`timeline-dot ${item.status}`} />
            <div>
              <span>{item.time}</span>
              <h4>{item.title}</h4>
              <p>{item.text}</p>
            </div>
          </div>
        ))}
      </div>

      <AuditEventsPanel />

      <div className="audit-health-panel">
        <div className="audit-health-header">
          <p className="eyebrow">Backend Audit Storage Status</p>
          <button
            type="button"
            className="audit-health-button"
            onClick={handleRefreshAuditHealth}
            disabled={auditHealthLoading}
          >
            {auditHealthLoading ? "Refreshing..." : "Refresh Audit Status"}
          </button>
        </div>
        {auditHealthError && (
          <div className="audit-health-error">{auditHealthError}</div>
        )}
        {auditHealth && (
          <>
            <div className="audit-health-grid">
              <div className="audit-health-row">
                <span>Status</span>
                <strong>{auditHealth.status}</strong>
              </div>
              <div className="audit-health-row">
                <span>Module</span>
                <strong>{auditHealth.module}</strong>
              </div>
              <div className="audit-health-row">
                <span>Phase</span>
                <strong>{auditHealth.phase}</strong>
              </div>
              <div className="audit-health-row">
                <span>Storage enabled</span>
                <strong>{String(auditHealth.storage_enabled)}</strong>
              </div>
              <div className="audit-health-row">
                <span>Storage mode</span>
                <strong>{auditHealth.storage_mode ?? "N/A"}</strong>
              </div>
              <div className="audit-health-row">
                <span>Execution enabled</span>
                <strong>{String(auditHealth.execution_enabled)}</strong>
              </div>
              {auditHealth.message && (
                <div className="audit-health-row full-width">
                  <span>Message</span>
                  <strong>{auditHealth.message}</strong>
                </div>
              )}
            </div>
            <div className="audit-health-note">
              Storage is not enabled yet. This panel only displays backend audit status.
            </div>
          </>
        )}
        {!auditHealth && !auditHealthError && !auditHealthLoading && (
          <div className="audit-health-empty">Click "Refresh Audit Status" to load backend audit status.</div>
        )}
      </div>

      <div className="migration-preview-panel">
        <div className="migration-preview-header">
          <p className="eyebrow">SQLite Migration Preview</p>
          <button
            type="button"
            className="migration-preview-button"
            onClick={handleRefreshMigrationPreview}
            disabled={migrationPreviewLoading}
          >
            {migrationPreviewLoading ? "Refreshing..." : "Refresh Migration Preview"}
          </button>
        </div>
        {migrationPreviewError && (
          <div className="migration-preview-error">{migrationPreviewError}</div>
        )}
        {migrationPreview && (
          <>
            <div className="migration-preview-grid">
              <div className="migration-preview-row">
                <span>Status</span>
                <strong>{migrationPreview.status}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Script path</span>
                <strong>{migrationPreview.script_path}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Exists</span>
                <strong>{String(migrationPreview.exists)}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Can run</span>
                <strong>{String(migrationPreview.can_run)}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Migrations enabled</span>
                <strong>{String(migrationPreview.migrations_enabled)}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Statement count</span>
                <strong>{migrationPreview.statement_count}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Table name</span>
                <strong>{migrationPreview.table_name}</strong>
              </div>
              <div className="migration-preview-row">
                <span>Execution enabled</span>
                <strong>{String(migrationPreview.execution_enabled)}</strong>
              </div>
              <div className="migration-preview-row full-width">
                <span>Message</span>
                <strong>{migrationPreview.preview_message}</strong>
              </div>
            </div>
            <div className="migration-preview-notes">
              {migrationPreview.safety_notes.map((note, i) => (
                <div key={i} className="migration-preview-note">{note}</div>
              ))}
            </div>
          </>
        )}
        {!migrationPreview && !migrationPreviewError && !migrationPreviewLoading && (
          <div className="migration-preview-empty">Click "Refresh Migration Preview" to load migration status.</div>
        )}
      </div>

      <div className="command-history-panel">
        <div className="command-history-header">
          <p className="eyebrow">Command Audit Log</p>
          <div className="command-history-actions">
            <button
              type="button"
              className="command-history-button"
              onClick={handleRefreshHistory}
            >
              Refresh History
            </button>
            <button
              type="button"
              className="command-history-button danger"
              onClick={handleClearHistory}
            >
              Clear Command History
            </button>
          </div>
        </div>

        <div className="database-readiness-note">
          <p className="eyebrow">Database Readiness Note</p>
          <p className="database-readiness-desc">
            Current command history is stored locally in browser/Electron localStorage.
            Backend SQLite database storage is prepared but disabled.
            Audit sync endpoint is preview-only and does not store to database.
            No command execution is connected to history records.
          </p>
          <div className="database-readiness-grid">
            <div className="database-readiness-item enabled">
              <span>Local history</span>
              <strong>Enabled</strong>
            </div>
            <div className="database-readiness-item enabled">
              <span>Backend audit preview</span>
              <strong>Enabled</strong>
            </div>
            <div className="database-readiness-item disabled">
              <span>SQLite storage</span>
              <strong>Disabled</strong>
            </div>
            <div className="database-readiness-item disabled">
              <span>Migrations</span>
              <strong>Disabled</strong>
            </div>
            <div className="database-readiness-item disabled">
              <span>Command execution</span>
              <strong>Disabled</strong>
            </div>
          </div>
        </div>

        {!hasHistory ? (
          <div className="command-history-empty">
            No command history saved yet.
          </div>
        ) : (
          <>
            <div className="command-history-search-row">
              <input
                className="command-history-search-input"
                type="text"
                placeholder="Search command history..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="command-history-search-clear"
                  onClick={() => setSearchQuery("")}
                >
                  Clear Search
                </button>
              )}
              <button
                type="button"
                className="command-history-clear-all"
                onClick={clearAll}
              >
                Clear All
              </button>
            </div>
            <div className="command-history-result-count">
              Showing {shownCount} of {totalCount} history entries
            </div>
            <div className="command-history-filter-bar">
              <div className="command-history-filter-group">
                <label>Source</label>
                <select
                  className="command-history-select"
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                >
                  <option value="all">All sources</option>
                  <option value="commands_page">Commands Page</option>
                  <option value="voice_page">Voice Page</option>
                  <option value="backend_preview">Backend Preview</option>
                  <option value="manual_test">Manual Test</option>
                </select>
              </div>
              <div className="command-history-filter-group">
                <label>Risk</label>
                <select
                  className="command-history-select"
                  value={riskFilter}
                  onChange={(e) => setRiskFilter(e.target.value)}
                >
                  <option value="all">All risks</option>
                  <option value="safe">Safe</option>
                  <option value="confirmation_required">Confirmation Required</option>
                  <option value="sensitive">Sensitive</option>
                  <option value="blocked">Blocked</option>
                </select>
              </div>
              <div className="command-history-filter-group">
                <label>Status</label>
                <select
                  className="command-history-select"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All statuses</option>
                  <option value="preview_only">Preview Only</option>
                  <option value="requires_confirmation">Requires Confirmation</option>
                  <option value="sensitive_warning">Sensitive Warning</option>
                  <option value="blocked">Blocked</option>
                  <option value="confirmation_required">Confirmation Required</option>
                  <option value="warning">Warning</option>
                  <option value="preview">Preview</option>
                </select>
              </div>
              <button
                type="button"
                className="command-history-clear-filter"
                onClick={clearFilters}
              >
                Clear Filters
              </button>
            </div>

            {!hasFiltered ? (
              <div className="command-history-empty">
                No history entries match your search or filters.
              </div>
            ) : (
              <div className="command-history-list">
                {filteredHistory.map((entry) => (
              <div
                className={`command-history-item${selectedHistoryEntryId === entry.id ? " active" : ""}`}
                key={entry.id}
                onClick={() => handleSelectEntry(entry.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleSelectEntry(entry.id); }}
              >
                <div className="command-history-meta">
                  <div>
                    <span>Source</span>
                    <strong>{entry.source}</strong>
                  </div>
                  <div>
                    <span>Time</span>
                    <strong>{formatTime(entry.createdAt)}</strong>
                  </div>
                  <div>
                    <span>Intent</span>
                    <strong>{entry.intent}</strong>
                  </div>
                  <div>
                    <span>Language</span>
                    <strong>{entry.language}</strong>
                  </div>
                  <div>
                    <span>Confidence</span>
                    <strong>{entry.confidence}%</strong>
                  </div>
                  <div className="command-history-risk">
                    <span>Risk level</span>
                    <strong>{entry.riskLevel}</strong>
                  </div>
                  <div>
                    <span>Can execute</span>
                    <strong>No</strong>
                  </div>
                  {entry.actionStatus && (
                    <div>
                      <span>Action status</span>
                      <strong>{entry.actionStatus}</strong>
                    </div>
                  )}
                  {entry.backendStatus && (
                    <div>
                      <span>Backend status</span>
                      <strong>{entry.backendStatus}</strong>
                    </div>
                  )}
                </div>
                <p className="command-history-command">
                  {entry.originalText}
                </p>
                <p className="command-history-summary">
                  {entry.summary}
                </p>
                <div className="command-history-item-actions">
                  <button
                    type="button"
                    className="audit-sync-button"
                    onClick={(e) => { e.stopPropagation(); handleSyncHistoryEntryToAudit(entry); }}
                    disabled={auditPreviewLoading}
                  >
                    {auditPreviewLoading ? "Syncing..." : "Sync Audit Preview"}
                  </button>
                  <button
                    type="button"
                    className="command-history-delete-button"
                    onClick={(e) => { e.stopPropagation(); handleDeleteHistoryEntry(entry.id); }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedEntry ? (
          <div className="command-history-detail">
            <div className="command-history-detail-header">
              <p className="eyebrow">History Detail</p>
              <button
                type="button"
                className="command-history-close-detail"
                onClick={handleCloseDetail}
              >
                Close Detail
              </button>
            </div>
            <div className="command-history-detail-grid">
              <div className="command-history-detail-row">
                <span>Original command</span>
                <strong>{selectedEntry.originalText}</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Source</span>
                <strong>{selectedEntry.source}</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Intent</span>
                <strong>{selectedEntry.intent}</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Language</span>
                <strong>{selectedEntry.language}</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Confidence</span>
                <strong>{selectedEntry.confidence}%</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Risk level</span>
                <strong>{selectedEntry.riskLevel}</strong>
              </div>
              {selectedEntry.actionStatus && (
                <div className="command-history-detail-row">
                  <span>Action status</span>
                  <strong>{selectedEntry.actionStatus}</strong>
                </div>
              )}
              {selectedEntry.backendStatus && (
                <div className="command-history-detail-row">
                  <span>Backend status</span>
                  <strong>{selectedEntry.backendStatus}</strong>
                </div>
              )}
              <div className="command-history-detail-row">
                <span>Can execute</span>
                <strong>No</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Created at</span>
                <strong>{formatTime(selectedEntry.createdAt)}</strong>
              </div>
              <div className="command-history-detail-row">
                <span>Summary</span>
                <strong>{selectedEntry.summary}</strong>
              </div>
            </div>
            <div className="command-history-safety-note">
              This is a preview/audit record only. No command was executed.
            </div>
            <div className="command-history-danger-note">
              <button
                type="button"
                className="audit-sync-button detail"
                onClick={() => handleSyncHistoryEntryToAudit(selectedEntry)}
                disabled={auditPreviewLoading}
              >
                {auditPreviewLoading ? "Syncing..." : "Sync Selected to Backend Audit"}
              </button>
              <button
                type="button"
                className="command-history-detail-delete"
                onClick={() => handleDeleteHistoryEntry(selectedEntry.id)}
              >
                Delete This Entry
              </button>
            </div>
            {auditPreviewError && (
              <div className="audit-preview-error">{auditPreviewError}</div>
            )}
            {auditPreviewResponse && (
              <div className="audit-preview-panel">
                <p className="eyebrow" style={{ margin: "0 0 10px" }}>Backend Audit Preview</p>
                <div className="audit-preview-grid">
                  <div className="audit-preview-row">
                    <span>Status</span>
                    <strong>{auditPreviewResponse.status}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Audit ID</span>
                    <strong>{auditPreviewResponse.audit_id}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Stored</span>
                    <strong>{String(auditPreviewResponse.stored)}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Execution enabled</span>
                    <strong>{String(auditPreviewResponse.execution_enabled)}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Message</span>
                    <strong>{auditPreviewResponse.message}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Source</span>
                    <strong>{auditPreviewResponse.source}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Intent</span>
                    <strong>{auditPreviewResponse.intent}</strong>
                  </div>
                  <div className="audit-preview-row">
                    <span>Risk level</span>
                    <strong>{auditPreviewResponse.risk_level}</strong>
                  </div>
                </div>
                <div className="audit-preview-note">
                  Backend audit preview does not store to database yet.
                </div>
              </div>
            )}
          </div>
        ) : hasHistory && hasFiltered ? (
          <div className="command-history-detail-empty">
            Select a history entry to view details.
          </div>
        ) : null}
      </>
    )}
      </div>

      <div className="module-note">
        Real history will be stored locally in SQLite after the database phase.
      </div>
    </section>
  );
}
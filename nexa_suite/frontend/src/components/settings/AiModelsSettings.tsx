/* ============================================================================
   SETTINGS · AI Models
   ----------------------------------------------------------------------------
   The "AI Models" section for Dashboard → Settings. Pure UI over the Multi-LLM
   manager (useLLM) — provider management, model selection, drag-and-drop
   failover priority, live status, and analytics. Touches no backend or chat
   logic; the router owns execution.
   ========================================================================== */
import { useState } from "react";
import { Cpu, Eye, EyeOff, GripVertical, RefreshCw, Server, Zap } from "lucide-react";
import { useLLM } from "@/lib/llm";
import type { ModelSelection, ProviderId, ProviderStatus } from "@/lib/llm";

const MODEL_OPTIONS: Array<{ id: ModelSelection; label: string; hint: string }> = [
  { id: "auto", label: "Smart Auto", hint: "Recommended" },
  { id: "gpt", label: "GPT", hint: "OpenAI" },
  { id: "gemini-pro", label: "Gemini Pro", hint: "Google" },
  { id: "gemini-flash", label: "Gemini Flash", hint: "Google" },
  { id: "claude", label: "Claude", hint: "Anthropic" },
  { id: "deepseek", label: "DeepSeek", hint: "DeepSeek" },
  { id: "ollama", label: "Ollama", hint: "Local" },
];

/** The providers the user configures (the backend safety net is shown separately). */
const EXTERNAL_IDS: ProviderId[] = ["openai", "gemini", "claude", "deepseek", "ollama"];

function StatusBadge({ status }: { status: ProviderStatus }) {
  const map: Record<ProviderStatus, { dot: string; label: string }> = {
    ready: { dot: "🟢", label: "Ready" },
    "rate-limited": { dot: "🟡", label: "Rate Limited" },
    disconnected: { dot: "🔴", label: "Disconnected" },
    unconfigured: { dot: "⚪", label: "Not configured" },
  };
  const s = map[status];
  return (
    <span className="nx-chip muted" title={`Status: ${s.label}`}>
      {s.dot} {s.label}
    </span>
  );
}

export function AiModelsSettings() {
  const { settings, analytics, manager, statusOf } = useLLM();
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [testing, setTesting] = useState<ProviderId | null>(null);
  const [testResult, setTestResult] = useState<Record<string, string>>({});
  const [dragId, setDragId] = useState<ProviderId | null>(null);

  const runTest = async (id: ProviderId) => {
    setTesting(id);
    setTestResult((prev) => ({ ...prev, [id]: "" }));
    const result = await manager.testConnection(id);
    setTestResult((prev) => ({ ...prev, [id]: result.ok ? "Connected ✓" : result.error || "Failed" }));
    setTesting(null);
  };

  const onDrop = (targetId: ProviderId) => {
    if (!dragId || dragId === targetId) return;
    const order = [...settings.priority];
    const from = order.indexOf(dragId);
    const to = order.indexOf(targetId);
    if (from === -1 || to === -1) return;
    order.splice(from, 1);
    order.splice(to, 0, dragId);
    manager.setPriority(order);
    setDragId(null);
  };

  const currentLabel = analytics.currentProvider
    ? manager.meta(analytics.currentProvider).label
    : "—";

  return (
    <section className="nx-card nx-ai-models">
      <div className="nx-card-head">
        <div className="nx-card-title"><Cpu /> 8. AI Models</div>
      </div>
      <div className="nx-chip-row" style={{ marginBottom: 10 }}>
        <div className="nx-chip muted">Multi-provider</div>
        <div className="nx-chip muted">Smart failover</div>
        <div className="nx-chip">Keys stored locally</div>
      </div>

      {/* -------- Model selection -------- */}
      <div className="nx-field-row"><span>Active model</span></div>
      <div className="nx-seg nx-seg-wrap">
        {MODEL_OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            className={settings.selection === option.id ? "active" : ""}
            onClick={() => manager.setSelection(option.id)}
            title={option.hint}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="nx-hint" style={{ marginTop: 6 }}>
        Smart Auto follows your priority order and fails over automatically. Conversation history is never lost on a switch.
      </p>

      {/* -------- Provider management -------- */}
      <div className="nx-field-row" style={{ marginTop: 14 }}><span>Providers</span></div>
      <div className="nx-list">
        {EXTERNAL_IDS.map((id) => {
          const meta = manager.meta(id);
          const config = manager.config(id);
          const status = statusOf(id);
          const show = revealed[id] ?? false;
          return (
            <div className="nx-ai-provider" key={id}>
              <div className="nx-ai-provider-head">
                <div className="nx-ai-provider-title">
                  <strong>{meta.label}</strong>
                  {meta.futureReady && <span className="nx-chip muted">Future-ready</span>}
                  <StatusBadge status={status} />
                </div>
                <button
                  type="button"
                  className={`nx-switch${config.enabled ? " on" : ""}`}
                  aria-pressed={config.enabled}
                  onClick={() => manager.setProviderEnabled(id, !config.enabled)}
                  title={config.enabled ? "Disable" : "Enable"}
                />
              </div>
              <small className="nx-ai-provider-desc">{meta.description}</small>

              {meta.requiresKey && (
                <div className="nx-ai-key">
                  <input
                    className="nx-input"
                    type={show ? "text" : "password"}
                    value={config.apiKey}
                    placeholder={`${meta.label} API key`}
                    autoComplete="off"
                    spellCheck={false}
                    onChange={(e) => manager.setApiKey(id, e.target.value)}
                  />
                  <button
                    type="button"
                    className="nx-icon-btn"
                    onClick={() => setRevealed((prev) => ({ ...prev, [id]: !show }))}
                    title={show ? "Hide key" : "Show key"}
                  >
                    {show ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              )}

              <div className="nx-ai-provider-row">
                <label className="nx-ai-model-select">
                  <span>Default model</span>
                  <select
                    className="nx-input"
                    value={config.defaultModel}
                    onChange={(e) => manager.setDefaultModel(id, e.target.value)}
                  >
                    {meta.models.map((model) => (
                      <option key={model.id} value={model.id}>{model.label}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="nx-btn ghost"
                  onClick={() => void runTest(id)}
                  disabled={testing === id}
                >
                  <RefreshCw size={13} style={{ marginRight: 6, verticalAlign: "-2px" }} />
                  {testing === id ? "Testing…" : "Test"}
                </button>
              </div>
              {testResult[id] && <div className="nx-ai-test-result">{testResult[id]}</div>}
            </div>
          );
        })}
      </div>

      {/* -------- Failover priority (drag-and-drop) -------- */}
      <div className="nx-field-row" style={{ marginTop: 14 }}><span>Failover priority</span></div>
      <p className="nx-hint" style={{ marginBottom: 8 }}>Drag to reorder. Failover follows this order; the built-in Nexa backend is always the final fallback.</p>
      <div className="nx-ai-priority">
        {settings.priority.map((id, index) => {
          const meta = manager.meta(id);
          return (
            <div
              key={id}
              className={`nx-ai-priority-item${dragId === id ? " dragging" : ""}`}
              draggable
              onDragStart={() => setDragId(id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(id)}
              onDragEnd={() => setDragId(null)}
            >
              <GripVertical size={15} className="nx-ai-grip" />
              <span className="nx-ai-priority-index">{index + 1}</span>
              <span className="nx-ai-priority-name">{meta.label}</span>
              <StatusBadge status={statusOf(id)} />
            </div>
          );
        })}
      </div>

      {/* -------- Baseline note -------- */}
      <div className="nx-row" style={{ marginTop: 12 }}>
        <span><Server size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />Nexa Backend</span>
        <StatusBadge status={statusOf("nexa-backend")} />
      </div>

      {/* -------- Analytics -------- */}
      <div className="nx-field-row" style={{ marginTop: 14 }}><span><Zap size={13} style={{ verticalAlign: "-2px", marginRight: 6 }} />Analytics</span></div>
      <div className="nx-ai-analytics">
        <div className="nx-ai-stat"><small>Current provider</small><strong>{currentLabel}</strong></div>
        <div className="nx-ai-stat"><small>Fallback count</small><strong>{analytics.fallbackCount}</strong></div>
        <div className="nx-ai-stat"><small>Requests today</small><strong>{analytics.requestsToday}</strong></div>
        <div className="nx-ai-stat wide"><small>Last error</small><strong className={analytics.lastError ? "nx-status-warn" : ""}>{analytics.lastError || "None"}</strong></div>
      </div>
    </section>
  );
}

export default AiModelsSettings;

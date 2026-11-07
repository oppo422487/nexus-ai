import { useEffect, useMemo, useState } from "react";
import { BrainCircuit, CheckCircle2, RefreshCw, Save, Stethoscope } from "lucide-react";
import { PageHero } from "@/components/ui";
import {
  createProductivityItem, getProductivityDashboard, getProductivityDiagnostics,
  ProductivityDashboardDto, ProductivityDiagnosticsDto,
} from "@/lib/backendAssistantClient";
import { EmailSkillPanel } from "@/components/email/EmailSkillPanel";

const EXAMPLES = [
  "নেক্সা মনে রাখো আমার favourite color blue",
  "নেক্সা নোট করো project-এর voice test করতে হবে",
  "নেক্সা task add API documentation শেষ করো",
  "নেক্সা shopping list এ coffee যোগ করো",
  "নেক্সা calendar এ tomorrow 10 am team meeting add করো",
  "নেক্সা email draft to Rahim project update পাঠাব",
  "নেক্সা YouTube-এ Bangla song চালাও",
  "নেক্সা YouTube ২০ সেকেন্ড সামনে নাও",
  "নেক্সা YouTube volume ৫০ করো",
  "নেক্সা এই স্ক্রিনে কী আছে?",
  "নেক্সা সব feature দেখাও",
];

export function SkillsHubPage() {
  const [dashboard, setDashboard] = useState<ProductivityDashboardDto | null>(null);
  const [diagnostics, setDiagnostics] = useState<ProductivityDiagnosticsDto | null>(null);
  const [kind, setKind] = useState("note");
  const [text, setText] = useState("");
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [nextDashboard, nextDiagnostics] = await Promise.all([getProductivityDashboard(), getProductivityDiagnostics()]);
      setDashboard(nextDashboard);
      setDiagnostics(nextDiagnostics);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Skills Hub could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);
  const localCount = useMemo(() => dashboard
    ? dashboard.memories.length + dashboard.notes.length + dashboard.calendar_events.length + dashboard.drafts.length
    : 0, [dashboard]);

  const createItem = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const result = await createProductivityItem({ kind, text: text.trim(), recipient: recipient.trim() });
      setMessage(result.message);
      if (result.created) { setText(""); setRecipient(""); await refresh(); }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Item could not be created.");
    } finally { setLoading(false); }
  };

  return (
    <section className="nx-page">
      <PageHero icon={<BrainCircuit />} eyebrow="Nexa Skills" title="Skills & Productivity Hub"
        description="Twenty integrated capabilities for voice, text, memory, productivity, safe actions and diagnostics." />

      <div className="nx-grid-3" style={{ marginBottom: 18 }}>
        <div className="nx-stat"><strong>{dashboard?.skills.length ?? "—"}</strong><span>Registered skills</span></div>
        <div className="nx-stat green"><strong>{diagnostics?.checks.filter((item) => item.ok).length ?? "—"}</strong><span>Healthy checks</span></div>
        <div className="nx-stat purple"><strong>{localCount}</strong><span>Local items</span></div>
      </div>

      <div className="nx-grid-2" style={{ alignItems: "start" }}>
        <section className="nx-card">
          <div className="nx-card-head"><div className="nx-card-title"><BrainCircuit /> Capability registry</div>
            <button className="nx-btn ghost" type="button" onClick={() => void refresh()} disabled={loading}><RefreshCw size={15} /> Refresh</button></div>
          <div className="nx-list">
            {dashboard?.skills.map((skill) => <div className="nx-list-item" key={skill.id}>
              <CheckCircle2 size={17} className="nx-status-ok" /><div className="nx-list-main"><strong>{skill.name}</strong><small>{skill.description}</small></div>
              <span className="nx-list-badge ok">{skill.status}</span>
            </div>)}
          </div>
        </section>

        <div style={{ display: "grid", gap: 16 }}>
          <EmailSkillPanel />
          <section className="nx-card">
            <div className="nx-card-head"><div className="nx-card-title"><Save /> Add local item</div></div>
            <select className="nx-input" value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="note">Note</option><option value="task">Task</option><option value="shopping">Shopping item</option>
              <option value="memory">Memory</option><option value="calendar">Calendar event</option>
              <option value="email">Email draft</option><option value="voice_profile">Voice profile</option>
            </select>
            {kind === "email" && <input className="nx-input" placeholder="Recipient" value={recipient} onChange={(event) => setRecipient(event.target.value)} />}
            <textarea className="nx-input" rows={4} placeholder={kind === "voice_profile" ? "Profile name" : "What should Nexa save?"} value={text} onChange={(event) => setText(event.target.value)} />
            <button type="button" className="nx-btn" onClick={() => void createItem()} disabled={loading || !text.trim()}><Save size={15} /> Confirm & save locally</button>
            {message && <p className="nx-hint">{message}</p>}
          </section>

          <section className="nx-card">
            <div className="nx-card-head"><div className="nx-card-title"><Stethoscope /> Diagnostics</div></div>
            <div className="nx-list">{diagnostics?.checks.map((check) => <div className="nx-list-item" key={check.name}>
              <span className={`nx-status-dot ${check.ok ? "ok" : "bad"}`} /><div className="nx-list-main"><strong>{check.name}</strong></div>
              <span className={`nx-list-badge ${check.ok ? "ok" : "bad"}`}>{check.ok ? "Ready" : "Needs attention"}</span>
            </div>)}</div>
          </section>

          <section className="nx-card"><div className="nx-card-head"><div className="nx-card-title">Voice examples</div></div>
            <div className="nx-list">{EXAMPLES.map((example) => <div className="nx-list-item" key={example}><div className="nx-list-main"><strong>{example}</strong></div></div>)}</div>
          </section>
        </div>
      </div>
    </section>
  );
}

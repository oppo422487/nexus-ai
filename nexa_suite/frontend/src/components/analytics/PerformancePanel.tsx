import { useEffect, useState } from "react";
import { Activity, Download } from "lucide-react";
import { DEFAULT_BACKEND_URL } from "@/lib/backendCommandClient";
import { getAuditStatistics } from "@/lib/backendAssistantClient";

export function PerformancePanel() {
  const [stats, setStats] = useState<Awaited<ReturnType<typeof getAuditStatistics>> | null>(null);
  useEffect(() => { getAuditStatistics().then(setStats).catch(() => setStats(null)); }, []);
  return (
    <section className="nx-card performance-panel">
      <div className="nx-card-head"><div className="nx-card-title"><Activity /> Performance & Usage</div><div className="performance-exports"><a className="nx-btn ghost" href={`${DEFAULT_BACKEND_URL}/api/audit/export?format=csv`}><Download size={14}/>CSV</a><a className="nx-btn ghost" href={`${DEFAULT_BACKEND_URL}/api/audit/export?format=json`}><Download size={14}/>JSON</a></div></div>
      {!stats ? <div className="nx-empty">Backend analytics unavailable.</div> : <>
        <div className="nx-grid-3"><div className="nx-stat"><strong>{stats.total_events}</strong><span>Total events</span></div><div className="nx-stat purple"><strong>{stats.by_status.executed ?? stats.by_status.completed ?? 0}</strong><span>Successful</span></div><div className="nx-stat green"><strong>{stats.by_status.failed ?? 0}</strong><span>Failed</span></div></div>
        <div className="performance-intents">{Object.entries(stats.by_intent).slice(0, 8).map(([name, count]) => <div key={name}><span>{name.replaceAll("_", " ")}</span><strong>{count}</strong></div>)}</div>
      </>}
    </section>
  );
}

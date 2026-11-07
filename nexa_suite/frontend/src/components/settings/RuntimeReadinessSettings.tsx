import { useEffect, useState } from "react";
import { BadgeCheck, RefreshCw, TriangleAlert } from "lucide-react";
import { configureHuggingFaceToken, getSetupReadiness, SetupReadinessDto } from "@/lib/backendAssistantClient";

const LABELS = {
  assemblyai_streaming_stt: "AssemblyAI Streaming STT",
  image_generation: "AI Image Generation",
  edge_tts: "Edge Neural TTS",
  advanced_youtube: "Advanced YouTube",
};

export function RuntimeReadinessSettings() {
  const [readiness, setReadiness] = useState<SetupReadinessDto | null>(null);
  const [message, setMessage] = useState("Checking backend runtime...");
  const [hfToken, setHfToken] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = async () => {
    try {
      const result = await getSetupReadiness();
      setReadiness(result);
      setMessage(result.all_dependencies_ready ? "All optional runtime dependencies are installed." : "Some optional runtime dependencies need attention.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Runtime readiness is unavailable.");
    }
  };

  useEffect(() => { void refresh(); }, []);

  const saveToken = async () => {
    if (!hfToken.trim()) return;
    setSaving(true);
    try {
      const result = await configureHuggingFaceToken(hfToken.trim());
      setMessage(result.message);
      if (result.configured) {
        setHfToken("");
        await refresh();
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Token configuration failed.");
    } finally {
      setSaving(false);
    }
  };

  return <section className="nx-card">
    <div className="nx-card-head">
      <div className="nx-card-title"><BadgeCheck /> Runtime Readiness</div>
      <button type="button" className="nx-link-btn" onClick={() => void refresh()}><RefreshCw size={13} /> Refresh</button>
    </div>
    {readiness && <div className="nx-list">
      {Object.entries(readiness.capabilities).map(([key, item]) => <div className="nx-list-row" key={key}>
        <div className="nx-list-main">
          <strong>{LABELS[key as keyof typeof LABELS]}</strong>
          <small>{item.action}{item.internet_required ? " Internet is required while using this feature." : ""}</small>
        </div>
        <span className={`nx-list-badge ${item.ready ? "low" : "high"}`}>{item.ready ? "Ready" : <><TriangleAlert size={11} /> Setup</>}</span>
      </div>)}
      <div className="nx-list-row"><div className="nx-list-main"><strong>Backend runtime</strong><small>Python {readiness.python}</small></div><span className="nx-list-badge low">{readiness.packaged_backend ? "Standalone" : "Development"}</span></div>
    </div>}
    {readiness && !readiness.capabilities.image_generation.configured && <div className="content-writer-fields" style={{ marginTop: 12 }}>
      <input type="password" autoComplete="off" value={hfToken} onChange={(event) => setHfToken(event.target.value)} placeholder="Hugging Face token (stored locally)" aria-label="Hugging Face token" />
      <button type="button" className="nx-btn primary" onClick={() => void saveToken()} disabled={saving || hfToken.trim().length < 8}>{saving ? "Saving..." : "Confirm & Save Token"}</button>
    </div>}
    <p className="youtube-control-message">{message}</p>
  </section>;
}

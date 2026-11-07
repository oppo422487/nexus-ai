import { useEffect, useState } from "react";
import { AppWindow, Play, SkipBack, SkipForward, Volume1, Volume2, VolumeX } from "lucide-react";
import { getSystemControlsHealth, requestSystemControl } from "@/lib/backendAssistantClient";

export function SystemControlsPanel() {
  const [available, setAvailable] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [apps, setApps] = useState<Array<{ key: string; label: string }>>([]);
  const [selectedApp, setSelectedApp] = useState("notepad");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Checking Windows controls...");

  useEffect(() => {
    getSystemControlsHealth()
      .then((response) => {
        setAvailable(response.available);
        setEnabled(response.enabled);
        setApps(response.closeable_apps);
        if (response.closeable_apps[0]) setSelectedApp(response.closeable_apps[0].key);
        setMessage(response.enabled ? "Controls require an explicit button click." : "Enable System Media & App Controls in Security Center.");
      })
      .catch(() => setMessage("Backend required for Windows controls."));
  }, []);

  const run = async (action: "volume_up" | "volume_down" | "mute" | "play_pause" | "next_track" | "previous_track" | "close_app") => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await requestSystemControl(action, action === "close_app" ? selectedApp : null);
      setMessage(response.error || response.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "System control failed.");
    } finally {
      setBusy(false);
    }
  };

  const disabled = busy || !available || !enabled;
  return (
    <section className="nx-card system-controls-card">
      <div className="nx-card-head">
        <div className="nx-card-title"><AppWindow /> Windows Controls</div>
        <span className={`nx-list-badge ${available && enabled ? "ok" : "mid"}`}>{available && enabled ? "Enabled" : "Locked"}</span>
      </div>
      <div className="system-control-actions">
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("volume_down")}><Volume1 size={15} /> Down</button>
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("mute")}><VolumeX size={15} /> Mute</button>
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("volume_up")}><Volume2 size={15} /> Up</button>
      </div>
      <div className="system-control-actions">
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("previous_track")}><SkipBack size={15} /> Previous</button>
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("play_pause")}><Play size={15} /> Play/Pause</button>
        <button type="button" className="nx-btn ghost" disabled={disabled} onClick={() => void run("next_track")}><SkipForward size={15} /> Next</button>
      </div>
      <div className="system-close-row">
        <select value={selectedApp} onChange={(event) => setSelectedApp(event.target.value)} disabled={disabled}>
          {apps.map((app) => <option key={app.key} value={app.key}>{app.label}</option>)}
        </select>
        <button type="button" className="nx-btn ghost danger" disabled={disabled} onClick={() => void run("close_app")}>Close app</button>
      </div>
      <p className="youtube-control-message">{message}</p>
    </section>
  );
}

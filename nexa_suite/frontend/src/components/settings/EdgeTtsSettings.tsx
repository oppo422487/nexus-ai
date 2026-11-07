import { useState } from "react";
import { AudioLines } from "lucide-react";
import { requestEdgeTtsAudio } from "@/lib/backendAssistantClient";

const VOICES = [
  ["bn-BD-NabanitaNeural", "Bangla — Nabanita"],
  ["bn-BD-PradeepNeural", "Bangla — Pradeep"],
  ["en-US-AriaNeural", "English — Aria"],
  ["en-US-GuyNeural", "English — Guy"],
] as const;

export function EdgeTtsSettings() {
  const [voice, setVoice] = useState(VOICES[0][0]);
  const [text, setText] = useState("হ্যালো, আমি নেক্সা। কীভাবে সাহায্য করতে পারি?");
  const [message, setMessage] = useState("Default online neural TTS. Requires an internet connection.");
  const [busy, setBusy] = useState(false);

  const preview = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const blob = await requestEdgeTtsAudio(text.trim(), voice);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.addEventListener("ended", () => URL.revokeObjectURL(url), { once: true });
      audio.addEventListener("error", () => URL.revokeObjectURL(url), { once: true });
      await audio.play();
      setMessage("Edge voice preview is playing.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Edge voice preview failed.");
    } finally {
      setBusy(false);
    }
  };

  return <section className="nx-card">
    <div className="nx-card-head"><div className="nx-card-title"><AudioLines /> Edge Neural Voice — Fallback</div><span className="nx-list-badge ok">Online</span></div>
    <div className="content-writer-fields">
      <select value={voice} onChange={(event) => setVoice(event.target.value as typeof voice)} aria-label="Edge TTS voice">
        {VOICES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
      <textarea rows={3} value={text} onChange={(event) => setText(event.target.value)} aria-label="Voice preview text" />
      <button type="button" className="nx-btn primary" onClick={() => void preview()} disabled={busy || !text.trim()}>{busy ? "Loading..." : "Play Neural Preview"}</button>
    </div>
    <p className="youtube-control-message">{message}</p>
  </section>;
}

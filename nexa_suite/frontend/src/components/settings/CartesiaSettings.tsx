import { useEffect, useState } from "react";
import { AudioLines } from "lucide-react";
import {
  getCartesiaStatus, getCartesiaVoices, removeCartesiaKey, requestTtsSpeak,
  saveCartesiaKey, setCartesiaVoice,
  type CartesiaStatusDto, type CartesiaVoiceDto,
} from "@/lib/backendAssistantClient";

export function CartesiaSettings() {
  const [status, setStatus] = useState<CartesiaStatusDto | null>(null);
  const [key, setKey] = useState("");
  const [language, setLanguage] = useState<"bn" | "en">("bn");
  const [voices, setVoices] = useState<CartesiaVoiceDto[]>([]);
  const [message, setMessage] = useState("Cartesia Sonic is primary. Edge neural voice is the fallback.");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void getCartesiaStatus().then(setStatus).catch(() => setMessage("Start the local backend to manage Cartesia.")); }, []);

  const loadVoices = async (selectedLanguage: "bn" | "en") => {
    setBusy(true);
    try {
      const result = await getCartesiaVoices(selectedLanguage);
      setVoices(result.voices);
      setMessage(result.message);
    } catch (err) { setMessage(err instanceof Error ? err.message : "Could not load voices."); }
    finally { setBusy(false); }
  };

  const save = async () => {
    setBusy(true);
    try {
      const result = await saveCartesiaKey(key);
      setMessage(result.message);
      if (result.ok) { setStatus(result); setKey(""); setVoices([]); }
    } catch (err) { setMessage(err instanceof Error ? err.message : "Could not save key."); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    setBusy(true);
    try {
      const result = await removeCartesiaKey();
      setStatus(result);
      setVoices([]);
      setKey("");
      setMessage(result.message);
    } catch (err) { setMessage(err instanceof Error ? err.message : "Could not remove key."); }
    finally { setBusy(false); }
  };

  const chooseVoice = async (voiceId: string) => {
    if (!voiceId) return;
    setBusy(true);
    try {
      const result = await setCartesiaVoice(language, voiceId);
      setMessage(result.message);
      if (result.ok) setStatus(result);
    } catch (err) { setMessage(err instanceof Error ? err.message : "Could not select voice."); }
    finally { setBusy(false); }
  };

  return <section className="nx-card">
    <div className="nx-card-head">
      <div className="nx-card-title"><AudioLines /> Cartesia Sonic 3.6 — Primary Voice</div>
      <span className={`nx-list-badge ${status?.configured ? "ok" : "warn"}`}>{status?.configured ? "Configured" : "Needs key"}</span>
    </div>
    <p className="youtube-control-message">Add a Cartesia key from any account with available credits. Replacing the key switches accounts. The key is encrypted for this Windows user and is never shown again.</p>
    <div className="nx-field-row">
      <span>API key</span>
      <input className="nx-input" type="password" autoComplete="off" spellCheck={false} value={key}
        placeholder={status?.configured ? "New key to replace current key" : "sk_car_..."}
        onChange={(event) => setKey(event.target.value)} />
    </div>
    <div className="nx-chip-row" style={{ marginTop: 8 }}>
      <button className="nx-btn primary" type="button" disabled={busy || !key.trim()} onClick={() => void save()}>{status?.configured ? "Replace key" : "Save key"}</button>
      <button className="nx-btn ghost" type="button" disabled={busy || !status?.configured} onClick={() => void remove()}>Remove key</button>
    </div>
    <div className="nx-field-row" style={{ marginTop: 12 }}>
      <span>Voice language</span>
      <select className="nx-input" value={language} onChange={(event) => { setLanguage(event.target.value as "bn" | "en"); setVoices([]); }}>
        <option value="bn">Bangla</option><option value="en">English</option>
      </select>
    </div>
    <button className="nx-btn ghost" type="button" disabled={busy || !status?.configured} onClick={() => void loadVoices(language)}>Load {language === "bn" ? "Bangla" : "English"} voices</button>
    {voices.length > 0 && <div className="nx-field-row" style={{ marginTop: 8 }}>
      <span>Cartesia voice</span>
      <select className="nx-input" value={language === "bn" ? status?.voice_bn || "" : status?.voice_en || ""}
        onChange={(event) => void chooseVoice(event.target.value)}>
        <option value="">Auto — first available voice</option>
        {voices.map((voice) => <option key={voice.id} value={voice.id}>{voice.name}</option>)}
      </select>
    </div>}
    <button className="nx-btn ghost" type="button" style={{ width: "100%", marginTop: 12 }} disabled={busy}
      onClick={() => void requestTtsSpeak(language === "bn" ? "হ্যালো, আমি নেক্সা। কীভাবে সাহায্য করতে পারি?" : "Hello, I am Nexa. How can I help you?")
        .then((result) => setMessage(result.message)).catch((err: unknown) => setMessage(err instanceof Error ? err.message : "Voice test failed."))}>
      ▶ Test primary voice
    </button>
    <p className="youtube-control-message" role="status">{message}</p>
  </section>;
}

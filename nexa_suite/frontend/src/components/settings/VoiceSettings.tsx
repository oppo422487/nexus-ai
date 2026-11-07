/* ============================================================================
   SETTINGS · Voice
   ----------------------------------------------------------------------------
   Settings → Voice section. Pure UI over the VoiceManager (useVoice): reply /
   continuous / auto-speak toggles, speed / pitch / volume, language, and the
   TTS voice picker, with a live "Test voice" button.
   ========================================================================== */
import { Volume2 } from "lucide-react";
import { useVoice } from "@/lib/voice";
import type { VoiceSttEngine } from "@/lib/voice";
import { loadProfile } from "@/lib";

function Switch({ on, onClick }: { on: boolean; onClick: () => void }) {
  return <button type="button" className={`nx-switch${on ? " on" : ""}`} aria-pressed={on} onClick={onClick} />;
}

export function VoiceSettings() {
  const { settings, voices, recognitionSupported, synthesisSupported, manager } = useVoice();

  return (
    <section className="nx-card nxv-settings">
      <div className="nx-card-head">
        <div className="nx-card-title"><Volume2 /> 9. Voice</div>
      </div>
      <div className="nx-chip-row" style={{ marginBottom: 10 }}>
        <div className={`nx-chip ${recognitionSupported ? "" : "warn"}`}>{recognitionSupported ? "Online STT ready" : "No online STT"}</div>
        <div className={`nx-chip ${synthesisSupported ? "" : "warn"}`}>{synthesisSupported ? "Cartesia / Edge TTS ready" : "No online TTS"}</div>
      </div>

      <div className="nx-switch-row">
        <span>Enable Voice Reply<small>Speak AI responses aloud</small></span>
        <Switch on={settings.enableVoiceReply} onClick={() => manager.updateSettings({ enableVoiceReply: !settings.enableVoiceReply })} />
      </div>

      <label className="nx-field">
        <span>Speech-to-Text Engine</span>
        <select className="nx-input" value={settings.sttEngine} onChange={(event) => manager.updateSettings({ sttEngine: event.target.value as VoiceSttEngine })}>
          <option value="auto">Auto — AssemblyAI, then local upload fallback</option>
          <option value="assemblyai">AssemblyAI Multilingual Streaming (primary)</option>
          <option value="browser">Browser Web Speech</option>
        </select>
        <small>AssemblyAI detects Bangla or English automatically and streams partial words in real time. The API key stays on the backend.</small>
      </label>
      <div className="nx-switch-row">
        <span>Auto Speak Responses<small>Speak every reply automatically as it arrives</small></span>
        <Switch on={settings.autoSpeak} onClick={() => manager.updateSettings({ autoSpeak: !settings.autoSpeak })} />
      </div>
      <div className="nx-switch-row">
        <span>Enable Continuous Listening<small>Keep listening hands-free after each turn</small></span>
        <Switch on={settings.continuousListening} onClick={() => manager.updateSettings({ continuousListening: !settings.continuousListening })} />
      </div>
      <div className="nx-switch-row">
        <span>Wake Word: Nexa<small>Require “Nexa”/“নেক্সা” before a new conversation</small></span>
        <Switch on={settings.wakeWordEnabled} onClick={() => manager.updateSettings({ wakeWordEnabled: !settings.wakeWordEnabled })} />
      </div>

      <label className="nx-field">
        <span>Voice Speed — {settings.rate.toFixed(2)}×</span>
        <input className="nxv-range" type="range" min={0.5} max={2} step={0.05} value={settings.rate}
          onChange={(e) => manager.updateSettings({ rate: Number(e.target.value) })} />
      </label>
      <label className="nx-field">
        <span>Voice Volume — {Math.round(settings.volume * 100)}%</span>
        <input className="nxv-range" type="range" min={0} max={1} step={0.05} value={settings.volume}
          onChange={(e) => manager.updateSettings({ volume: Number(e.target.value) })} />
      </label>

      <p className="nx-hint">Voice recognition and replies follow Language in your profile: {loadProfile().languageMode}. Choose Bangla or English there for dedicated recognition.</p>

      <label className="nx-field">
        <span>AI Voice</span>
        <select className="nx-input" value={settings.voiceURI ?? ""}
          onChange={(e) => manager.updateSettings({ voiceURI: e.target.value || null })}>
          <option value="">Auto (match language)</option>
          {voices.map((v) => (
            <option key={v.voiceURI} value={v.voiceURI}>{v.name} — {v.lang}</option>
          ))}
        </select>
        <small>This selects the Edge fallback voice. Choose the Cartesia voice in its Settings card.</small>
      </label>

      <button type="button" className="nx-btn ghost" style={{ width: "100%", marginTop: 8 }}
        onClick={() => manager.previewVoice()} disabled={!synthesisSupported}>
        <Volume2 size={14} style={{ marginRight: 6, verticalAlign: "-2px" }} /> Test voice
      </button>
    </section>
  );
}

export default VoiceSettings;

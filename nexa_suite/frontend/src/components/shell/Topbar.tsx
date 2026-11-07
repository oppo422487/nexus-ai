import { EngineControls, useEngine } from "@/lib/engineRuntime";
import { Bell, Mic, Settings as SettingsIcon } from "lucide-react";
import { CommandBar } from "@/components/ui";
import { PushToTalkPanel } from "@/components/voice/PushToTalkPanel";

export function Topbar({
  profileName,
  voiceReady,
  dueReminderCount,
  onCommandSubmit,
  onVoiceTranscript,
  onOpenVoice,
  onOpenSettings,
}: {
  profileName: string;
  voiceReady: boolean;
  dueReminderCount: number;
  onCommandSubmit: (text: string) => void;
  onVoiceTranscript: (text: string) => void | Promise<void>;
  onOpenVoice: () => void;
  onOpenSettings: () => void;
}) {
  const engine = useEngine();
  const initials = (profileName || "Local User")
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="nx-topbar nxos-topbar">
      {/* AI status — the assistant's live state, front and centre-left. */}
      <div className="nxos-ai-status" title="Nexa core status">
        <span className={`nxos-ai-orb ${voiceReady ? "online" : "offline"}`} />
        <div className="nxos-ai-status-text">
          <strong>Nexa</strong>
          <span className={voiceReady ? "on" : "off"}>
            {engine.enabled ? engine.speaking ? "কথা বলছি" : engine.connected ? "প্রস্তুত" : "সংযোগ হচ্ছে" : voiceReady ? "Online · Ready" : "Offline"}
          </span>
        </div>
      </div>

      {/* Command bar — the primary way to drive the OS. */}
      <CommandBar
        placeholder="Type a command or ask Nexa…  (e.g. গুগল খোলো)"
        onSubmit={onCommandSubmit}
      />

      <div className="nxos-topbar-actions">
        {voiceReady ? (
          <>
            {engine.enabled ? <EngineControls compact /> : <PushToTalkPanel compact onTranscript={onVoiceTranscript} />}
            <button type="button" className="nx-voice-pill nxos-voice-pill" onClick={onOpenVoice} title="Open continuous voice conversation">
              <Mic size={15} /><span className="on">Voice room</span>
            </button>
          </>
        ) : (
          <div className="nx-voice-pill nxos-voice-pill"><span className="off">Voice off</span></div>
        )}

        <button
          type="button"
          className="nx-icon-btn"
          title={
            dueReminderCount > 0
              ? `${dueReminderCount} reminder(s) due now`
              : "No due reminders"
          }
        >
          <Bell />
          {dueReminderCount > 0 && (
            <span className="nx-bell-dot">{dueReminderCount}</span>
          )}
        </button>

        <button
          type="button"
          className="nx-icon-btn"
          onClick={onOpenSettings}
          title="Open settings"
        >
          <SettingsIcon />
        </button>

        <div className="nx-profile nxos-profile">
          <div className="nx-avatar">{initials || "LU"}</div>
          <div className="nxos-profile-text">
            <strong>{profileName || "Local User"}</strong>
            <span>Local · Private</span>
          </div>
        </div>
      </div>
    </header>
  );
}

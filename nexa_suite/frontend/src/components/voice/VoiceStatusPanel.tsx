import type { FC } from "react";

type VoiceStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

type VoiceStatusPanelProps = {
  status?: VoiceStatus;
  title?: string;
  subtitle?: string;
};

const statusLabelMap: Record<VoiceStatus, string> = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Processing",
  speaking: "Speaking",
  error: "Error",
};

const statusDescriptionMap: Record<VoiceStatus, string> = {
  idle: "The voice system is waiting for a mode selection or a command.",
  listening: "The assistant is ready to accept your voice input.",
  thinking: "Your command is being analyzed by the UI engine.",
  speaking: "A voice response would play once speech output is connected.",
  error: "The voice status has encountered an issue and is paused.",
};

export const VoiceStatusPanel: FC<VoiceStatusPanelProps> = ({
  status = "idle",
  title = "Voice status",
  subtitle,
}) => {
  return (
    <section className="voice-panel">
      <div className="voice-panel-header">
        <div>
          <p className="eyebrow">{title}</p>
          <h4>{statusLabelMap[status]}</h4>
          <p>{subtitle ?? statusDescriptionMap[status]}</p>
        </div>

        <div className={`voice-orb-mini voice-status-${status}`}>
          <div className="voice-orb-mini-core" />
        </div>
      </div>

      <div className="voice-status-note">
        <p>Voice engine is frontend-only in this phase.</p>
      </div>
    </section>
  );
};

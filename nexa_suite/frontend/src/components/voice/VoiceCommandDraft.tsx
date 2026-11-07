import type { FC } from "react";

type RiskLevel = "safe" | "confirmation_required" | "sensitive";

type VoiceCommandDraftProps = {
  command?: string;
  intent?: string;
  riskLevel?: RiskLevel;
};

const riskLabelMap: Record<RiskLevel, string> = {
  safe: "Safe",
  confirmation_required: "Confirmation required",
  sensitive: "Sensitive",
};

export const VoiceCommandDraft: FC<VoiceCommandDraftProps> = ({
  command,
  intent,
  riskLevel = "safe",
}) => {
  const commandText = command?.trim() || "No draft command yet.";
  const intentText = intent?.trim() || "Awaiting detected intent.";

  return (
    <section className="voice-panel">
      <div className="voice-panel-header">
        <div>
          <p className="eyebrow">Voice command</p>
          <h4>Command draft</h4>
          <p>Execution is disabled for now. This preview remains UI-only.</p>
        </div>
      </div>

      <div className="voice-command-box">
        <p>{commandText}</p>
      </div>

      <div className="voice-meta-grid">
        <div>
          <span>Detected intent</span>
          <strong>{intentText}</strong>
        </div>
        <div>
          <span>Risk level</span>
          <strong className={`voice-risk-badge ${riskLevel}`}> {riskLabelMap[riskLevel]}</strong>
        </div>
      </div>
    </section>
  );
};

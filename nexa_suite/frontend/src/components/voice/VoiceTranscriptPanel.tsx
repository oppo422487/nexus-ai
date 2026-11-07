import type { FC } from "react";

type VoiceLanguage = "Bangla" | "English" | "Mixed";

type VoiceTranscriptPanelProps = {
  transcript?: string;
  confidence?: number;
  language?: VoiceLanguage;
};

export const VoiceTranscriptPanel: FC<VoiceTranscriptPanelProps> = ({
  transcript,
  confidence,
  language,
}) => {
  const trimmedTranscript = transcript?.trim();
  const hasTranscript = Boolean(trimmedTranscript);
  const confidenceValue = typeof confidence === "number" ? confidence : undefined;
  const confidenceLabel = confidenceValue === undefined
    ? "N/A"
    : confidenceValue > 0 && confidenceValue <= 1
    ? `${Math.round(confidenceValue * 100)}%`
    : `${Math.round(confidenceValue)}%`;

  return (
    <section className="voice-panel">
      <div className="voice-panel-header">
        <div>
          <p className="eyebrow">Voice transcript</p>
          <h4>Transcript preview</h4>
          <p>
            {hasTranscript
              ? "This area shows the latest recognized text from the voice draft."
              : "Awaiting a frontend voice transcript."}
          </p>
        </div>
      </div>

      <div className="voice-transcript-box">
        {hasTranscript ? trimmedTranscript : "No voice transcript yet."}
      </div>

      <div className="voice-meta-grid">
        <div>
          <span>Language</span>
          <strong>{language ?? "N/A"}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{confidenceLabel}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{hasTranscript ? "Ready" : "Empty"}</strong>
        </div>
      </div>
    </section>
  );
};

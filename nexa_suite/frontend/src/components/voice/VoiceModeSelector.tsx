import { useEffect, useState } from "react";

export type VoiceMode = "Push to Talk" | "Always Listening" | "Manual Text";

type VoiceModeSelectorProps = {
  selectedMode?: VoiceMode;
  onModeChange?: (mode: VoiceMode) => void;
};

const modeOptions: { mode: VoiceMode; label: string; description: string }[] = [
  {
    mode: "Push to Talk",
    label: "Push to Talk",
    description: "Tap to activate voice capture when you are ready.",
  },
  {
    mode: "Always Listening",
    label: "Always Listening",
    description: "The UI keeps the voice system on standby.",
  },
  {
    mode: "Manual Text",
    label: "Manual Text",
    description: "Type commands instead of using voice input.",
  },
];

export const VoiceModeSelector = ({
  selectedMode,
  onModeChange,
}: VoiceModeSelectorProps) => {
  const [internalMode, setInternalMode] = useState<VoiceMode>(selectedMode ?? "Push to Talk");

  useEffect(() => {
    if (selectedMode) {
      setInternalMode(selectedMode);
    }
  }, [selectedMode]);

  const activeMode = selectedMode ?? internalMode;

  const handleModeSelect = (mode: VoiceMode) => {
    setInternalMode(mode);
    onModeChange?.(mode);
  };

  return (
    <section className="voice-panel">
      <div className="voice-panel-header">
        <div>
          <p className="eyebrow">Voice mode</p>
          <h4>Input selector</h4>
          <p>Select a voice mode for the next development phase.</p>
        </div>
      </div>

      <div className="voice-mode-grid">
        {modeOptions.map((item) => (
          <button
            key={item.mode}
            type="button"
            className={`voice-mode-card ${activeMode === item.mode ? "active" : ""}`}
            onClick={() => handleModeSelect(item.mode)}
          >
            <strong>{item.label}</strong>
            <p>{item.description}</p>
          </button>
        ))}
      </div>
    </section>
  );
};

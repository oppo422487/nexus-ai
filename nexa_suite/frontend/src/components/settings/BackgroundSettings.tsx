/* ============================================================================
   SETTINGS · Background
   ----------------------------------------------------------------------------
   Enable/disable the premium AI globe background and pick a quality preset.
   Purely drives the background store — nothing here imports three/globe.
   ========================================================================== */
import { Globe2 } from "lucide-react";
import { useBackgroundSettings } from "@/background";
import type { QualitySetting } from "@/background";

const QUALITY_OPTIONS: Array<{ id: QualitySetting; label: string }> = [
  { id: "auto", label: "Auto" },
  { id: "high", label: "High" },
  { id: "medium", label: "Medium" },
  { id: "low", label: "Low" },
];

export function BackgroundSettings() {
  const { settings, setEnabled, setQuality } = useBackgroundSettings();

  return (
    <section className="nx-card">
      <div className="nx-card-head">
        <div className="nx-card-title"><Globe2 /> 10. Background</div>
      </div>
      <div className="nx-chip-row" style={{ marginBottom: 10 }}>
        <div className="nx-chip muted">Premium</div>
        <div className="nx-chip muted">Lazy-loaded</div>
        <div className="nx-chip muted">GPU-adaptive</div>
      </div>

      <div className="nx-switch-row">
        <span>
          AI Globe Background
          <small>Holographic Earth, neural network, and particles behind the app. Off = the lightweight fast UI.</small>
        </span>
        <button
          type="button"
          className={`nx-switch${settings.enabled ? " on" : ""}`}
          aria-pressed={settings.enabled}
          onClick={() => setEnabled(!settings.enabled)}
        />
      </div>

      <div className="nx-field-row" style={{ marginTop: 6 }}><span>Quality</span></div>
      <div className="nx-seg nx-seg-wrap">
        {QUALITY_OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            className={settings.quality === option.id ? "active" : ""}
            onClick={() => setQuality(option.id)}
            disabled={!settings.enabled}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="nx-hint" style={{ marginTop: 6 }}>
        Auto detects your GPU and scales particles, bloom, and resolution to keep it smooth. It pauses automatically when the window is hidden.
      </p>
    </section>
  );
}

export default BackgroundSettings;

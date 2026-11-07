import { useEffect, useState } from "react";
import {
  getBackendTtsStatus,
  requestTtsSpeak,
  TtsStatusResponseDto,
  updateBackendPermission,
} from "@/lib/backendAssistantClient";

/** Voice reply (TTS) settings: enable/disable + test online Edge neural voice. */
export function TtsSettingsCard() {
  const [status, setStatus] = useState<TtsStatusResponseDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      setStatus(await getBackendTtsStatus());
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "TTS status could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleToggle = async () => {
    if (!status) return;
    setSaving(true);
    setMessage(null);
    try {
      await updateBackendPermission("voice_tts", !status.enabled);
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "TTS toggle failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setMessage(null);
    try {
      const result = await requestTtsSpeak("Hello, I am Nexa, your desktop assistant.");
      setMessage(result.spoken ? "Test voice spoken." : (result.error || result.message));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "TTS test failed.");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="settings-card tts-settings-card">
      <h4>Voice Reply (TTS)</h4>
      {errorMessage && <div className="backend-preview-error">{errorMessage}</div>}
      {loading && !status && <p className="settings-loading">Checking voice engine...</p>}
      {status && (
        <>
          <div className="profile-preview-grid">
            <div className="profile-preview-row">
              <span>Engine installed</span>
              <strong>{status.dependency_installed ? "Yes" : "No"}</strong>
            </div>
            <div className="profile-preview-row">
              <span>Voice reply</span>
              <strong>{status.enabled ? "Enabled" : "Disabled"}</strong>
            </div>
            <div className="profile-preview-row">
              <span>Online neural voices</span>
              <strong>{status.voices.length}</strong>
            </div>
          </div>
          <div className="transcript-action-row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="transcript-action-button"
              onClick={handleToggle}
              disabled={saving || !status.dependency_installed}
            >
              {saving
                ? "Saving..."
                : status.enabled
                ? "Disable Voice Reply"
                : "Enable Voice Reply"}
            </button>
            <button
              type="button"
              className="transcript-action-button secondary"
              onClick={handleTest}
              disabled={testing || !status.enabled}
            >
              {testing ? "Speaking..." : "Test Voice"}
            </button>
          </div>
          {message && <p className="history-save-message">{message}</p>}
          <p className="settings-tts-note">
            Online Edge TTS supports Bangla and requires an internet connection.
          </p>
        </>
      )}
    </div>
  );
}

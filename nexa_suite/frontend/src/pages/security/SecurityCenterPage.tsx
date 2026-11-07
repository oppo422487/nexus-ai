import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import {
  getBackendPermissions,
  PermissionItemDto,
  updateBackendPermission,
} from "@/lib/backendAssistantClient";
import { PageHero } from "@/components/ui";

export function SecurityCenterPage() {
  const [permissions, setPermissions] = useState<PermissionItemDto[]>([]);
  const [lockedPermissions, setLockedPermissions] = useState<PermissionItemDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await getBackendPermissions();
      setPermissions(response.permissions);
      setLockedPermissions(response.locked_permissions);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "Permission state could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleToggle = async (permission: PermissionItemDto) => {
    setSavingKey(permission.key);
    setErrorMessage(null);
    try {
      const response = await updateBackendPermission(
        permission.key,
        !permission.enabled,
      );
      if (!response.updated) {
        setErrorMessage(response.message);
      }
      await refresh();
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Permission update failed.",
      );
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <section className="page-surface system-page">
      <PageHero
        icon={<ShieldCheck />}
        eyebrow="Safety & Permissions"
        title="Security Center"
        description="Every capability is enforced server-side. Toggling a feature off blocks its backend endpoint immediately — not just the UI."
      />

      {errorMessage && <div className="backend-preview-error">{errorMessage}</div>}
      {loading && permissions.length === 0 && (
        <div className="command-history-empty">Loading permission state...</div>
      )}

      <div className="security-grid">
        {permissions.map((permission) => (
          <div className="security-card" key={permission.key}>
            <div>
              <h4>{permission.label}</h4>
              <p>{permission.description}</p>
            </div>
            <button
              type="button"
              className={`security-toggle${permission.enabled ? " on" : ""}`}
              onClick={() => void handleToggle(permission)}
              disabled={savingKey === permission.key}
            >
              {savingKey === permission.key
                ? "..."
                : permission.enabled
                ? "Enabled"
                : "Disabled"}
            </button>
          </div>
        ))}
      </div>

      <div className="danger-zone">
        <p className="eyebrow">Locked Off — Cannot Be Enabled</p>
        <h4>These capabilities are permanently blocked by safety policy.</h4>
        <div className="security-locked-grid">
          {lockedPermissions.map((permission) => (
            <div className="security-locked-row" key={permission.key}>
              <strong>{permission.label}</strong>
              <p>{permission.description}</p>
              <span className="security-locked-badge">Locked</span>
            </div>
          ))}
        </div>
        <p>
          Dangerous commands (delete, format, shutdown, system32, registry, cmd,
          powershell and their Bangla equivalents) are blocked server-side even
          when a request claims user confirmation.
        </p>
      </div>
    </section>
  );
}

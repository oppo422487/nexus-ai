import { getBackendCommandHealth } from "./backendCommandClient";
import { getBackendAuditHealth, getBackendAuditMigrationPreview } from "./backendAuditClient";
import { getBackendDatabaseStatus } from "./backendDatabaseClient";

export type BackendSystemStatusModule = {
  key: string;
  label: string;
  ok: boolean;
  status: string;
  phase?: string;
  message?: string;
  error?: string;
};

export type BackendSystemStatusSummary = {
  checkedAt: string;
  overallOk: boolean;
  modules: BackendSystemStatusModule[];
};

export async function getBackendSystemStatus(): Promise<BackendSystemStatusSummary> {
  const modules: BackendSystemStatusModule[] = [];

  // 1. Command Preview
  try {
    const cmd = await getBackendCommandHealth();
    modules.push({
      key: "commands",
      label: "Command Preview",
      ok: cmd.execution_enabled === false,
      status: cmd.status,
      phase: cmd.phase,
      message: "Command preview route is online.",
    });
  } catch (err) {
    modules.push({
      key: "commands",
      label: "Command Preview",
      ok: false,
      status: "offline",
      error: err instanceof Error ? err.message : "Failed to reach command health.",
    });
  }

  // 2. Audit Preview
  try {
    const audit = await getBackendAuditHealth();
    modules.push({
      key: "audit",
      label: "Audit Preview",
      ok: audit.execution_enabled === false,
      status: audit.status,
      phase: audit.phase,
      message: audit.message ?? "Audit route is online.",
    });
  } catch (err) {
    modules.push({
      key: "audit",
      label: "Audit Preview",
      ok: false,
      status: "offline",
      error: err instanceof Error ? err.message : "Failed to reach audit health.",
    });
  }

  // 3. Migration Preview
  try {
    const mig = await getBackendAuditMigrationPreview();
    modules.push({
      key: "migration",
      label: "Migration Preview",
      ok: mig.can_run === false && mig.execution_enabled === false,
      status: mig.status,
      message: mig.preview_message,
    });
  } catch (err) {
    modules.push({
      key: "migration",
      label: "Migration Preview",
      ok: false,
      status: "offline",
      error: err instanceof Error ? err.message : "Failed to reach migration preview.",
    });
  }

  // 4. Local Database
  try {
    const db = await getBackendDatabaseStatus();
    modules.push({
      key: "database",
      label: "Local Database",
      ok: db.database_enabled === false && db.execution_enabled === false,
      status: db.status,
      phase: db.phase,
      message: db.reason,
    });
  } catch (err) {
    modules.push({
      key: "database",
      label: "Local Database",
      ok: false,
      status: "offline",
      error: err instanceof Error ? err.message : "Failed to reach database status.",
    });
  }

  return {
    checkedAt: new Date().toISOString(),
    overallOk: modules.every((m) => m.ok),
    modules,
  };
}

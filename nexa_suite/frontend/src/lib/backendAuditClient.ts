import type { CommandHistoryEntry } from "./commandHistory";
import { DEFAULT_BACKEND_URL } from "./backendCommandClient";

export type BackendAuditPreviewRequest = {
  source: string;
  original_text: string;
  intent: string;
  language: string;
  confidence: number;
  risk_level: string;
  action_status?: string | null;
  backend_status?: string | null;
  can_execute: boolean;
  summary: string;
  created_at?: string | null;
};

export type BackendAuditPreviewResponse = {
  status: string;
  audit_id: string;
  stored: boolean;
  execution_enabled: boolean;
  message: string;
  source: string;
  intent: string;
  risk_level: string;
};

export type BackendAuditHealthResponse = {
  status: string;
  module: string;
  phase: string;
  storage_enabled: boolean;
  execution_enabled: boolean;
  storage_mode?: string;
  message?: string;
};

export function commandHistoryEntryToAuditRequest(
  entry: CommandHistoryEntry,
): BackendAuditPreviewRequest {
  return {
    source: entry.source,
    original_text: entry.originalText,
    intent: entry.intent,
    language: entry.language,
    confidence: entry.confidence,
    risk_level: entry.riskLevel,
    action_status: entry.actionStatus ?? null,
    backend_status: entry.backendStatus ?? null,
    can_execute: entry.canExecute,
    summary: entry.summary,
    created_at: entry.createdAt,
  };
}

export async function getBackendAuditHealth(
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendAuditHealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/audit/health`);
  } catch {
    throw new Error(
      `Failed to reach backend audit health at ${backendUrl}/api/audit/health`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend audit health request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendAuditHealthResponse>;
}

export type BackendAuditMigrationPreviewResponse = {
  status: string;
  script_path: string;
  exists: boolean;
  can_run: boolean;
  migrations_enabled: boolean;
  statement_count: number;
  table_name: string;
  preview_message: string;
  safety_notes: string[];
  execution_enabled: boolean;
};

export async function getBackendAuditMigrationPreview(
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendAuditMigrationPreviewResponse> {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/audit/migration/preview`);
  } catch {
    throw new Error(
      `Failed to reach backend audit migration preview at ${backendUrl}/api/audit/migration/preview`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend audit migration preview request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendAuditMigrationPreviewResponse>;
}

export async function requestBackendAuditPreview(
  entry: CommandHistoryEntry,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendAuditPreviewResponse> {
  const body = commandHistoryEntryToAuditRequest(entry);

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/audit/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `Failed to reach backend audit preview at ${backendUrl}/api/audit/preview`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend audit preview request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendAuditPreviewResponse>;
}

import type { CommandUnderstandingResult } from "./commandUnderstanding";

export type BackendCommandPreviewRequest = {
  original_text: string;
  normalized_text?: string | null;
  intent: string;
  language: string;
  confidence: number;
  risk_level: string;
  entities: Record<string, string>;
  confirmation_reason?: string | null;
};

export type BackendCommandPreviewResponse = {
  status: string;
  can_execute: boolean;
  execution_mode: string;
  message: string;
  intent: string;
  risk_level: string;
  preview_steps: string[];
  warning?: string | null;
  blocked_reason?: string | null;
};

export type BackendCommandHealthResponse = {
  status: string;
  module: string;
  phase: string;
  execution_enabled: boolean;
};

export const DEFAULT_BACKEND_URL = "http://127.0.0.1:8766";

export function commandResultToBackendRequest(
  result: CommandUnderstandingResult,
): BackendCommandPreviewRequest {
  return {
    original_text: result.originalText,
    normalized_text: result.normalizedText,
    intent: result.intent,
    language: result.language,
    confidence: result.confidence,
    risk_level: result.riskLevel,
    entities: result.entities,
    confirmation_reason: result.confirmationReason,
  };
}

export async function getBackendCommandHealth(
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendCommandHealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/commands/health`);
  } catch {
    throw new Error(
      `Failed to reach backend command health at ${backendUrl}/api/commands/health`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend command health request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendCommandHealthResponse>;
}

export async function requestBackendCommandPreview(
  result: CommandUnderstandingResult,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendCommandPreviewResponse> {
  const body = commandResultToBackendRequest(result);

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/commands/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `Failed to reach backend command preview at ${backendUrl}/api/commands/preview`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend command preview request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendCommandPreviewResponse>;
}

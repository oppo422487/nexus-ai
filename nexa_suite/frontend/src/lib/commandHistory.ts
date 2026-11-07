import type { CommandUnderstandingResult } from "./commandUnderstanding";
import type { ActionPreview } from "./actionPreview";
import type { BackendCommandPreviewResponse } from "./backendCommandClient";

export type CommandHistorySource =
  | "commands_page"
  | "voice_page"
  | "backend_preview"
  | "manual_test";

export type CommandHistoryEntry = {
  id: string;
  source: CommandHistorySource;
  originalText: string;
  intent: string;
  language: string;
  confidence: number;
  riskLevel: string;
  actionStatus?: string;
  backendStatus?: string;
  canExecute: false;
  createdAt: string;
  summary: string;
};

export const COMMAND_HISTORY_STORAGE_KEY = "nexa-ai:command-history";

type CreateEntryArgs = {
  source: CommandHistorySource;
  result: CommandUnderstandingResult;
  actionPreview?: ActionPreview;
  backendPreview?: BackendCommandPreviewResponse;
};

export function createCommandHistoryEntry(
  args: CreateEntryArgs,
): CommandHistoryEntry {
  const { source, result, actionPreview, backendPreview } = args;

  return {
    id: `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    source,
    originalText: result.originalText,
    intent: result.intent,
    language: result.language,
    confidence: result.confidence,
    riskLevel: result.riskLevel,
    actionStatus: actionPreview?.status,
    backendStatus: backendPreview?.status,
    canExecute: false,
    createdAt: new Date().toISOString(),
    summary: `[${result.intent}] command from ${source} saved as preview-only history.`,
  };
}

export function loadCommandHistory(): CommandHistoryEntry[] {
  try {
    const raw = localStorage.getItem(COMMAND_HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CommandHistoryEntry[];
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

export function saveCommandHistoryEntry(
  entry: CommandHistoryEntry,
): CommandHistoryEntry[] {
  try {
    const history = loadCommandHistory();
    history.unshift(entry);
    const trimmed = history.slice(0, 50);
    localStorage.setItem(COMMAND_HISTORY_STORAGE_KEY, JSON.stringify(trimmed));
    return trimmed;
  } catch {
    return [entry];
  }
}

export function deleteCommandHistoryEntry(id: string): CommandHistoryEntry[] {
  try {
    const history = loadCommandHistory();
    const updated = history.filter((entry) => entry.id !== id);
    if (updated.length === history.length) return history;
    localStorage.setItem(COMMAND_HISTORY_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return loadCommandHistory();
  }
}

export function clearCommandHistory(): void {
  try {
    localStorage.removeItem(COMMAND_HISTORY_STORAGE_KEY);
  } catch {
    // localStorage unavailable
  }
}

export function getLatestCommandHistory(limit = 10): CommandHistoryEntry[] {
  return loadCommandHistory().slice(0, limit);
}

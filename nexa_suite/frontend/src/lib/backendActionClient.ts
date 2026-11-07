import { DEFAULT_BACKEND_URL } from "./backendCommandClient";

export type ActionTargetDto = {
  kind: string;
  value: string;
  label?: string | null;
};

export type ActionExecutionRequestDto = {
  request_id?: string | null;
  intent: "open_website" | "open_app" | "file_search" | "noop" | "blocked";
  target?: ActionTargetDto | null;
  original_text: string;
  normalized_text?: string | null;
  confidence?: number;
  safety_level?: "safe" | "confirmation_required" | "sensitive" | "blocked";
  user_confirmed?: boolean;
  dry_run?: boolean;
  source?: string;
};

export type ActionExecutionResponseDto = {
  request_id?: string | null;
  status: "pending_confirmation" | "executed" | "blocked" | "failed" | "preview_only";
  intent: string;
  target?: ActionTargetDto | null;
  safety_level: string;
  can_execute: boolean;
  executed: boolean;
  dry_run: boolean;
  user_confirmed: boolean;
  message: string;
  error?: string | null;
  preview_steps?: string[];
};

export type ActionHealthResponseDto = {
  status: string;
  module: string;
  phase: string;
  website_execution_available: boolean;
  app_execution_available: boolean;
  file_search_available: boolean;
  requires_confirmation: boolean;
};

export async function getBackendActionHealth(
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<ActionHealthResponseDto> {
  const response = await fetch(`${backendUrl}/api/actions/health`);
  if (!response.ok) {
    throw new Error(
      `Backend action health request failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<ActionHealthResponseDto>;
}

export async function requestOpenWebsiteAction(
  request: ActionExecutionRequestDto,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<ActionExecutionResponseDto> {
  const response = await fetch(`${backendUrl}/api/actions/website/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(
      `Backend website open request failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<ActionExecutionResponseDto>;
}

export async function requestOpenAppAction(
  request: ActionExecutionRequestDto,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<ActionExecutionResponseDto> {
  const response = await fetch(`${backendUrl}/api/actions/app/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(
      `Backend app open request failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<ActionExecutionResponseDto>;
}

export function buildAppActionRequest(args: {
  targetValue: string;
  label?: string;
  originalText: string;
  normalizedText?: string;
  confidence?: number;
  userConfirmed?: boolean;
  dryRun?: boolean;
  source?: string;
}): ActionExecutionRequestDto {
  return {
    intent: "open_app",
    target: { kind: "app", value: args.targetValue, label: args.label ?? null },
    original_text: args.originalText,
    normalized_text: args.normalizedText ?? null,
    confidence: args.confidence ?? 0,
    safety_level: "confirmation_required",
    user_confirmed: args.userConfirmed ?? false,
    dry_run: args.dryRun ?? true,
    source: args.source ?? "commands_page",
  };
}

export type FileSearchScopeDto = "desktop" | "downloads" | "documents" | "all_safe";

export type FileSearchRequestDto = {
  request_id?: string | null;
  query: string;
  scope?: FileSearchScopeDto;
  extensions?: string[];
  max_results?: number;
  original_text?: string | null;
  source?: string;
  dry_run?: boolean;
};

export type FileSearchResultItemDto = {
  name: string;
  path: string;
  extension?: string | null;
  size_bytes?: number | null;
  modified_at?: string | null;
  is_directory: boolean;
};

export type FileSearchResponseDto = {
  request_id?: string | null;
  status: "preview_only" | "completed" | "blocked" | "failed";
  query: string;
  scope: FileSearchScopeDto;
  risk_level: "safe" | "blocked";
  searched: boolean;
  result_count: number;
  results: FileSearchResultItemDto[];
  message: string;
  error?: string | null;
  safety_notes?: string[];
};

export async function requestFileSearchAction(
  request: FileSearchRequestDto,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<FileSearchResponseDto> {
  const response = await fetch(`${backendUrl}/api/actions/files/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(
      `Backend file search request failed with status ${response.status}`,
    );
  }
  return response.json() as Promise<FileSearchResponseDto>;
}

export function buildFileSearchRequest(args: {
  query: string;
  scope?: FileSearchScopeDto;
  extensions?: string[];
  maxResults?: number;
  originalText?: string;
  source?: string;
  dryRun?: boolean;
}): FileSearchRequestDto {
  return {
    query: args.query,
    scope: args.scope ?? "all_safe",
    extensions: args.extensions ?? [],
    max_results: args.maxResults ?? 20,
    original_text: args.originalText ?? null,
    source: args.source ?? "commands_page",
    dry_run: args.dryRun ?? false,
  };
}

export function buildWebsiteActionRequest(args: {
  targetValue: string;
  label?: string;
  originalText: string;
  normalizedText?: string;
  confidence?: number;
  userConfirmed?: boolean;
  dryRun?: boolean;
  source?: string;
}): ActionExecutionRequestDto {
  return {
    intent: "open_website",
    target: { kind: "url", value: args.targetValue, label: args.label ?? null },
    original_text: args.originalText,
    normalized_text: args.normalizedText ?? null,
    confidence: args.confidence ?? 0,
    safety_level: "confirmation_required",
    user_confirmed: args.userConfirmed ?? false,
    dry_run: args.dryRun ?? true,
    source: args.source ?? "commands_page",
  };
}

/* ============================================================================
   MULTI-LLM · ERRORS
   ----------------------------------------------------------------------------
   A single error type + classifier so the router's failover decision never
   depends on provider-specific error shapes. Providers translate their failures
   into an LLMError; the router only looks at `kind`.
   ========================================================================== */

export type LLMErrorKind =
  | "rate-limit" // 429 / rate limited
  | "quota" // quota / billing exceeded
  | "unavailable" // 5xx / provider down / network
  | "timeout" // request aborted by timeout
  | "auth" // 401 / 403 — bad or missing key
  | "bad-request" // 400 — our request was malformed
  | "unknown";

/** Error kinds that should trigger automatic failover to the next provider. */
const FAILOVER_KINDS: ReadonlySet<LLMErrorKind> = new Set<LLMErrorKind>([
  "rate-limit",
  "quota",
  "unavailable",
  "timeout",
  "auth",
]);

export class LLMError extends Error {
  readonly kind: LLMErrorKind;
  readonly status?: number;

  constructor(kind: LLMErrorKind, message: string, status?: number) {
    super(message);
    this.name = "LLMError";
    this.kind = kind;
    this.status = status;
  }

  /** Whether this failure should hand off to the next provider. */
  get isFailover(): boolean {
    return FAILOVER_KINDS.has(this.kind);
  }
}

/** Short human label for a failover reason (used in toasts). */
export function reasonLabel(kind: LLMErrorKind): string {
  switch (kind) {
    case "rate-limit":
      return "rate limit reached";
    case "quota":
      return "quota reached";
    case "unavailable":
      return "unavailable";
    case "timeout":
      return "timed out";
    case "auth":
      return "authentication failed";
    default:
      return "failed";
  }
}

/** Classify an HTTP status + optional body into an LLMErrorKind. */
export function classifyHttp(status: number, bodyText = ""): LLMErrorKind {
  const body = bodyText.toLowerCase();
  if (status === 429) {
    return body.includes("quota") || body.includes("billing") || body.includes("insufficient")
      ? "quota"
      : "rate-limit";
  }
  if (status === 401 || status === 403) return "auth";
  if (status === 400) {
    return body.includes("quota") || body.includes("exceeded") ? "quota" : "bad-request";
  }
  if (status >= 500) return "unavailable";
  if (body.includes("quota") || body.includes("exceeded")) return "quota";
  if (body.includes("rate limit")) return "rate-limit";
  return "unknown";
}

/** Normalise any thrown value into an LLMError (network/abort aware). */
export function toLLMError(err: unknown): LLMError {
  if (err instanceof LLMError) return err;
  if (err instanceof DOMException && err.name === "AbortError") {
    return new LLMError("timeout", "Request timed out");
  }
  if (err instanceof TypeError) {
    // fetch throws TypeError on network failure / CORS
    return new LLMError("unavailable", err.message || "Network error");
  }
  const message = err instanceof Error ? err.message : String(err);
  return new LLMError("unknown", message);
}

/** Read a Response body as text without throwing. */
export async function safeBodyText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

/** fetch with an AbortController-backed timeout, chained to a caller signal. */
export async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  signal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onAbort);
  }
}

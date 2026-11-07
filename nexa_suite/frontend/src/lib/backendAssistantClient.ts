/**
 * Backend clients for the assistant feature endpoints:
 * permissions, STT engines/transcription, TTS, web answers,
 * document preview, reminders, chat, and the real audit event log.
 */
import { DEFAULT_BACKEND_URL } from "./backendCommandClient";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function sendJson<T>(url: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/* ---------------- Permissions ---------------- */

export type PermissionItemDto = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
  locked: boolean;
};

export type PermissionsResponseDto = {
  status: string;
  module: string;
  permissions: PermissionItemDto[];
  locked_permissions: PermissionItemDto[];
  message: string;
};

export type PermissionUpdateResponseDto = {
  status: string;
  key: string;
  enabled: boolean;
  updated: boolean;
  message: string;
};

export function getBackendPermissions(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<PermissionsResponseDto>(`${backendUrl}/api/permissions`);
}

export function updateBackendPermission(
  key: string,
  enabled: boolean,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<PermissionUpdateResponseDto>(
    `${backendUrl}/api/permissions`,
    "PUT",
    { key, enabled },
  );
}

/* ---------------- Local WhatsApp contacts ---------------- */

export type ContactItemDto = {
  name: string;
  phone_number: string;
  email_address?: string | null;
  nickname?: string | null;
  aliases: string[];
  relationship: string;
  default_tone: string;
  created_at: string;
  updated_at: string;
};

export type ContactListResponseDto = {
  status: string;
  contacts: ContactItemDto[];
  storage: string;
  message: string;
};

export type ContactMutationResponseDto = {
  status: string;
  ok: boolean;
  contact?: ContactItemDto | null;
  message: string;
  error?: string | null;
};

export function getBackendContacts(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<ContactListResponseDto>(`${backendUrl}/api/contacts`);
}

export function saveBackendContact(
  input: {
    name: string;
    phone_number: string;
    email_address?: string | null;
    nickname?: string | null;
    aliases?: string[];
    relationship?: string | null;
    default_tone?: string | null;
  },
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ContactMutationResponseDto>(
    `${backendUrl}/api/contacts`,
    "POST",
    input,
  );
}

export function deleteBackendContact(name: string, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<ContactMutationResponseDto>(
    `${backendUrl}/api/contacts/${encodeURIComponent(name)}`,
    "DELETE",
  );
}

/* ---------------- Voice: STT ---------------- */

export type SttEngineInfoDto = {
  name: string;
  label: string;
  dependency_installed: boolean;
  model_available: boolean;
  ready: boolean;
  message: string;
};

export type SttEnginesResponseDto = {
  status: string;
  preferred_engine: string;
  engines: SttEngineInfoDto[];
  execution_enabled: boolean;
  message: string;
};

export type TranscriptionResponseDto = {
  status: string;
  engine: string;
  transcribed: boolean;
  text: string;
  language?: string | null;
  execution_enabled: boolean;
  message: string;
  warning?: string | null;
  error?: string | null;
};

export function getBackendSttEngines(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<SttEnginesResponseDto>(`${backendUrl}/api/voice/stt/engines`);
}

export async function transcribeAudioBlob(
  blob: Blob,
  filename = "push-to-talk.wav",
  backendUrl = DEFAULT_BACKEND_URL,
  language = "bn-BD",
): Promise<TranscriptionResponseDto> {
  const form = new FormData();
  form.append("audio", blob, filename);
  const response = await fetch(`${backendUrl}/api/voice/stt/transcribe?language=${encodeURIComponent(language)}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`Transcription request failed with status ${response.status}`);
  }
  return response.json() as Promise<TranscriptionResponseDto>;
}

/* ---------------- Voice: TTS ---------------- */

export type TtsStatusResponseDto = {
  status: string;
  dependency_installed: boolean;
  available: boolean;
  enabled: boolean;
  voices: Array<{ id: string; name: string; languages: string[] }>;
  message: string;
  error?: string | null;
};

export type TtsSpeakResponseDto = {
  status: string;
  spoken: boolean;
  message: string;
  error?: string | null;
};

export function getBackendTtsStatus(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<TtsStatusResponseDto>(`${backendUrl}/api/voice/tts/status`);
}

export type CartesiaStatusDto = { configured: boolean; provider: string; model: string; voice_bn: string; voice_en: string; key_masked: string };
export type CartesiaVoiceDto = { id: string; name: string };

export function getCartesiaStatus(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<CartesiaStatusDto>(`${backendUrl}/api/voice/tts/cartesia/status`);
}
export function saveCartesiaKey(apiKey: string, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<CartesiaStatusDto & { ok: boolean; message: string }>(`${backendUrl}/api/voice/tts/cartesia/key`, "PUT", { api_key: apiKey });
}
export function removeCartesiaKey(backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<CartesiaStatusDto & { ok: boolean; message: string }>(`${backendUrl}/api/voice/tts/cartesia/key`, "DELETE");
}
export function getCartesiaVoices(language: "bn" | "en", backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<{ ok: boolean; voices: CartesiaVoiceDto[]; message: string }>(`${backendUrl}/api/voice/tts/cartesia/voices?language=${language}`);
}
export function setCartesiaVoice(language: "bn" | "en", voiceId: string, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<CartesiaStatusDto & { ok: boolean; message: string }>(`${backendUrl}/api/voice/tts/cartesia/voice`, "PUT", { language, voice_id: voiceId });
}

export async function requestPreferredTtsAudio(text: string, edgeVoice: string, backendUrl = DEFAULT_BACKEND_URL, rate = "+0%"):
  Promise<{ blob: Blob; provider: string; fallbackReason: string | null }> {
  const response = await fetch(`${backendUrl}/api/voice/tts/audio`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language: /[\u0980-\u09ff]/u.test(text) ? "bn" : "en", edge_voice: edgeVoice, rate }),
  });
  if (!response.ok) throw new Error(`TTS failed with status ${response.status}`);
  if (!(response.headers.get("content-type") || "").includes("audio")) {
    const result = await response.json() as { error?: string; message?: string };
    throw new Error(result.error || result.message || "TTS unavailable.");
  }
  return { blob: await response.blob(), provider: response.headers.get("X-TTS-Provider") || "unknown", fallbackReason: response.headers.get("X-TTS-Fallback-Reason") };
}

export async function requestTtsSpeak(
  text: string,
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<TtsSpeakResponseDto> {
  const voice = /[\u0980-\u09ff]/u.test(text) ? "bn-BD-NabanitaNeural" : "en-US-AriaNeural";
  const { blob, provider, fallbackReason } = await requestPreferredTtsAudio(text, voice, backendUrl);
  const url = URL.createObjectURL(blob);
  try {
    const audio = new Audio(url);
    await new Promise<void>((resolve, reject) => {
      audio.addEventListener("ended", () => resolve(), { once: true });
      audio.addEventListener("error", () => reject(new Error("Online TTS audio playback failed.")), { once: true });
      audio.play().catch(reject);
    });
    return { status: "completed", spoken: true, message: provider === "cartesia" ? "Spoken through Cartesia Sonic." : `Spoken through Edge fallback.${fallbackReason ? ` ${fallbackReason}` : ""}` };
  } finally {
    URL.revokeObjectURL(url);
  }
}

/* ---------------- Advanced YouTube controller ---------------- */

export type YouTubePlayerStateDto = {
  available: boolean;
  launched: boolean;
  playing: boolean;
  muted: boolean;
  title: string;
  current_time: number;
  duration: number;
  volume: number;
  playback_rate: number;
  timer_remaining_seconds?: number | null;
  current_url: string;
};

export type YouTubeCommandResponseDto = {
  status: string;
  module: string;
  action: string;
  executed: boolean;
  requires_confirmation: boolean;
  message: string;
  state?: YouTubePlayerStateDto | null;
  error?: string | null;
};

export type YouTubeCapabilitiesResponseDto = {
  status: string;
  module: string;
  available: boolean;
  enabled: boolean;
  actions: string[];
  message: string;
};

export function getYouTubeCapabilities(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<YouTubeCapabilitiesResponseDto>(`${backendUrl}/api/youtube/capabilities`);
}

export function getYouTubeStatus(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<YouTubeCommandResponseDto>(`${backendUrl}/api/youtube/status`);
}

export function requestYouTubeCommand(
  input: {
    action?: string;
    command?: string;
    query?: string | null;
    value?: number | null;
    enabled?: boolean | null;
    user_confirmed?: boolean;
    source?: string;
  },
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<YouTubeCommandResponseDto>(
    `${backendUrl}/api/youtube/command`,
    "POST",
    {
      action: "auto",
      command: "",
      user_confirmed: true,
      source: "youtube_panel",
      ...input,
    },
  );
}

/* ---------------- Optional image generation ---------------- */

export type ImageGenerationHealthDto = {
  status: string;
  available: boolean;
  enabled: boolean;
  model: string;
  message: string;
};

export type ImageGenerationResponseDto = {
  status: string;
  generated: boolean;
  prompt: string;
  image_id?: string | null;
  image_url?: string | null;
  provider: string;
  model?: string | null;
  message: string;
  error?: string | null;
};

export function getImageGenerationHealth(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<ImageGenerationHealthDto>(`${backendUrl}/api/images/health`);
}

export function requestImageGeneration(
  prompt: string,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ImageGenerationResponseDto>(
    `${backendUrl}/api/images/generate`,
    "POST",
    { prompt, width: 768, height: 768, user_confirmed: true },
  );
}

export function queueImageGeneration(prompt: string, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<{ status: string; queued: boolean; message?: string; job?: { id: string; status: string; prompt: string } }>(
    `${backendUrl}/api/images/queue`, "POST", { prompt, width: 768, height: 768, user_confirmed: true },
  );
}

export function getImageJobs(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<{ status: string; jobs: Array<{ id: string; status: string; prompt: string; image_url?: string | null; error?: string | null }> }>(`${backendUrl}/api/images/jobs`);
}

export function getImageHistory(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<{ status: string; images: Array<{ id: string; image_url: string; created_at: string }> }>(`${backendUrl}/api/images/history`);
}

export function exportContent(title: string, content: string, format: "txt" | "md", backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<{ status: string; exported: boolean; download_url?: string | null; message: string; error?: string | null }>(
    `${backendUrl}/api/content/export`, "POST", { title, content, format, user_confirmed: true },
  );
}

export function getContentHistory(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<{ status: string; documents: Array<{ id: string; name: string; size: number; download_url: string }> }>(`${backendUrl}/api/content/history`);
}

export function getAuditStatistics(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<{ status: string; total_events: number; sample_size: number; by_status: Record<string, number>; by_intent: Record<string, number>; by_source: Record<string, number> }>(`${backendUrl}/api/audit/stats`);
}

export function updateBackendReminder(
  reminderId: string,
  input: { title?: string; note?: string; due_at?: string; recurrence?: string },
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(`${backendUrl}/api/reminders/${encodeURIComponent(reminderId)}`, "PUT", { ...input, user_confirmed: true });
}

export async function requestEdgeTtsAudio(
  text: string,
  voice: string,
  backendUrl = DEFAULT_BACKEND_URL,
  rate = "+0%",
): Promise<Blob> {
  const response = await fetch(`${backendUrl}/api/voice/tts/edge/audio`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, voice, rate }),
  });
  if (!response.ok) throw new Error(`Edge TTS failed with status ${response.status}`);
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("audio")) {
    const result = await response.json() as { error?: string; message?: string };
    throw new Error(result.error || result.message || "Edge TTS unavailable.");
  }
  return response.blob();
}

/* ---------------- Whitelisted Windows controls ---------------- */

export type SystemControlsHealthDto = {
  status: string;
  available: boolean;
  enabled: boolean;
  closeable_apps: Array<{ key: string; label: string }>;
};

export type SystemControlResponseDto = {
  status: string;
  action: string;
  executed: boolean;
  message: string;
  error?: string | null;
};

export function getSystemControlsHealth(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<SystemControlsHealthDto>(`${backendUrl}/api/system-controls/health`);
}

/* ---------------- Productivity hub, skills and diagnostics ---------------- */

export type ProductivitySkillDto = { id: string; name: string; status: string; description: string };
export type ProductivityItemDto = Record<string, string | null>;
export type ProductivityDashboardDto = {
  status: string;
  skills: ProductivitySkillDto[];
  memories: ProductivityItemDto[];
  notes: ProductivityItemDto[];
  calendar_events: ProductivityItemDto[];
  drafts: ProductivityItemDto[];
  voice_profiles: ProductivityItemDto[];
};
export type ProductivityDiagnosticsDto = {
  status: string;
  backend: string;
  permissions: Record<string, boolean>;
  checks: Array<{ name: string; ok: boolean }>;
};

export function getProductivityDashboard(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<ProductivityDashboardDto>(`${backendUrl}/api/productivity/dashboard`);
}

export function getProductivityDiagnostics(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<ProductivityDiagnosticsDto>(`${backendUrl}/api/productivity/diagnostics`);
}

export function createProductivityItem(
  input: { kind: string; text: string; recipient?: string; subject?: string; start_at?: string | null; wake_word?: string; language?: string },
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<{ status: string; created: boolean; item?: ProductivityItemDto; message: string }>(
    `${backendUrl}/api/productivity/items`, "POST", { ...input, user_confirmed: true },
  );
}

export function requestSystemControl(
  action: "volume_up" | "volume_down" | "mute" | "play_pause" | "next_track" | "previous_track" | "close_app",
  target?: string | null,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<SystemControlResponseDto>(
    `${backendUrl}/api/system-controls/execute`,
    "POST",
    { action, target: target ?? null, user_confirmed: true },
  );
}

/* ---------------- Web answers ---------------- */

export type WebAnswerResponseDto = {
  status: string;
  answered: boolean;
  question: string;
  answer: string;
  source?: string | null;
  source_url?: string | null;
  execution_enabled: boolean;
  message: string;
  error?: string | null;
};

export function requestWebAnswer(
  question: string,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<WebAnswerResponseDto>(
    `${backendUrl}/api/web/answer`,
    "POST",
    { question },
  );
}

/* ---------------- Chat ---------------- */

export type ChatHistoryItemDto = {
  role: "user" | "assistant" | string;
  content: string;
};

export type ChatWeatherSnapshotDto = {
  location: string;
  temperature_c?: number | null;
  condition?: string | null;
  wind_kph?: number | null;
  humidity_percent?: number | null;
};

export type ChatSearchResultDto = {
  title: string;
  snippet: string;
  source_url?: string | null;
  provider: string;
  confidence: string;
};

export type ChatActionStatusDto = {
  kind: string;
  target: string;
  label: string;
  executed: boolean;
  requires_confirmation: boolean;
  message: string;
  recipient?: string | null;
  draft_text?: string | null;
  action_label?: string | null;
};

export type ChatPendingTaskDto = {
  kind: string;
  status_label: string;
  prompt: string;
  recipient?: string | null;
  message?: string | null;
  expires_at?: string | null;
};

export type ChatMessageResponseDto = {
  status: string;
  module: string;
  intent: string;
  message: string;
  answer: string;
  blocked: boolean;
  requires_confirmation: boolean;
  execution_enabled: boolean;
  provider?: string | null;
  source?: string | null;
  source_url?: string | null;
  chips: string[];
  sources: string[];
  weather?: ChatWeatherSnapshotDto | null;
  search_results: ChatSearchResultDto[];
  show_search_results_by_default: boolean;
  action?: ChatActionStatusDto | null;
  pending_task?: ChatPendingTaskDto | null;
  confidence?: string | null;
  live_data: boolean;
  live_data_warning: boolean;
  auto_execute_safe: boolean;
  llm_used: boolean;
  llm_provider?: string | null;
  fallback_used: boolean;
  source_type: "local" | "search" | "tool" | "llm" | "hybrid" | string;
  error?: string | null;
};

export function requestChatMessage(
  message: string,
  history: ChatHistoryItemDto[] = [],
  addressStyle?: string,
  whatsappDraftOpenTarget = "auto",
  source = "chat_page",
  backendUrl = DEFAULT_BACKEND_URL,
  preferredLanguage = "auto",
) {
  return sendJson<ChatMessageResponseDto>(
    `${backendUrl}/api/chat/message`,
    "POST",
    {
      message,
      history,
      source,
      address_style: addressStyle,
      preferred_language: preferredLanguage,
      whatsapp_draft_open_target: whatsappDraftOpenTarget,
    },
  );
}

/* ---------------- Documents ---------------- */

export type DocumentPreviewResponseDto = {
  status: string;
  previewed: boolean;
  path: string;
  name: string;
  extension?: string | null;
  size_bytes?: number | null;
  page_count?: number | null;
  preview_text: string;
  truncated: boolean;
  read_only: boolean;
  message: string;
  safety_notes: string[];
  error?: string | null;
};

export function requestDocumentPreview(
  path: string,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<DocumentPreviewResponseDto>(
    `${backendUrl}/api/documents/preview`,
    "POST",
    { path },
  );
}

/* ---------------- Reminders ---------------- */

export type ReminderItemDto = {
  id: string;
  title: string;
  note: string;
  due_at?: string | null;
  status: string;
  created_at: string;
  recurrence?: string;
  last_triggered_at?: string | null;
};

export type ReminderListResponseDto = {
  status: string;
  reminders: ReminderItemDto[];
  due_now: ReminderItemDto[];
  message: string;
};

export type ReminderMutationResponseDto = {
  status: string;
  ok: boolean;
  reminder?: ReminderItemDto | null;
  message: string;
  error?: string | null;
};

export function getBackendReminders(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<ReminderListResponseDto>(`${backendUrl}/api/reminders`);
}

export function createBackendReminder(
  input: { title: string; note?: string; due_at?: string | null; recurrence?: string },
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(
    `${backendUrl}/api/reminders`,
    "POST",
    { ...input, user_confirmed: true },
  );
}

export function createNaturalLanguageReminder(
  text: string,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(
    `${backendUrl}/api/reminders/natural`,
    "POST",
    { text, user_confirmed: true },
  );
}

export function snoozeBackendReminder(
  reminderId: string,
  minutes = 10,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(
    `${backendUrl}/api/reminders/${encodeURIComponent(reminderId)}/snooze`,
    "POST",
    { minutes, user_confirmed: true },
  );
}

export function setBackendReminderStatus(
  reminderId: string,
  status: "done" | "dismissed" | "pending",
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(
    `${backendUrl}/api/reminders/${encodeURIComponent(reminderId)}/status?status=${status}`,
    "POST",
  );
}

export function deleteBackendReminder(
  reminderId: string,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return sendJson<ReminderMutationResponseDto>(
    `${backendUrl}/api/reminders/${encodeURIComponent(reminderId)}`,
    "DELETE",
  );
}

/* ---------------- Audit events ---------------- */

export type AuditEventDto = {
  id: number;
  created_at: string;
  source: string;
  intent: string;
  status: string;
  risk_level: string;
  target: string;
  message: string;
};

export type AuditEventsResponseDto = {
  status: string;
  storage_enabled: boolean;
  total_events: number;
  events: AuditEventDto[];
  message: string;
};

export function getBackendAuditEvents(
  limit = 50,
  backendUrl = DEFAULT_BACKEND_URL,
) {
  return getJson<AuditEventsResponseDto>(
    `${backendUrl}/api/audit/recent?limit=${limit}`,
  );
}

export type SetupCapabilityDto = {
  ready: boolean;
  dependency_installed: boolean;
  configured: boolean;
  internet_required: boolean;
  action: string;
};

export type SetupReadinessDto = {
  status: string;
  packaged_backend: boolean;
  python: string;
  all_dependencies_ready: boolean;
  capabilities: Record<"assemblyai_streaming_stt" | "image_generation" | "edge_tts" | "advanced_youtube", SetupCapabilityDto>;
};

export function getSetupReadiness(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<SetupReadinessDto>(`${backendUrl}/api/setup/readiness`);
}

export function configureHuggingFaceToken(token: string, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<{ status: string; configured: boolean; message: string }>(
    `${backendUrl}/api/setup/huggingface`,
    "POST",
    { token, user_confirmed: true },
  );
}

/* ---------------- Email ---------------- */

export type EmailStatusDto = { status: string; provider: string; sender: string; configured: boolean; confirmation_required: boolean; message: string };
export type EmailRequestDto = { recipient: string; subject: string; body: string };
export type EmailResultDto = { status: string; sent: boolean; confirmation_required?: boolean; recipient?: string; subject?: string; body?: string; provider?: string; message: string };

export function getEmailStatus(backendUrl = DEFAULT_BACKEND_URL) {
  return getJson<EmailStatusDto>(`${backendUrl}/api/email/status`);
}

export function previewEmail(input: EmailRequestDto, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<EmailResultDto>(`${backendUrl}/api/email/preview`, "POST", { ...input, user_confirmed: false });
}

export function sendConfirmedEmail(input: EmailRequestDto, backendUrl = DEFAULT_BACKEND_URL) {
  return sendJson<EmailResultDto>(`${backendUrl}/api/email/send`, "POST", { ...input, user_confirmed: true });
}

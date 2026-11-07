import { useEngine, engineCommand, EngineControls, EngineInlineTools } from "@/lib/engineRuntime";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Brain,
  Cpu,
  Globe,
  LayoutGrid,
  Lightbulb,
  Mic,
  Rocket,
  Send,
  Sparkles,
  Volume2,
  Wifi,
  Zap,
} from "lucide-react";
import {
  buildAppActionRequest,
  buildWebsiteActionRequest,
  detectAppKeyFromText,
  detectCommandIntent,
  detectFileSearchHints,
  loadProfile,
  requestOpenAppAction,
  requestOpenWebsiteAction,
} from "@/lib";
import {
  AuditEventDto,
  ChatMessageResponseDto,
  getBackendAuditEvents,
  getBackendSttEngines,
  getBackendTtsStatus,
  requestChatMessage,
  requestTtsSpeak,
  requestYouTubeCommand,
} from "@/lib/backendAssistantClient";
import { ALL_TARGETS, APP_TARGETS, SafeTarget, WEBSITE_TARGETS } from "@/lib/safeTargets";
import { PushToTalkPanel } from "@/components/voice/PushToTalkPanel";
import { YouTubeControlPanel } from "@/components/youtube";
import { ImageGenerationPanel } from "@/components/images";
import { SystemControlsPanel } from "@/components/system";
import { ContentWriterPanel } from "@/components/content";
import { PerformancePanel } from "@/components/analytics";
import type { NavId } from "@/components/shell/Sidebar";
import { useInteraction, PremiumButton, VoiceOrb } from "@/interaction";

type PendingAction = {
  type: "launch";
  target: SafeTarget;
  sourceText: string;
  recipient?: string | null;
  draftText?: string | null;
  actionLabel?: string | null;
  youtubeCommand?: string | null;
};

type ChatRole = "user" | "assistant";

type DashboardChatEntry = {
  id: string;
  role: ChatRole;
  text: string;
  createdAt: string;
  intent?: string;
  status?: string;
  provider?: string | null;
  source?: string | null;
  sourceUrl?: string | null;
  chips?: string[];
  sources?: string[];
  searchResults?: ChatMessageResponseDto["search_results"];
  showSearchResultsByDefault?: boolean;
  llmUsed?: boolean;
  llmProvider?: string | null;
  pendingAction?: PendingAction | null;
  pendingTask?: ChatMessageResponseDto["pending_task"] | null;
  actionResult?: string | null;
  actionError?: string | null;
  speaking?: boolean;
  speakMessage?: string | null;
};

const STORAGE_KEY = "nexa.dashboardChat.history";
const CLEARED_ENGINE_CURSOR_KEY = "nexa.nativeChat.clearedCursor.v1";

function readClearedEngineCursor(): { generation: string; cursor: number } {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(CLEARED_ENGINE_CURSOR_KEY) || "null");
    if (value && typeof value === "object" && "generation" in value && "cursor" in value &&
        typeof value.generation === "string" && typeof value.cursor === "number" &&
        Number.isSafeInteger(value.cursor) && value.cursor >= 0) {
      return { generation: value.generation, cursor: value.cursor };
    }
  } catch { /* Missing or malformed browser storage starts with no cleared cursor. */ }
  return { generation: "", cursor: 0 };
}

const WEBSITE_HINTS: Record<string, string[]> = {
  youtube: ["youtube", "ইউটিউব", "utube"],
  google: ["google", "গুগল"],
  github: ["github", "গিটহাব"],
  facebook: ["facebook", "ফেসবুক"],
  gmail: ["gmail", "জিমেইল"],
  chatgpt: ["chatgpt", "চ্যাটজিপিটি"],
  stackoverflow: ["stackoverflow", "stack overflow"],
};

const SUGGESTIONS = [
  "today weather in Dhaka",
  "ajker weather ki",
  "google theke search kore bolo python latest version",
  "calculator open koro",
  "delete system32",
];

function makeEntry(
  role: ChatRole,
  text: string,
  extra: Partial<DashboardChatEntry> = {},
): DashboardChatEntry {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function resolveLaunchTarget(text: string): PendingAction | null {
  const lower = text.trim().toLowerCase();
  const appKey = detectAppKeyFromText(lower);
  if (appKey) {
    const target = APP_TARGETS.find((item) => item.value === appKey);
    if (target) return { type: "launch", target, sourceText: text };
  }
  for (const target of WEBSITE_TARGETS) {
    const hints = WEBSITE_HINTS[target.value] ?? [target.value];
    if (hints.some((hint) => lower.includes(hint))) {
      return { type: "launch", target, sourceText: text };
    }
  }
  return null;
}

function pendingActionFromResponse(
  response: ChatMessageResponseDto,
  sourceText: string,
): PendingAction | null {
  if (!response.action || !response.requires_confirmation || response.action.executed) {
    return null;
  }
  const kind = response.action.kind === "app" ? "app" : "website";
  const target: SafeTarget = {
    kind,
    value: response.action.target,
    label: response.action.label,
    description: response.action.action_label ?? response.action.message,
    accent:
      response.action.kind === "whatsapp_draft"
        ? "#22c55e"
        : response.action.label.toLowerCase().includes("youtube")
        ? "#ef4444"
        : kind === "website"
        ? "#22d3ee"
        : "#818cf8",
  };
  return {
    type: "launch",
    target,
    sourceText,
    recipient: response.action.recipient,
    draftText: response.action.draft_text,
    actionLabel: response.action.action_label,
    youtubeCommand: response.action.kind === "youtube_control" ? response.action.target : null,
  };
}

function chatResponseToEntry(
  response: ChatMessageResponseDto,
  sourceText: string,
): DashboardChatEntry {
  const debugChatChips = localStorage.getItem("nexa_debug_chat_chips") === "true";
  const hideLocalConversationMeta =
    response.source === "Local conversation" &&
    response.provider?.toLowerCase().includes("local assistant") &&
    !response.search_results?.length &&
    !response.weather &&
    !response.action &&
    !debugChatChips;
  const technicalChips = new Set([
    "Whitelisted URL",
    "Trusted skill",
    "No browser automation",
    "Safe website whitelist",
    "Provider local",
    "Topic general",
    "No execution",
    "Audit recorded",
    "Trusted Quick Launch",
    "Safe whitelist",
    "Local solver",
  ]);
  const cleanChips = debugChatChips
    ? response.chips
    : response.chips.filter((chip) => !technicalChips.has(chip) && !chip.startsWith("Topic:") && !chip.startsWith("Provider:"));
  const showProvider =
    debugChatChips ||
    response.source_type === "search" ||
    response.source_type === "hybrid" ||
    response.llm_used ||
    response.intent === "weather" ||
    response.intent === "current_time";
  const showSource =
    debugChatChips ||
    response.source_type === "search" ||
    response.intent === "weather" ||
    response.intent === "current_time";
  const pendingAction =
    response.requires_confirmation && !response.auto_execute_safe && !response.action?.executed
      ? pendingActionFromResponse(response, sourceText) ?? resolveLaunchTarget(sourceText)
      : null;
  return makeEntry("assistant", response.answer, {
    intent: response.intent,
    status: response.status,
    provider: hideLocalConversationMeta || !showProvider ? undefined : response.provider,
    source: hideLocalConversationMeta || !showSource ? undefined : response.source,
    sourceUrl: hideLocalConversationMeta || (!showSource && !response.search_results?.length) ? undefined : response.source_url,
    chips: hideLocalConversationMeta
      ? []
      : response.llm_used && response.llm_provider && !cleanChips.includes(response.llm_provider)
      ? [...cleanChips, response.llm_provider]
      : cleanChips,
    sources: hideLocalConversationMeta ? [] : response.sources,
    searchResults: response.search_results,
    showSearchResultsByDefault: response.show_search_results_by_default,
    llmUsed: response.llm_used,
    llmProvider: response.llm_provider,
    pendingAction,
    pendingTask: response.pending_task,
    actionResult: response.auto_execute_safe && response.action?.executed ? response.answer : response.action?.executed ? response.action.message : null,
  });
}

export function CommandCenterPage({
  backendConnected,
  commandSeed,
  onNavigate,
}: {
  backendConnected: boolean;
  commandSeed: { text: string; ts: number; autoSpeak?: boolean; source?: string } | null;
  onNavigate: (page: NavId) => void;
}) {
  const engine = useEngine();
  const [initialClearedCursor] = useState(readClearedEngineCursor);
  const clearedCursor = useRef(initialClearedCursor);
  const { emit, notify } = useInteraction();
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<DashboardChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const [events, setEvents] = useState<AuditEventDto[]>([]);
  const [sttReady, setSttReady] = useState<boolean | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!engine.enabled || !engine.generation) return;
    const incoming = engine.events.filter(event =>
      ["user", "assistant", "context", "tool"].includes(event.kind) &&
      (clearedCursor.current.generation !== engine.generation || event.id > clearedCursor.current.cursor));
    setMessages(previous => {
      const existing = new Set(previous.map(message => message.id));
      const additions = incoming.filter(event => !existing.has(`engine-${engine.generation}-${event.id}`)).map(event =>
        makeEntry(event.kind === "user" ? "user" : "assistant", event.text, {
          id: `engine-${engine.generation}-${event.id}`,
          createdAt: new Date(event.at * 1000).toISOString(),
          chips: event.kind === "context" ? [event.label || "Context"] : event.kind === "tool" ? [event.label || "Tool result"] : [],
        }));
      return additions.length ? [...previous, ...additions].slice(-300) : previous;
    });
  }, [engine.enabled, engine.generation, engine.events]);

  const understanding = useMemo(
    () => detectCommandIntent(draft || ""),
    [draft],
  );

  const refreshEvents = () => {
    getBackendAuditEvents(40)
      .then((response) => setEvents(response.events))
      .catch(() => setEvents([]));
  };

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setMessages(JSON.parse(raw) as DashboardChatEntry[]);
    } catch {
      setMessages([]);
    }
    refreshEvents();
    getBackendSttEngines()
      .then((response) => setSttReady(response.engines.some((engine) => engine.ready)))
      .catch(() => setSttReady(false));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-40)));
    } catch {
      // Dashboard history is convenience-only.
    }
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (commandSeed?.text) {
      void sendToAssistant(commandSeed.text, { autoSpeak: commandSeed.autoSpeak, source: commandSeed.source });
    }
  }, [commandSeed]);

  const backendHistory = useMemo(
    () => messages.slice(-8).map((item) => ({ role: item.role, content: item.text })),
    [messages],
  );

  const sendToAssistant = async (
    value?: string,
    options: { autoSpeak?: boolean; source?: string } = {},
  ) => {
    const text = (value ?? draft).trim();
    if (!text || loading) return;
    setDraft("");
    setGlobalError(null);
    setLoading(true);
    window.dispatchEvent(new CustomEvent("nexa:voice-output-state", { detail: { active: true } }));

    const userEntry = makeEntry("user", text);
    if (!engine.enabled) setMessages((prev) => [...prev, userEntry]);
    emit({ type: "ai:thinking", payload: { active: true, label: "Nexa is thinking" } });

    try {
      if (engine.enabled) {
        await engineCommand("text", { text });
        return;
      }
      let whatsappDraftOpenTarget = "auto";
      try {
        const rawPrefs = localStorage.getItem("nexa.localPrefs");
        if (rawPrefs) {
          whatsappDraftOpenTarget = JSON.parse(rawPrefs).whatsappDraftOpenTarget ?? "auto";
        }
      } catch {
        whatsappDraftOpenTarget = "auto";
      }
      const response = await requestChatMessage(
        text,
        backendHistory,
        loadProfile().addressingPreference,
        whatsappDraftOpenTarget,
        options.source ?? "dashboard_text",
        undefined,
        loadProfile().languageMode,
      );
      const assistantEntry = chatResponseToEntry(response, text);
      setMessages((prev) => [...prev, assistantEntry]);
      refreshEvents();

      if ((options.autoSpeak ?? true) && response.answer.trim()) {
        setMessages((prev) =>
          prev.map((entry) =>
            entry.id === assistantEntry.id ? { ...entry, speaking: true, speakMessage: null } : entry,
          ),
        );
        try {
          const ttsStatus = await getBackendTtsStatus();
          if (!ttsStatus.enabled) {
            setMessages((prev) =>
              prev.map((entry) =>
                entry.id === assistantEntry.id
                  ? { ...entry, speaking: false, speakMessage: "TTS permission is disabled. Enable TTS in Settings/Security." }
                  : entry,
              ),
            );
          } else {
            const speech = await requestTtsSpeak(response.answer.slice(0, 380));
            setMessages((prev) =>
              prev.map((entry) =>
                entry.id === assistantEntry.id
                  ? {
                      ...entry,
                      speaking: false,
                      speakMessage: speech.spoken ? "Spoken through online neural TTS." : speech.error || speech.message,
                    }
                  : entry,
              ),
            );
          }
        } catch (err) {
          setMessages((prev) =>
            prev.map((entry) =>
              entry.id === assistantEntry.id
                ? { ...entry, speaking: false, speakMessage: err instanceof Error ? err.message : "TTS request failed." }
                : entry,
            ),
          );
        }
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? `${err.message}. Start the backend at http://127.0.0.1:8766 and try again.`
          : "Dashboard chat request failed.";
      setGlobalError(message);
      setMessages((prev) => [
        ...prev,
        makeEntry("assistant", message, {
          status: "failed",
          chips: ["Backend required", "Error"],
        }),
      ]);
      notify({ title: "Chat request failed", message: "Start the backend and try again.", tone: "error" });
    } finally {
      window.dispatchEvent(new CustomEvent("nexa:voice-output-state", { detail: { active: false } }));
      window.dispatchEvent(new CustomEvent("nexa:voice-turn-complete"));
      emit({ type: "ai:thinking", payload: { active: false } });
      setLoading(false);
    }
  };

  const updateMessage = (id: string, patch: Partial<DashboardChatEntry>) => {
    setMessages((prev) =>
      prev.map((entry) => (entry.id === id ? { ...entry, ...patch } : entry)),
    );
  };

  const confirmAction = async (entry: DashboardChatEntry) => {
    if (!entry.pendingAction) return;
    setExecutingId(entry.id);
    updateMessage(entry.id, { actionError: null, actionResult: null });
    const actionLabel = entry.pendingAction.target.label;
    emit({ type: "command:execute", payload: { id: entry.id, label: `Opening ${actionLabel}`, status: "start" } });
    try {
      if (entry.pendingAction.youtubeCommand) {
        const youtubeResponse = await requestYouTubeCommand({
          action: "auto",
          command: entry.pendingAction.youtubeCommand,
          user_confirmed: true,
          source: "dashboard_chat_confirmation",
        });
        if (youtubeResponse.executed || youtubeResponse.status === "ok") {
          updateMessage(entry.id, {
            pendingAction: null,
            actionResult: youtubeResponse.message,
          });
          emit({ type: "command:execute", payload: { id: entry.id, label: youtubeResponse.message, status: "success" } });
        } else {
          updateMessage(entry.id, { actionError: youtubeResponse.error || youtubeResponse.message });
          emit({ type: "command:execute", payload: { id: entry.id, label: "YouTube command failed", status: "error" } });
        }
        refreshEvents();
        return;
      }
      const common = {
        targetValue: entry.pendingAction.target.value,
        label: entry.pendingAction.target.label,
        originalText: entry.pendingAction.sourceText,
        normalizedText: entry.pendingAction.sourceText.toLowerCase(),
        confidence: 100,
        userConfirmed: true,
        dryRun: false,
        source: "dashboard_chat",
      };
      const response =
        entry.pendingAction.target.kind === "website"
          ? await requestOpenWebsiteAction(buildWebsiteActionRequest(common))
          : await requestOpenAppAction(buildAppActionRequest(common));
      if (response.executed) {
        updateMessage(entry.id, {
          pendingAction: null,
          actionResult: `Done. ${entry.pendingAction.target.label} opened through the safe backend action API.`,
        });
        emit({ type: "command:execute", payload: { id: entry.id, label: `${actionLabel} opened`, status: "success" } });
      } else {
        updateMessage(entry.id, {
          actionError: response.error || response.message,
        });
        emit({ type: "command:execute", payload: { id: entry.id, label: "Action blocked", status: "error" } });
      }
      refreshEvents();
    } catch (err) {
      updateMessage(entry.id, {
        actionError: err instanceof Error ? err.message : "Action request failed.",
      });
      emit({ type: "command:execute", payload: { id: entry.id, label: "Action failed", status: "error" } });
    } finally {
      setExecutingId(null);
    }
  };

  const speakAnswer = async (entry: DashboardChatEntry) => {
    updateMessage(entry.id, { speaking: true, speakMessage: null });
    try {
      const status = await getBackendTtsStatus();
      if (!status.enabled) {
        updateMessage(entry.id, {
          speaking: false,
          speakMessage: "TTS permission is disabled. Enable TTS in Settings/Security to speak answers.",
        });
        return;
      }
      const response = await requestTtsSpeak(entry.text.slice(0, 380));
      updateMessage(entry.id, {
        speaking: false,
        speakMessage: response.spoken ? "Spoken through online neural TTS." : response.error || response.message,
      });
    } catch (err) {
      updateMessage(entry.id, {
        speaking: false,
        speakMessage: err instanceof Error ? err.message : "TTS request failed.",
      });
    }
  };

  const clearHistory = () => {
    const confirmed = window.confirm("Clear Dashboard chat history?");
    if (!confirmed) return;
    if (engine.enabled) {
      clearedCursor.current = { generation: engine.generation, cursor: engine.cursor };
      try {
        localStorage.setItem(CLEARED_ENGINE_CURSOR_KEY, JSON.stringify(clearedCursor.current));
      } catch { /* Clear still works for this mounted page if storage is unavailable. */ }
    }
    setMessages([]);
    setGlobalError(null);
  };

  const today = new Date().toDateString();
  const todayEvents = events.filter(
    (event) => new Date(event.created_at).toDateString() === today,
  );
  const executedToday = todayEvents.filter((event) => event.status === "executed" || event.status === "completed").length;
  const blockedToday = todayEvents.filter((event) => event.status === "blocked").length;
  const recentCommands = events.slice(0, 5);

  const targetIconAccent = (intent: string) =>
    ALL_TARGETS.find((target) => intent.includes(target.kind))?.accent ?? "#818cf8";

  const fileSearchDetected = detectFileSearchHints(draft).isFileSearch;

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }, []);
  const profileName = useMemo(() => loadProfile().userName?.trim() || "", []);

  return (
    <>
      <div className="nx-page">
        <section className="dash-hero" aria-label="AI Command Center">
          <span className="dash-hero-glow" aria-hidden="true" />
          <div className="dash-hero-core">
            <VoiceOrb size={104} />
          </div>
          <div className="dash-hero-main">
            <p className="dash-hero-eyebrow"><Sparkles size={12} /> AI Command Center</p>
            <h1 className="dash-hero-title">
              {greeting}{profileName ? `, ${profileName}` : ""}
            </h1>
            <p className="dash-hero-sub">
              Nexa is {backendConnected ? "online and ready" : "offline"} · voice{" "}
              {engine.enabled ? engine.connected ? "ready" : "connecting" : sttReady === null ? "checking" : sttReady ? "ready" : "on standby"} · safety enforced
            </p>
            <div className="dash-hero-stats">
              <div className="dash-hero-stat">
                <strong>{executedToday}</strong>
                <span>Executed today</span>
              </div>
              <div className="dash-hero-stat">
                <strong>{todayEvents.length}</strong>
                <span>Events</span>
              </div>
              <div className="dash-hero-stat">
                <strong>{blockedToday}</strong>
                <span>Blocked</span>
              </div>
            </div>
          </div>
          <span className="dash-hero-status">
            <span className={`dash-hero-dot ${backendConnected ? "ok" : "warn"}`} />
            {backendConnected ? "Core online" : "Core offline"}
          </span>
        </section>

        <section className="nx-card dashboard-chat-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Bot /> Nexa Assistant</div>
            <button type="button" className="nx-btn ghost" onClick={clearHistory} disabled={loading || executingId !== null}>
              Clear
            </button>
          </div>

          <EngineControls />
          {engine.enabled && engine.confirmation && (
            <div className="nx-native-confirmation" role="group" aria-label="কাজটি নিশ্চিত করুন">
              <strong>{engine.confirmation.title}</strong>
              <pre>{engine.confirmation.detail}</pre>
              <button type="button" className="nx-btn" disabled={executingId === engine.confirmation.id}
                onClick={() => {
                  const pending = engine.confirmation;
                  if (!pending) return;
                  setExecutingId(pending.id);
                  void engineCommand("confirm", { id: pending.id, accepted: true })
                    .catch(failure => setGlobalError(failure.message)).finally(() => setExecutingId(null));
                }}>নিশ্চিত করুন</button>
              <button type="button" className="nx-btn ghost" onClick={() => {
                const pending = engine.confirmation;
                if (pending) void engineCommand("confirm", { id: pending.id, accepted: false }).catch(failure => setGlobalError(failure.message));
              }}>বাতিল</button>
            </div>
          )}
          <div className="dashboard-chat-thread" aria-live="polite">
            <EngineInlineTools />
            {messages.length === 0 && (
              <div className="nx-empty">
                Ask weather, web questions, or safe action requests here. Answers stay on the Dashboard.
              </div>
            )}
            {messages.map((entry) => (
              <article key={entry.id} className={`dashboard-chat-bubble ${entry.role}`}>
                <div className="dashboard-chat-avatar">{entry.role === "user" ? <Mic /> : <Bot />}</div>
                <div className="dashboard-chat-body">
                  <p>{entry.text}</p>
                  {entry.role === "assistant" && (
                    <>
                      <div className="nx-chip-row dashboard-chat-chips">
                        {(entry.chips ?? []).map((chip) => (
                          <span key={chip} className={`nx-chip ${entry.status === "blocked" ? "warn" : "muted"}`}>
                            {chip}
                          </span>
                        ))}
                        {(entry.sources ?? []).slice(0, 4).map((source) => (
                          <span key={source} className="nx-chip">{source}</span>
                        ))}
                        {entry.provider && <span className="nx-chip">{entry.provider}</span>}
                        {entry.source && entry.source !== entry.provider && <span className="nx-chip muted">{entry.source}</span>}
                      </div>

                      {entry.sourceUrl && <div className="dashboard-chat-source">Source: {entry.sourceUrl}</div>}

                      {entry.pendingTask && (
                        <div className="nx-result-ok dashboard-pending-task">
                          {entry.pendingTask.status_label}
                        </div>
                      )}

                      {entry.searchResults && entry.searchResults.length > 0 && (
                        <>
                          <button
                            type="button"
                            className="nx-link-btn dashboard-source-toggle"
                            onClick={() =>
                              setExpandedSources((prev) => ({
                                ...prev,
                                [entry.id]: !(prev[entry.id] ?? entry.showSearchResultsByDefault ?? false),
                              }))
                            }
                          >
                            {(expandedSources[entry.id] ?? entry.showSearchResultsByDefault) ? "Hide sources" : "View sources"}
                          </button>
                          {(expandedSources[entry.id] ?? entry.showSearchResultsByDefault) && (
                            <div className="dashboard-search-results">
                              {entry.searchResults.slice(0, 3).map((result) => (
                                <div className="dashboard-search-result" key={`${result.provider}-${result.title}`}>
                                  <strong>{result.title}</strong>
                                  <span>{result.snippet || result.provider}</span>
                                  {result.source_url && <small>{result.source_url}</small>}
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}

                      <div className="dashboard-chat-actions">
                        <button
                          type="button"
                          className="nx-btn ghost"
                          onClick={() => void speakAnswer(entry)}
                          disabled={entry.speaking || !entry.text.trim()}
                        >
                          <Volume2 size={14} />
                          {entry.speaking ? "Speaking..." : "Speak"}
                        </button>
                      </div>

                      {entry.speakMessage && <div className="nx-result-ok">{entry.speakMessage}</div>}

                      {entry.pendingAction && (
                        <div className="nx-confirm dashboard-inline-confirm">
                          <h5>Confirm action</h5>
                          {entry.pendingAction.draftText ? (
                            <p>
                              Open <strong>{entry.pendingAction.target.label}</strong> for{" "}
                              <strong>{entry.pendingAction.recipient ?? "selected contact"}</strong> with draft:
                              <br />
                              <span className="dashboard-draft-preview">{entry.pendingAction.draftText}</span>
                              <br />
                              Nexa will not click Send or read private chats.
                            </p>
                          ) : entry.pendingAction.youtubeCommand ? (
                            <p>
                              Run <strong>{entry.pendingAction.target.label}</strong> in Nexa's controlled YouTube window?
                              This action cannot access other browser tabs.
                            </p>
                          ) : (
                            <p>
                              Open <strong>{entry.pendingAction.target.label}</strong> (
                              {entry.pendingAction.target.kind === "website" ? "whitelisted website" : "whitelisted app"})?
                              Chat only previewed this action. Nothing runs until you confirm.
                            </p>
                          )}
                          <div className="nx-confirm-actions">
                            <PremiumButton
                              type="button"
                              onClick={() => void confirmAction(entry)}
                              disabled={executingId !== null}
                            >
                              {executingId === entry.id
                                ? "Opening..."
                                : entry.pendingAction.actionLabel ?? `Confirm & Open ${entry.pendingAction.target.label}`}
                            </PremiumButton>
                            <PremiumButton
                              type="button"
                              variant="ghost"
                              onClick={() => updateMessage(entry.id, { pendingAction: null })}
                              disabled={executingId !== null}
                            >
                              Cancel
                            </PremiumButton>
                          </div>
                        </div>
                      )}

                      {entry.actionResult && <div className="nx-result-ok">{entry.actionResult}</div>}
                      {entry.actionError && <div className="nx-result-err">{entry.actionError}</div>}
                    </>
                  )}
                </div>
              </article>
            ))}
            {(loading || (engine.enabled && (engine.state === "THINKING" || engine.state === "PROCESSING"))) && (
              <article className="dashboard-chat-bubble assistant">
                <div className="dashboard-chat-avatar"><Bot /></div>
                <div className="dashboard-chat-body"><p>{engine.enabled ? "নেক্সা ভাবছে…" : "Thinking through the safe backend..."}</p></div>
              </article>
            )}
            <div ref={endRef} />
          </div>

          {globalError && <div className="nx-result-err">{globalError}</div>}

          <div className="nx-cmd-bar dashboard-chat-input">
            <button type="button" className="dashboard-voice-launch" onClick={() => onNavigate("voice")} title="Open continuous voice conversation" aria-label="Open voice conversation">
              <Mic />
            </button>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder='Ask Nexa: "today weather in Dhaka", "open youtube", or "delete system32"'
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendToAssistant();
                }
              }}
            />
            <button
              type="button"
              className="nx-cmd-send"
              onClick={() => void sendToAssistant()}
              disabled={!draft.trim() || loading}
              title="Send to Nexa"
            >
              <Send size={17} />
            </button>
          </div>

          <div className="nx-chip-row dashboard-chat-suggestions">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="nx-suggestion"
                onClick={() => void sendToAssistant(suggestion)}
                disabled={loading}
              >
                {suggestion}
              </button>
            ))}
          </div>

          {fileSearchDetected && (
            <div className="nx-locked-note">
              File search works in the File Organizer. Dashboard chat keeps file write operations disabled.
              <button type="button" className="nx-link-btn" onClick={() => onNavigate("files")}>
                Open Files
              </button>
            </div>
          )}
        </section>

        <YouTubeControlPanel />

        <ImageGenerationPanel />

        <SystemControlsPanel />

        <div className="nx-grid-2">
          <ContentWriterPanel />
          <PerformancePanel />
        </div>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Zap /> Quick Actions</div>
          </div>
          <div className="nx-grid-4">
            {[
              ALL_TARGETS.find((target) => target.value === "youtube")!,
              ALL_TARGETS.find((target) => target.value === "chrome")!,
              ALL_TARGETS.find((target) => target.value === "google")!,
              ALL_TARGETS.find((target) => target.value === "calculator")!,
            ].map((target) => (
              <button
                key={target.value}
                type="button"
                className="nx-tile"
                onClick={() => void sendToAssistant(`Open ${target.label}`)}
              >
                <span
                  className="nx-tile-icon"
                  style={{ background: `${target.accent}22`, color: target.accent }}
                >
                  <Rocket />
                </span>
                <strong>Open {target.label}</strong>
                <small>Shows confirmation in chat</small>
              </button>
            ))}
          </div>
        </section>

        <div className="nx-grid-2">
          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Brain /> Input Understanding</div>
            </div>
            <div className="nx-row"><span>Draft</span><strong>{draft || "-"}</strong></div>
            <div className="nx-row"><span>Local intent hint</span><strong>{understanding.intent}</strong></div>
            <div className="nx-row"><span>Language</span><strong>{understanding.language}</strong></div>
            <div className="nx-row"><span>Confidence</span><strong>{understanding.confidence}%</strong></div>
            <div className="nx-row">
              <span>Risk</span>
              <strong className={understanding.riskLevel === "blocked" ? "nx-status-err" : understanding.riskLevel === "safe" ? "nx-status-ok" : "nx-status-warn"}>
                {understanding.riskLevel}
              </strong>
            </div>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Cpu /> System Status</div>
            </div>
            <div className="nx-row">
              <span><Wifi size={13} style={{ marginRight: 7 }} />Backend</span>
              <strong className={backendConnected ? "nx-status-ok" : "nx-status-err"}>
                {backendConnected ? "Connected" : "Offline"}
              </strong>
            </div>
            <div className="nx-row">
              <span><Mic size={13} style={{ marginRight: 7 }} />Voice Engine</span>
              <strong className={sttReady ? "nx-status-ok" : "nx-status-warn"}>
                {engine.enabled ? engine.connected ? "Ready" : "Connecting" : sttReady === null ? "Checking..." : sttReady ? "Ready" : "Not ready"}
              </strong>
            </div>
            <div className="nx-row">
              <span><Globe size={13} style={{ marginRight: 7 }} />Web/Weather</span>
              <strong className={backendConnected ? "nx-status-ok" : "nx-status-warn"}>
                {backendConnected ? "Available in chat" : "Needs backend"}
              </strong>
            </div>
            <div className="nx-row">
              <span><AlertTriangle size={13} style={{ marginRight: 7 }} />Safety Gates</span>
              <strong className="nx-status-ok">Enforced</strong>
            </div>
          </section>
        </div>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Activity /> Recent Backend Events</div>
            <button type="button" className="nx-link-btn" onClick={() => onNavigate("history")}>
              View all
            </button>
          </div>
          {recentCommands.length === 0 ? (
            <div className="nx-empty">No backend events recorded yet. Try a chat question or quick action.</div>
          ) : (
            <div className="nx-list">
              {recentCommands.map((event) => (
                <div className="nx-list-row" key={event.id}>
                  <span
                    className="nx-tile-icon"
                    style={{ background: "rgba(99,102,241,0.12)", color: targetIconAccent(event.intent) }}
                  >
                    <LayoutGrid />
                  </span>
                  <div className="nx-list-main">
                    <strong>{event.intent}{event.target ? ` -> ${event.target}` : ""}</strong>
                    <small>{new Date(event.created_at).toLocaleTimeString()}</small>
                  </div>
                  <span
                    className={`nx-list-badge ${
                      event.status === "executed" || event.status === "completed"
                        ? "ok"
                        : event.status === "blocked" || event.status === "failed"
                        ? "bad"
                        : "mid"
                    }`}
                  >
                    {event.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <aside className="nx-rail">
        {engine.enabled ? <section className="nx-card">
          <div className="nx-card-head"><div className="nx-card-title">নেক্সা Live Voice</div></div>
          <p>কথা, উত্তর, context এবং tool-এর ফলাফল পাশের chat-এ আসবে।</p>
          <EngineControls />
        </section> : (
        <PushToTalkPanel
          onTranscript={(text) => {
            setDraft(text);
            return sendToAssistant(text, { autoSpeak: true, source: "dashboard_voice" });
          }}
        />
        )}

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Activity /> Today's Activity</div>
          </div>
          <div className="nx-grid-3">
            <div className="nx-stat"><strong>{executedToday}</strong><span>Executed</span></div>
            <div className="nx-stat purple"><strong>{todayEvents.length}</strong><span>Total events</span></div>
            <div className="nx-stat green"><strong>{blockedToday}</strong><span>Blocked</span></div>
          </div>
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Lightbulb /> Chat Examples</div>
          </div>
          <div className="nx-list">
            {SUGGESTIONS.slice(0, 4).map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="nx-suggestion"
                onClick={() => void sendToAssistant(suggestion)}
                disabled={loading}
              >
                {suggestion} <span>Send</span>
              </button>
            ))}
          </div>
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Sparkles /> Dashboard Mode</div>
          </div>
          <div className="nx-row"><span>Answers</span><strong>In chat</strong></div>
          <div className="nx-row"><span>Weather</span><strong>Open-Meteo</strong></div>
          <div className="nx-row"><span>Web</span><strong>Safe providers</strong></div>
          <div className="nx-row"><span>Actions</span><strong>Confirm first</strong></div>
        </section>
      </aside>
    </>
  );
}

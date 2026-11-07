import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, CloudSun, Eraser, Search, Send, ShieldCheck, User } from "lucide-react";
import { chat } from "@/lib/llm";
import type { ChatResult, ChatTurn } from "@/lib/llm";
import { loadProfile } from "@/lib";
import { PageHero } from "@/components/ui";
import { useInteraction, VoiceOrb, ThinkingIndicator, PremiumButton } from "@/interaction";

type ChatRole = "user" | "assistant";

type ChatEntry = {
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
};

const STORAGE_KEY = "nexa.aiChat.history";

const suggestions = [
  "ajker weather ki",
  "আজকের weather কি",
  "today weather in Dhaka",
  "google theke search kore bolo python latest version",
];

function createEntry(role: ChatRole, text: string, extra: Partial<ChatEntry> = {}): ChatEntry {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function resultToEntry(result: ChatResult): ChatEntry {
  // Backend answers carry rich chips/source; direct providers surface their name.
  const chips = [...(result.extras?.chips ?? [])];
  if (result.providerId !== "nexa-backend" && !chips.includes(result.providerLabel)) {
    chips.push(result.providerLabel);
  }
  return createEntry("assistant", result.text, {
    intent: result.extras?.intent,
    status: result.extras?.status,
    provider: result.extras?.backendProvider ?? result.providerLabel,
    source: result.extras?.source ?? null,
    sourceUrl: result.extras?.sourceUrl ?? null,
    chips,
  });
}

/** A stable per-session conversation id so history/continuity survive provider
 *  switching (the router never resets it). */
function newConversationId(): string {
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ChatPage() {
  const { emit, notify } = useInteraction();
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);
  const conversationId = useRef<string>(newConversationId());

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setMessages(JSON.parse(raw) as ChatEntry[]);
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-40)));
    } catch {
      // Local history is helpful, not required.
    }
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const chatHistory: ChatTurn[] = useMemo(
    () => messages.slice(-8).map((item) => ({ role: item.role, content: item.text })),
    [messages],
  );

  const sendMessage = async (value?: string) => {
    const text = (value ?? draft).trim();
    if (!text || loading) return;
    setDraft("");
    setErrorMessage(null);
    setConfirmClear(false);
    const userEntry = createEntry("user", text);
    setMessages((prev) => [...prev, userEntry]);
    setLoading(true);
    emit({ type: "ai:thinking", payload: { active: true, label: "Nexa is thinking" } });
    try {
      // Unified entry: the LLM router picks the provider and fails over
      // automatically. History + conversation id are preserved across switches.
      const result = await chat(text, {
        history: chatHistory,
        conversationId: conversationId.current,
        addressStyle: loadProfile().addressingPreference,
        preferredLanguage: loadProfile().languageMode,
        onNotice: (notice) => notify(notice),
      });
      setMessages((prev) => [...prev, resultToEntry(result)]);
    } catch (err) {
      const message =
        err instanceof Error
          ? `${err.message}. Start the backend at http://127.0.0.1:8766 and try again.`
          : "Chat request failed.";
      setErrorMessage(message);
      setMessages((prev) => [
        ...prev,
        createEntry("assistant", message, {
          status: "failed",
          chips: ["Backend required", "Error"],
        }),
      ]);
      notify({ title: "Chat request failed", message: "Start the backend and try again.", tone: "error" });
    } finally {
      emit({ type: "ai:thinking", payload: { active: false } });
      setLoading(false);
    }
  };

  const clearHistory = () => {
    if (!confirmClear) {
      setConfirmClear(true);
      return;
    }
    setMessages([]);
    setConfirmClear(false);
    setErrorMessage(null);
  };

  return (
    <div className="nx-page chat-page nxos-chat-page">
      <PageHero
        icon={<Bot />}
        eyebrow="Conversation"
        title={<>AI Chat <span>Live Answers</span></>}
        description="Ask weather or safe web questions in Bangla, Banglish, or English. Answers stay inside Nexa — no action execution."
        meta={
          <>
            <span className="nx-chip"><CloudSun size={13} /> Open-Meteo</span>
            <span className="nx-chip"><Search size={13} /> DuckDuckGo + Wikipedia</span>
            <span className="nx-chip muted"><ShieldCheck size={13} /> Read-only</span>
          </>
        }
        actions={
          <PremiumButton type="button" variant="ghost" onClick={clearHistory} disabled={loading}>
            <Eraser size={14} />
            {confirmClear ? "Confirm clear" : "Clear"}
          </PremiumButton>
        }
      />

      <section className="nx-card chat-shell nxos-chat">
        <div className="chat-thread nxos-chat-thread" aria-live="polite">
          {messages.length === 0 && (
            <div className="nxos-chat-empty">
              <VoiceOrb size={76} />
              <h3>Ask Nexa anything</h3>
              <p>Weather, safe web answers, and translations — Bangla, Banglish, or English.</p>
            </div>
          )}
          {messages.map((item) => (
            <article key={item.id} className={`chat-bubble ${item.role}`}>
              <div className="chat-avatar">{item.role === "user" ? <User /> : <Bot />}</div>
              <div className="chat-bubble-body">
                <p>{item.text}</p>
                {item.role === "assistant" && (
                  <div className="nx-chip-row chat-chip-row">
                    {(item.chips ?? []).map((chip) => (
                      <span key={chip} className={`nx-chip ${item.status === "blocked" ? "warn" : "muted"}`}>
                        {chip}
                      </span>
                    ))}
                    {item.provider && <span className="nx-chip">{item.provider}</span>}
                    {item.source && item.source !== item.provider && <span className="nx-chip muted">{item.source}</span>}
                  </div>
                )}
                {item.sourceUrl && (
                  <div className="chat-source">Source: {item.sourceUrl}</div>
                )}
              </div>
            </article>
          ))}
          {loading && (
            <article className="chat-bubble assistant">
              <div className="chat-avatar"><Bot /></div>
              <div className="chat-bubble-body"><ThinkingIndicator label="Thinking through safe providers" /></div>
            </article>
          )}
          <div ref={endRef} />
        </div>

        {errorMessage && <div className="nx-result-err">{errorMessage}</div>}

        <div className="nxos-composer">
          <div className="nx-chip-row chat-suggestions">
            {suggestions.map((example) => (
              <button
                type="button"
                className="nx-suggestion"
                key={example}
                onClick={() => void sendMessage(example)}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>

          <div className="nx-cmd-bar chat-input">
            <Bot />
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask Nexa… weather, web answer, or a safe question"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
            />
            <button
              type="button"
              className="nx-cmd-send"
              title="Send message"
              onClick={() => void sendMessage()}
              disabled={loading || !draft.trim()}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

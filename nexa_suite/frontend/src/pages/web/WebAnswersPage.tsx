import { useEffect, useState } from "react";
import {
  Clock,
  Globe,
  Mic,
  Search,
  Sparkles,
  Volume2,
  Wifi,
} from "lucide-react";
import {
  requestWebAnswer,
  WebAnswerResponseDto,
  requestTtsSpeak,
  getBackendTtsStatus,
} from "@/lib/backendAssistantClient";
import {
  buildWebsiteActionRequest,
  requestOpenWebsiteAction,
} from "@/lib";
import { WEBSITE_TARGETS, SafeTarget } from "@/lib/safeTargets";
import { PageHero } from "@/components/ui";

const exampleQuestions = ["Bitcoin", "Bangladesh", "Artificial intelligence", "ঢাকা"];

type RecentSearch = { question: string; at: string; answered: boolean };

export function WebAnswersPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<WebAnswerResponseDto | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState(false);
  const [speakMessage, setSpeakMessage] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);

  const [shortcutConfirm, setShortcutConfirm] = useState<SafeTarget | null>(null);
  const [shortcutBusy, setShortcutBusy] = useState(false);
  const [shortcutMessage, setShortcutMessage] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("nexa.recentSearches");
      if (raw) setRecentSearches(JSON.parse(raw) as RecentSearch[]);
    } catch {
      // ignore corrupted local data
    }
  }, []);

  const saveRecent = (entry: RecentSearch) => {
    setRecentSearches((prev) => {
      const next = [entry, ...prev.filter((r) => r.question !== entry.question)].slice(0, 8);
      try {
        localStorage.setItem("nexa.recentSearches", JSON.stringify(next));
      } catch {
        // storage full — non-fatal
      }
      return next;
    });
  };

  const handleAsk = async (value?: string) => {
    const q = (value ?? question).trim();
    if (!q) return;
    setLoading(true);
    setErrorMessage(null);
    setResponse(null);
    setSpeakMessage(null);
    try {
      const result = await requestWebAnswer(q);
      setResponse(result);
      saveRecent({ question: q, at: new Date().toISOString(), answered: result.answered });
      if (!result.answered) setErrorMessage(result.error || result.message);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "Web answer request failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSpeak = async () => {
    if (!response?.answer) return;
    setSpeaking(true);
    setSpeakMessage(null);
    try {
      const status = await getBackendTtsStatus();
      if (!status.enabled) {
        setSpeakMessage("Voice reply is disabled. Enable it in Settings or the Security Center.");
        return;
      }
      const result = await requestTtsSpeak(response.answer.slice(0, 380));
      setSpeakMessage(result.spoken ? "Spoken through online neural TTS." : (result.error || result.message));
    } catch (err) {
      setSpeakMessage(err instanceof Error ? err.message : "TTS request failed.");
    } finally {
      setSpeaking(false);
    }
  };

  const handleShortcutOpen = async () => {
    if (!shortcutConfirm) return;
    setShortcutBusy(true);
    setShortcutMessage(null);
    try {
      const request = buildWebsiteActionRequest({
        targetValue: shortcutConfirm.value,
        label: shortcutConfirm.label,
        originalText: `Open ${shortcutConfirm.label}`,
        normalizedText: `open ${shortcutConfirm.label.toLowerCase()}`,
        confidence: 100,
        userConfirmed: true,
        dryRun: false,
        source: "web_page_shortcut",
      });
      const result = await requestOpenWebsiteAction(request);
      setShortcutMessage(
        result.executed ? `${shortcutConfirm.label} opened safely.` : (result.error || result.message),
      );
      setShortcutConfirm(null);
    } catch (err) {
      setShortcutMessage(err instanceof Error ? err.message : "Open request failed.");
    } finally {
      setShortcutBusy(false);
    }
  };

  return (
    <>
      <div className="nx-page">
        <PageHero
          icon={<Globe />}
          eyebrow="Web Intelligence"
          title={<>Web Search & <span>Safe Answers</span></>}
          description="Instant answers from safe public sources. No scraping, no unknown websites."
          meta={
            <>
              <span className="nx-chip"><Wifi size={13} /> DuckDuckGo + Wikipedia only</span>
              <span className="nx-chip"><Mic size={13} /> Works with voice transcripts</span>
              <span className="nx-chip muted">Answers never execute actions</span>
            </>
          }
        />

        <section className="nx-card">
          <div className="nx-cmd-bar" style={{ maxWidth: "100%" }}>
            <Search />
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder='Ask anything... e.g. "Bitcoin" or "ঢাকা"'
              onKeyDown={(event) => {
                if (event.key === "Enter") void handleAsk();
              }}
            />
            <button
              type="button"
              className="nx-cmd-send"
              onClick={() => void handleAsk()}
              disabled={loading || !question.trim()}
              title="Search safely"
            >
              <Search size={16} />
            </button>
          </div>
          <div className="nx-chip-row" style={{ marginTop: 14 }}>
            {exampleQuestions.map((example) => (
              <button
                key={example}
                type="button"
                className="nx-suggestion"
                style={{ width: "auto" }}
                onClick={() => {
                  setQuestion(example);
                  void handleAsk(example);
                }}
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>
        </section>

        {loading && (
          <section className="nx-card">
            <div className="nx-empty">Contacting safe answer sources...</div>
          </section>
        )}

        {errorMessage && !loading && <div className="nx-result-err">{errorMessage}</div>}

        {response && response.answered && (
          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Sparkles /> Answer</div>
              <button type="button" className="nx-btn ghost" onClick={handleSpeak} disabled={speaking}>
                <Volume2 size={14} style={{ marginRight: 6, verticalAlign: "-2px" }} />
                {speaking ? "Speaking..." : "Speak"}
              </button>
            </div>
            <p style={{ color: "#e6f1ff", lineHeight: 1.7, margin: "0 0 12px" }}>{response.answer}</p>
            <div className="nx-row"><span>Source</span><strong>{response.source}</strong></div>
            {response.source_url && (
              <div className="nx-row"><span>Reference</span><strong style={{ fontSize: 12 }}>{response.source_url}</strong></div>
            )}
            {speakMessage && <div className="nx-result-ok">{speakMessage}</div>}
            <div className="nx-hero-hint" style={{ textAlign: "left" }}>
              Informational only — no website was opened and nothing was executed.
            </div>
          </section>
        )}

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Globe /> Website Shortcuts</div>
          </div>
          <div className="nx-grid-4">
            {WEBSITE_TARGETS.map((target) => (
              <button
                key={target.value}
                type="button"
                className="nx-tile"
                onClick={() => {
                  setShortcutConfirm(target);
                  setShortcutMessage(null);
                }}
              >
                <span className="nx-tile-icon" style={{ background: `${target.accent}22`, color: target.accent }}>
                  <Globe />
                </span>
                <strong>{target.label}</strong>
                <small>Confirm to open</small>
              </button>
            ))}
          </div>

          {shortcutConfirm && (
            <div className="nx-confirm">
              <h5>Confirm website open</h5>
              <p>Open <strong>{shortcutConfirm.label}</strong> in your browser?</p>
              <div className="nx-confirm-actions">
                <button type="button" className="nx-btn" onClick={handleShortcutOpen} disabled={shortcutBusy}>
                  {shortcutBusy ? "Opening..." : "Confirm & Open"}
                </button>
                <button type="button" className="nx-btn ghost" onClick={() => setShortcutConfirm(null)} disabled={shortcutBusy}>
                  Cancel
                </button>
              </div>
            </div>
          )}
          {shortcutMessage && <div className="nx-result-ok">{shortcutMessage}</div>}
        </section>
      </div>

      <aside className="nx-rail">
        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Clock /> Recent Searches</div>
          </div>
          {recentSearches.length === 0 ? (
            <div className="nx-empty">No searches yet.</div>
          ) : (
            <div className="nx-list">
              {recentSearches.map((entry) => (
                <button
                  key={entry.question + entry.at}
                  type="button"
                  className="nx-suggestion"
                  onClick={() => {
                    setQuestion(entry.question);
                    void handleAsk(entry.question);
                  }}
                >
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {entry.question}
                  </span>
                  <span className={`nx-list-badge ${entry.answered ? "ok" : "mid"}`}>
                    {entry.answered ? "answered" : "no answer"}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Sparkles /> How it stays safe</div>
          </div>
          <div className="nx-row"><span>Allowed hosts</span><strong>DuckDuckGo, Wikipedia</strong></div>
          <div className="nx-row"><span>Scraping</span><strong className="nx-status-ok">Never</strong></div>
          <div className="nx-row"><span>Auto-open links</span><strong className="nx-status-ok">Never</strong></div>
          <div className="nx-row"><span>Browser opens</span><strong>Confirmation only</strong></div>
        </section>
      </aside>
    </>
  );
}

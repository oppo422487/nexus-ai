import { useEffect, useState } from "react";
import {
  AppWindow,
  Clock,
  Globe,
  Lock,
  Rocket,
  Settings2,
} from "lucide-react";
import {
  buildWebsiteActionRequest,
  buildAppActionRequest,
  requestOpenWebsiteAction,
  requestOpenAppAction,
} from "@/lib";
import {
  AuditEventDto,
  getBackendAuditEvents,
} from "@/lib/backendAssistantClient";
import { APP_TARGETS, WEBSITE_TARGETS, SafeTarget } from "@/lib/safeTargets";
import { PageHero } from "@/components/ui";

export function LauncherHubPage() {
  const [selected, setSelected] = useState<SafeTarget | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recentLaunches, setRecentLaunches] = useState<AuditEventDto[]>([]);

  const refreshRecent = () => {
    getBackendAuditEvents(60)
      .then((response) =>
        setRecentLaunches(
          response.events
            .filter((e) => e.intent === "open_app" || e.intent === "open_website")
            .slice(0, 6),
        ),
      )
      .catch(() => setRecentLaunches([]));
  };

  useEffect(() => {
    refreshRecent();
  }, []);

  const handleSelect = (target: SafeTarget) => {
    setSelected(target);
    setConfirming(false);
    setResultMessage(null);
    setErrorMessage(null);
  };

  const handleLaunch = async () => {
    if (!selected) return;
    setExecuting(true);
    setErrorMessage(null);
    setResultMessage(null);
    try {
      const common = {
        targetValue: selected.value,
        label: selected.label,
        originalText: `Open ${selected.label}`,
        normalizedText: `open ${selected.label.toLowerCase()}`,
        confidence: 100,
        userConfirmed: true,
        dryRun: false,
        source: "launcher_page",
      };
      const response =
        selected.kind === "website"
          ? await requestOpenWebsiteAction(buildWebsiteActionRequest(common))
          : await requestOpenAppAction(buildAppActionRequest(common));
      if (response.executed) {
        setResultMessage(`${selected.label} opened safely.`);
      } else {
        setErrorMessage(response.error || response.message);
      }
      setConfirming(false);
      refreshRecent();
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Is the backend running?`
          : "Launch request failed.",
      );
    } finally {
      setExecuting(false);
    }
  };

  const renderTargetGrid = (targets: SafeTarget[]) => (
    <div className="nx-grid-3">
      {targets.map((target) => (
        <button
          key={target.value}
          type="button"
          className={`nx-launch-card${selected?.value === target.value ? " selected" : ""}`}
          onClick={() => handleSelect(target)}
        >
          <span
            className="nx-tile-icon"
            style={{ background: `${target.accent}22`, color: target.accent }}
          >
            {target.kind === "website" ? <Globe /> : <AppWindow />}
          </span>
          <span>
            <strong>{target.label}</strong>
            <small>{target.description} · {target.kind === "website" ? "Web" : "Desktop"}</small>
          </span>
        </button>
      ))}
    </div>
  );

  return (
    <>
      <div className="nx-page">
        <PageHero
          icon={<Rocket />}
          eyebrow="Launcher"
          title={<>App & <span>Website Launcher</span></>}
          description="Open whitelisted apps and websites with confirmation, by click or voice."
          meta={
            <>
              <span className="nx-chip">Whitelist enforced server-side</span>
              <span className="nx-chip">Confirmation required</span>
              <span className="nx-chip muted">{APP_TARGETS.length} apps · {WEBSITE_TARGETS.length} websites</span>
            </>
          }
        />

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><AppWindow /> Desktop Apps</div>
          </div>
          {renderTargetGrid(APP_TARGETS)}
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Globe /> Websites</div>
          </div>
          {renderTargetGrid(WEBSITE_TARGETS)}
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Settings2 /> Launcher Configuration</div>
          </div>
          <div className="nx-locked-note">
            <Lock />
            <span>
              Custom launchers, arbitrary URLs, and executable paths are{" "}
              <strong>locked off by safety policy</strong>. Only the whitelisted
              targets above can ever be opened, and the backend re-validates every
              launch — adding unknown apps or websites is not possible from the UI.
            </span>
          </div>
        </section>
      </div>

      <aside className="nx-rail">
        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Rocket /> Launch Preview</div>
          </div>
          {!selected ? (
            <div className="nx-empty">Select an app or website to preview the launch.</div>
          ) : (
            <>
              <div className="nx-row"><span>Target</span><strong>{selected.label}</strong></div>
              <div className="nx-row"><span>Type</span><strong>{selected.kind === "website" ? "Website" : "Desktop App"}</strong></div>
              <div className="nx-row"><span>Whitelisted</span><strong className="nx-status-ok">Yes</strong></div>
              <div className="nx-row"><span>Status</span><strong className="nx-status-ok">Ready</strong></div>

              {!confirming ? (
                <button
                  type="button"
                  className="nx-btn"
                  style={{ width: "100%", marginTop: 14 }}
                  onClick={() => setConfirming(true)}
                  disabled={executing}
                >
                  Launch {selected.label}
                </button>
              ) : (
                <div className="nx-confirm" style={{ marginTop: 14 }}>
                  <h5>Confirm launch</h5>
                  <p>Open {selected.label} now?</p>
                  <div className="nx-confirm-actions">
                    <button type="button" className="nx-btn" onClick={handleLaunch} disabled={executing}>
                      {executing ? "Opening..." : "Confirm & Open"}
                    </button>
                    <button type="button" className="nx-btn ghost" onClick={() => setConfirming(false)} disabled={executing}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              {resultMessage && <div className="nx-result-ok">{resultMessage}</div>}
              {errorMessage && <div className="nx-result-err">{errorMessage}</div>}
            </>
          )}
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Clock /> Recent Launches</div>
          </div>
          {recentLaunches.length === 0 ? (
            <div className="nx-empty">No launches recorded yet.</div>
          ) : (
            <div className="nx-list">
              {recentLaunches.map((event) => (
                <div className="nx-list-row" key={event.id}>
                  <span className="nx-tile-icon" style={{ background: "rgba(99,102,241,0.12)", color: "#818cf8" }}>
                    {event.intent === "open_website" ? <Globe /> : <AppWindow />}
                  </span>
                  <div className="nx-list-main">
                    <strong>{event.target || event.intent}</strong>
                    <small>{new Date(event.created_at).toLocaleString()}</small>
                  </div>
                  <span
                    className={`nx-list-badge ${
                      event.status === "executed" ? "ok" : event.status === "blocked" || event.status === "failed" ? "bad" : "mid"
                    }`}
                  >
                    {event.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </aside>
    </>
  );
}

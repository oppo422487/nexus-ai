import { useEffect, useState } from "react";
import {
  AuditEventDto,
  getBackendAuditEvents,
} from "@/lib/backendAssistantClient";

/** Live audit trail of real backend events (executed/blocked actions). */
export function AuditEventsPanel() {
  const [events, setEvents] = useState<AuditEventDto[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await getBackendAuditEvents(50);
      setEvents(response.events);
      setTotalEvents(response.total_events);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "Audit events could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div className="audit-health-panel">
      <div className="audit-health-header">
        <p className="eyebrow">Real Backend Audit Trail ({totalEvents} total)</p>
        <button
          type="button"
          className="audit-health-button"
          onClick={() => void refresh()}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh Events"}
        </button>
      </div>

      {errorMessage && <div className="audit-health-error">{errorMessage}</div>}

      {events.length === 0 && !loading && !errorMessage ? (
        <div className="audit-health-empty">
          No audit events recorded yet. Execute or block an action to see it here.
        </div>
      ) : (
        <div className="audit-event-list">
          {events.map((event) => (
            <div className="audit-event-row" key={event.id}>
              <span className={`audit-event-badge ${event.status}`}>
                {event.status}
              </span>
              <div className="audit-event-main">
                <strong>
                  {event.source} · {event.intent}
                  {event.target ? ` → ${event.target}` : ""}
                </strong>
                <p>{event.message}</p>
              </div>
              <span className="audit-event-time">{formatTime(event.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

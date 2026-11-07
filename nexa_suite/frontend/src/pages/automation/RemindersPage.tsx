import { useEffect, useState } from "react";
import { AlarmClock } from "lucide-react";
import {
  createBackendReminder,
  createNaturalLanguageReminder,
  deleteBackendReminder,
  getBackendReminders,
  ReminderItemDto,
  setBackendReminderStatus,
  snoozeBackendReminder,
  updateBackendReminder,
} from "@/lib/backendAssistantClient";
import { PageHero } from "@/components/ui";

export function RemindersPage({ embedded = false }: { embedded?: boolean } = {}) {
  const [reminders, setReminders] = useState<ReminderItemDto[]>([]);
  const [dueNow, setDueNow] = useState<ReminderItemDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [recurrence, setRecurrence] = useState("");
  const [naturalText, setNaturalText] = useState("");
  const [confirmingCreate, setConfirmingCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editNote, setEditNote] = useState("");
  const [editDueAt, setEditDueAt] = useState("");
  const [editRecurrence, setEditRecurrence] = useState("");

  const refresh = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await getBackendReminders();
      if (response.status === "blocked") {
        setErrorMessage(response.message);
        setReminders([]);
        setDueNow([]);
      } else {
        setReminders(response.reminders);
        setDueNow(response.due_now);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "Reminders could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60000);
    return () => window.clearInterval(timer);
  }, []);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setSaving(true);
    setErrorMessage(null);
    setInfoMessage(null);
    try {
      const dueIso = dueAt ? new Date(dueAt).toISOString() : null;
      const response = await createBackendReminder({
        title: title.trim(),
        note: note.trim(),
        due_at: dueIso,
        recurrence,
      });
      if (response.ok) {
        setInfoMessage("Reminder saved locally.");
        setTitle("");
        setNote("");
        setDueAt("");
        setRecurrence("");
        setConfirmingCreate(false);
        await refresh();
      } else {
        setErrorMessage(response.error || response.message);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Reminder could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const handleNaturalCreate = async () => {
    if (!naturalText.trim()) return;
    setSaving(true);
    setErrorMessage(null);
    try {
      const response = await createNaturalLanguageReminder(naturalText.trim());
      if (!response.ok) {
        setErrorMessage(response.error || response.message);
        return;
      }
      setNaturalText("");
      setInfoMessage(response.message);
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Smart reminder could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const handleSnooze = async (id: string, minutes = 10) => {
    try {
      const response = await snoozeBackendReminder(id, minutes);
      setInfoMessage(response.message);
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Reminder snooze failed.");
    }
  };

  const handleStatus = async (id: string, status: "done" | "dismissed") => {
    try {
      await setBackendReminderStatus(id, status);
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Reminder update failed.");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteBackendReminder(id);
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Reminder delete failed.");
    }
  };

  const beginEdit = (reminder: ReminderItemDto) => {
    setEditingId(reminder.id);
    setEditTitle(reminder.title);
    setEditNote(reminder.note || "");
    setEditDueAt(reminder.due_at ? new Date(reminder.due_at).toISOString().slice(0, 16) : "");
    setEditRecurrence(reminder.recurrence || "");
  };

  const handleEdit = async (id: string) => {
    if (!editTitle.trim()) return;
    setSaving(true);
    setErrorMessage(null);
    try {
      const response = await updateBackendReminder(id, {
        title: editTitle.trim(),
        note: editNote.trim(),
        due_at: editDueAt ? new Date(editDueAt).toISOString() : "",
        recurrence: editRecurrence,
      });
      if (!response.ok) throw new Error(response.error || response.message);
      setEditingId(null);
      setInfoMessage("Reminder updated locally.");
      await refresh();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Reminder edit failed.");
    } finally {
      setSaving(false);
    }
  };

  const formatTime = (iso?: string | null) => {
    if (!iso) return "No due time";
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <section className={embedded ? "reminders-embedded" : "page-surface system-page"}>
      {!embedded && (
        <PageHero
          icon={<AlarmClock />}
          eyebrow="Reminders & Scheduler"
          title="Reminder Center"
          description="Local reminders stored on this machine only. Creating a reminder requires your confirmation, and nothing is sent anywhere."
        />
      )}

      {dueNow.length > 0 && (
        <div className="reminder-due-banner">
          <p className="eyebrow">Due now</p>
          {dueNow.map((reminder) => (
            <div className="reminder-due-row" key={reminder.id}>
              <strong>{reminder.title}</strong>
              <button
                type="button"
                className="transcript-action-button"
                onClick={() => void handleStatus(reminder.id, "done")}
              >
                Mark Done
              </button>
              <button
                type="button"
                className="transcript-action-button secondary"
                onClick={() => void handleSnooze(reminder.id, 10)}
              >
                Snooze 10m
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="command-input-card">
        <p className="eyebrow">Smart reminder</p>
        <div className="reminder-form-grid">
          <input
            className="command-history-search-input"
            type="text"
            placeholder='Try “remind me in 20 minutes to call Rahim”'
            value={naturalText}
            onChange={(event) => setNaturalText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void handleNaturalCreate();
            }}
          />
          <button
            type="button"
            className="backend-preview-button"
            onClick={() => void handleNaturalCreate()}
            disabled={!naturalText.trim() || saving}
          >
            Create Smart Reminder
          </button>
        </div>

        <p className="eyebrow">New reminder</p>
        <div className="reminder-form-grid">
          <input
            className="command-history-search-input"
            type="text"
            placeholder="Reminder title (e.g. 'Submit assignment')"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <input
            className="command-history-search-input"
            type="datetime-local"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
          />
          <select
            className="command-history-search-input"
            value={recurrence}
            onChange={(event) => setRecurrence(event.target.value)}
            aria-label="Reminder recurrence"
          >
            <option value="">One time</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <textarea
          className="command-lab-textarea"
          rows={2}
          placeholder="Optional note..."
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
        {!confirmingCreate ? (
          <div className="transcript-action-row">
            <button
              type="button"
              className="backend-preview-button"
              onClick={() => setConfirmingCreate(true)}
              disabled={!title.trim() || saving}
            >
              Create Reminder
            </button>
            {infoMessage && <span className="history-save-message">{infoMessage}</span>}
          </div>
        ) : (
          <div className="reminder-confirm-row">
            <span>
              Save reminder <strong>{title.trim()}</strong>
              {dueAt ? ` for ${formatTime(new Date(dueAt).toISOString())}` : ""}?
            </span>
            <div className="transcript-action-row">
              <button
                type="button"
                className="transcript-action-button"
                onClick={() => void handleCreate()}
                disabled={saving}
              >
                {saving ? "Saving..." : "Confirm & Save"}
              </button>
              <button
                type="button"
                className="transcript-action-button secondary"
                onClick={() => setConfirmingCreate(false)}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {errorMessage && <div className="backend-preview-error">{errorMessage}</div>}

      <div className="command-history-panel">
        <div className="command-history-header">
          <p className="eyebrow">Your reminders</p>
          <button
            type="button"
            className="command-history-button"
            onClick={() => void refresh()}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {reminders.length === 0 && !loading ? (
          <div className="command-history-empty">No reminders yet. Create one above.</div>
        ) : (
          <div className="command-history-list">
            {reminders.map((reminder) => (
              <div className="reminder-item" key={reminder.id}>
                {editingId === reminder.id ? (
                  <div className="reminder-item-main reminder-edit-fields">
                    <input className="command-history-search-input" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} aria-label="Edit reminder title" />
                    <input className="command-history-search-input" type="datetime-local" value={editDueAt} onChange={(event) => setEditDueAt(event.target.value)} aria-label="Edit reminder due time" />
                    <select className="command-history-search-input" value={editRecurrence} onChange={(event) => setEditRecurrence(event.target.value)} aria-label="Edit recurrence">
                      <option value="">One time</option><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="yearly">Yearly</option>
                    </select>
                    <textarea className="command-lab-textarea" rows={2} value={editNote} onChange={(event) => setEditNote(event.target.value)} placeholder="Optional note" />
                  </div>
                ) : <div className="reminder-item-main">
                  <strong className={reminder.status !== "pending" ? "reminder-done" : ""}>
                    {reminder.title}
                  </strong>
                  {reminder.note && <p>{reminder.note}</p>}
                  <span className="reminder-meta">
                    {formatTime(reminder.due_at)} · {reminder.status}
                    {reminder.recurrence ? ` · ${reminder.recurrence}` : ""}
                  </span>
                </div>}
                <div className="reminder-item-actions">
                  {editingId === reminder.id ? <>
                    <button type="button" className="transcript-action-button" onClick={() => void handleEdit(reminder.id)} disabled={saving || !editTitle.trim()}>Save</button>
                    <button type="button" className="transcript-action-button secondary" onClick={() => setEditingId(null)} disabled={saving}>Cancel</button>
                  </> : <button type="button" className="transcript-action-button secondary" onClick={() => beginEdit(reminder)}>Edit</button>}
                  {reminder.status === "pending" && (
                    <button
                      type="button"
                      className="transcript-action-button"
                      onClick={() => void handleStatus(reminder.id, "done")}
                    >
                      Done
                    </button>
                  )}
                  <button
                    type="button"
                    className="transcript-action-button danger"
                    onClick={() => void handleDelete(reminder.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="module-note">
        Reminders are local records only. Deleting a reminder removes a database row,
        never a file. Workflow automation (n8n) remains a future, permission-gated phase.
      </div>
    </section>
  );
}

import { useEffect, useState } from "react";
import { Mail, Send, ShieldCheck, X } from "lucide-react";
import { getEmailStatus, previewEmail, sendConfirmedEmail, type EmailRequestDto, type EmailStatusDto } from "@/lib/backendAssistantClient";

const EMPTY: EmailRequestDto = { recipient: "", subject: "", body: "" };

export function EmailSkillPanel() {
  const [draft, setDraft] = useState<EmailRequestDto>(EMPTY);
  const [status, setStatus] = useState<EmailStatusDto | null>(null);
  const [preview, setPreview] = useState<EmailRequestDto | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void getEmailStatus().then(setStatus).catch(() => setMessage("Email backend is unavailable.")); }, []);
  const update = (key: keyof EmailRequestDto, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  const valid = draft.recipient.trim().includes("@") && draft.subject.trim() && draft.body.trim();

  const prepare = async () => {
    if (!valid) return;
    setBusy(true); setMessage("");
    try {
      const result = await previewEmail(draft);
      setPreview({ recipient: result.recipient || draft.recipient.trim(), subject: result.subject || draft.subject.trim(), body: result.body || draft.body.trim() });
    } catch (error) { setMessage(error instanceof Error ? error.message : "Email preview failed."); }
    finally { setBusy(false); }
  };

  const send = async () => {
    if (!preview) return;
    setBusy(true); setMessage("");
    try {
      const result = await sendConfirmedEmail(preview);
      setMessage(result.message);
      if (result.sent) { setDraft(EMPTY); setPreview(null); }
    } catch (error) { setMessage(error instanceof Error ? error.message : "Email delivery failed."); }
    finally { setBusy(false); }
  };

  return <section className="nx-card nx-email-skill">
    <div className="nx-card-head"><div className="nx-card-title"><Mail /> Direct Email</div><span className={`nx-list-badge ${status?.configured ? "ok" : "mid"}`}>{status?.configured ? status.provider : "Setup"}</span></div>
    <p className="nx-hint">Compose, review and explicitly confirm every email before Nexa sends it.</p>
    {!status?.configured && <div className="nx-email-setup">{status?.message || "Checking email provider…"}</div>}
    <div className="nx-email-fields">
      <input className="nx-input" type="email" autoComplete="off" placeholder="Recipient email" value={draft.recipient} onChange={(event) => update("recipient", event.target.value)} />
      <input className="nx-input" placeholder="Subject" value={draft.subject} onChange={(event) => update("subject", event.target.value)} />
      <textarea className="nx-input" rows={6} placeholder="Write your email…" value={draft.body} onChange={(event) => update("body", event.target.value)} />
    </div>
    <button type="button" className="nx-btn" disabled={busy || !valid} onClick={() => void prepare()}><ShieldCheck size={15} /> Review before sending</button>
    {preview && <div className="nx-email-confirm" role="dialog" aria-label="Confirm email send">
      <div className="nx-email-confirm-head"><strong>Final delivery confirmation</strong><button type="button" onClick={() => setPreview(null)} aria-label="Close preview"><X size={15} /></button></div>
      <dl><div><dt>To</dt><dd>{preview.recipient}</dd></div><div><dt>Subject</dt><dd>{preview.subject}</dd></div></dl>
      <p>{preview.body}</p>
      <button type="button" className="nx-btn danger" disabled={busy || !status?.configured} onClick={() => void send()}><Send size={15} /> Confirm & send email</button>
    </div>}
    {message && <p className="nx-hint">{message}</p>}
  </section>;
}

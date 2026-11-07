import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { DEFAULT_BACKEND_URL } from "@/lib/backendCommandClient";
import { exportContent, getContentHistory } from "@/lib/backendAssistantClient";

export function ContentWriterPanel() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [format, setFormat] = useState<"md" | "txt">("md");
  const [documents, setDocuments] = useState<Array<{ id: string; name: string; size: number; download_url: string }>>([]);
  const [message, setMessage] = useState("Exports are permission-gated and saved only in Nexa data.");
  const [busy, setBusy] = useState(false);

  const refresh = () => getContentHistory().then((result) => setDocuments(result.documents)).catch(() => setDocuments([]));
  useEffect(() => {
    void refresh();
  }, []);

  const save = async () => {
    if (!title.trim() || !content.trim()) return;
    setBusy(true);
    try {
      const result = await exportContent(title.trim(), content.trim(), format);
      setMessage(result.error || result.message);
      if (result.exported) { setTitle(""); setContent(""); refresh(); }
    } catch (err) { setMessage(err instanceof Error ? err.message : "Export failed."); }
    finally { setBusy(false); }
  };

  return (
    <section className="nx-card content-writer-card">
      <div className="nx-card-head"><div className="nx-card-title"><FileText /> Content Writer</div><span className="nx-list-badge mid">Local export</span></div>
      <div className="content-writer-fields">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Document title" />
        <select value={format} onChange={(e) => setFormat(e.target.value as "md" | "txt")}><option value="md">Markdown</option><option value="txt">Plain text</option></select>
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={6} placeholder="Write or paste assistant-generated content here..." />
        <button type="button" className="nx-btn primary" onClick={() => void save()} disabled={busy || !title.trim() || !content.trim()}><Download size={15} />{busy ? "Exporting..." : "Confirm & Export"}</button>
      </div>
      <p className="youtube-control-message">{message}</p>
      {documents.length > 0 && <div className="content-history">{documents.slice(0, 4).map((doc) => <a key={doc.id} href={`${DEFAULT_BACKEND_URL}${doc.download_url}`} download>{doc.name} <small>{Math.ceil(doc.size / 1024)} KB</small></a>)}</div>}
    </section>
  );
}

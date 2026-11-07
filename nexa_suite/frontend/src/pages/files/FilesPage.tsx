import { useState } from "react";
import { FolderSearch } from "lucide-react";
import {
  buildFileSearchRequest,
  requestFileSearchAction,
  FileSearchResponseDto,
} from "@/lib";
import {
  DocumentPreviewResponseDto,
  requestDocumentPreview,
} from "@/lib/backendAssistantClient";
import { PageHero } from "@/components/ui";

type SearchScope = "all_safe" | "desktop" | "downloads" | "documents";

const PREVIEWABLE_EXTENSIONS = new Set(["pdf", "txt", "md"]);

export function FilesPage() {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<SearchScope>("all_safe");
  const [extensions, setExtensions] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<FileSearchResponseDto | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [preview, setPreview] = useState<DocumentPreviewResponseDto | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setErrorMessage(null);
    setResponse(null);
    setPreview(null);
    setPreviewError(null);
    try {
      const request = buildFileSearchRequest({
        query: query.trim(),
        scope,
        extensions: extensions
          .split(",")
          .map((ext) => ext.trim())
          .filter(Boolean),
        maxResults: 30,
        originalText: query.trim(),
        source: "files_page",
        dryRun: false,
      });
      const result = await requestFileSearchAction(request);
      setResponse(result);
      if (result.status !== "completed") {
        setErrorMessage(result.message);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend server and try again.`
          : "File search failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (path: string) => {
    setPreviewLoading(true);
    setPreviewError(null);
    setPreview(null);
    try {
      const result = await requestDocumentPreview(path);
      setPreview(result);
      if (!result.previewed) {
        setPreviewError(result.error || result.message);
      }
    } catch (err) {
      setPreviewError(
        err instanceof Error ? err.message : "Document preview failed.",
      );
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <section className="page-surface module-enhanced">
      <PageHero
        icon={<FolderSearch />}
        eyebrow="File Search & Document Preview"
        title="File Control Center"
        description="Read-only search across Desktop, Downloads, and Documents. PDF/TXT/MD files can be previewed as text. Files are never modified, moved, or executed."
      />

      <div className="command-input-card">
        <p className="eyebrow">Search</p>
        <div className="files-search-grid">
          <input
            className="command-history-search-input"
            type="text"
            placeholder='File name contains... (e.g. "report" or "pdf")'
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void handleSearch();
            }}
          />
          <select
            className="command-history-select"
            value={scope}
            onChange={(event) => setScope(event.target.value as SearchScope)}
          >
            <option value="all_safe">All safe folders</option>
            <option value="desktop">Desktop</option>
            <option value="downloads">Downloads</option>
            <option value="documents">Documents</option>
          </select>
          <input
            className="command-history-search-input"
            type="text"
            placeholder="Extensions (e.g. pdf, docx)"
            value={extensions}
            onChange={(event) => setExtensions(event.target.value)}
          />
          <button
            type="button"
            className="backend-preview-button"
            onClick={() => void handleSearch()}
            disabled={loading || !query.trim()}
          >
            {loading ? "Searching..." : "Search Files"}
          </button>
        </div>
        <p className="execution-disabled-note">
          Metadata-only results. Click a PDF/TXT/MD result for a read-only text preview.
        </p>
      </div>

      {errorMessage && <div className="file-search-error">{errorMessage}</div>}

      {response && response.results.length > 0 && (
        <div className="file-search-list">
          {response.results.map((item, idx) => {
            const canPreview =
              !item.is_directory &&
              item.extension !== null &&
              item.extension !== undefined &&
              PREVIEWABLE_EXTENSIONS.has(item.extension);
            return (
              <div className="file-search-item" key={idx}>
                <div className="file-search-item-header">
                  <strong className="file-search-item-name">{item.name}</strong>
                  <span className={`file-search-badge${item.is_directory ? " dir" : ""}`}>
                    {item.is_directory ? "Directory" : "File"}
                  </span>
                </div>
                <div className="file-search-item-path">{item.path}</div>
                <div className="file-search-item-meta">
                  {item.extension && <span>.{item.extension}</span>}
                  {item.size_bytes !== null && item.size_bytes !== undefined && (
                    <span>{(item.size_bytes / 1024).toFixed(1)} KB</span>
                  )}
                  {item.modified_at && (
                    <span>{new Date(item.modified_at).toLocaleString()}</span>
                  )}
                  {canPreview && (
                    <button
                      type="button"
                      className="transcript-action-button"
                      onClick={() => void handlePreview(item.path)}
                      disabled={previewLoading}
                    >
                      {previewLoading ? "Loading..." : "Preview Text"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {response && response.result_count === 0 && response.status === "completed" && (
        <div className="file-search-empty">No files found matching your query.</div>
      )}

      {!response && !errorMessage && !loading && (
        <div className="file-search-empty">
          Search safe folders by partial file name. Try "pdf" in Downloads.
        </div>
      )}

      {previewError && <div className="file-search-error">{previewError}</div>}

      {preview && preview.previewed && (
        <div className="document-preview-card">
          <div className="audit-health-header">
            <p className="eyebrow">
              Read-only preview: {preview.name}
              {preview.page_count !== null && preview.page_count !== undefined
                ? ` (${preview.page_count} pages)`
                : ""}
            </p>
            <button
              type="button"
              className="audit-health-button"
              onClick={() => setPreview(null)}
            >
              Close Preview
            </button>
          </div>
          {preview.preview_text ? (
            <pre className="document-preview-text">{preview.preview_text}</pre>
          ) : (
            <div className="file-search-empty">
              No extractable text (this may be a scanned/image PDF).
            </div>
          )}
          {preview.truncated && (
            <div className="backend-preview-note">Preview truncated to the first part of the document.</div>
          )}
          <div className="file-search-notes">
            {preview.safety_notes.map((note, i) => (
              <div key={i} className="file-search-note">{note}</div>
            ))}
          </div>
        </div>
      )}

      <div className="module-note">
        File operations (move/rename/delete/organize) stay disabled by safety policy.
      </div>
    </section>
  );
}

import { useState } from "react";
import { Terminal } from "lucide-react";
import { ActionConfirmationCard } from "@/components/action-confirmation";
import { ActionPreviewCard } from "@/components/action-preview";
import { PageHero } from "@/components/ui";
import { BackendCommandPreviewResponse, CommandUnderstandingResult, FileSearchResponseDto, buildAppActionRequest, buildFileSearchRequest, buildWebsiteActionRequest, containsDangerousCommandPhrase, createActionPreview, createCommandHistoryEntry, detectAppKeyFromText, detectCommandIntent, detectFileSearchHints, getIntentLabel, isCommandSensitive, requestBackendCommandPreview, requestFileSearchAction, requestOpenAppAction, requestOpenWebsiteAction, saveCommandHistoryEntry, shouldAskConfirmation } from "@/lib";

export function CommandsPage() {
  const defaultCommand = "ইউটিউব খুলে একটা বাংলা গান চালাও";
  const [commandInput, setCommandInput] = useState(defaultCommand);
  const [result, setResult] = useState<CommandUnderstandingResult>(() => detectCommandIntent(defaultCommand));
  const actionPreview = createActionPreview(result);

  const [backendPreview, setBackendPreview] = useState<BackendCommandPreviewResponse | null>(null);
  const [backendPreviewLoading, setBackendPreviewLoading] = useState(false);
  const [backendPreviewError, setBackendPreviewError] = useState<string | null>(null);

  const [commandExecutionLoading, setCommandExecutionLoading] = useState(false);
  const [commandExecutionResultMessage, setCommandExecutionResultMessage] = useState<string | null>(null);
  const [commandExecutionErrorMessage, setCommandExecutionErrorMessage] = useState<string | null>(null);

  const [fileSearchLoading, setFileSearchLoading] = useState(false);
  const [fileSearchResponse, setFileSearchResponse] = useState<FileSearchResponseDto | null>(null);
  const [fileSearchError, setFileSearchError] = useState<string | null>(null);

  const commandTextForCheck = (result.normalizedText || commandInput).toLowerCase();

  const websiteKeywords = [
    "youtube", "google", "github", "facebook", "gmail",
    "chatgpt", "stackoverflow", "ইউটিউব", "গুগল", "ফেসবুক",
  ];

  const appKeywords = [
    "notepad", "calculator", "calc", "chrome",
    "file explorer", "explorer", "vscode", "vs code",
    "নোটপ্যাড", "ক্যালকুলেটর", "ক্রোম",
  ];

  const isWebsiteExecutionCandidate =
    result.intent === "open_website" ||
    result.intent === "youtube_search" ||
    websiteKeywords.some((kw) => commandTextForCheck.includes(kw));

  const isAppExecutionCandidate =
    result.intent === "open_app" ||
    appKeywords.some((kw) => commandTextForCheck.includes(kw));

  const isSupportedExecutionCandidate = isWebsiteExecutionCandidate || isAppExecutionCandidate;

  const getWebsiteTargetFromCommand = (): { value: string; label: string } | null => {
    const lower = commandTextForCheck;
    if (result.intent === "youtube_search" || lower.includes("youtube") || lower.includes("ইউটিউব"))
      return { value: "youtube", label: "YouTube" };
    if (lower.includes("google") || lower.includes("গুগল"))
      return { value: "google", label: "Google" };
    if (lower.includes("github"))
      return { value: "github", label: "GitHub" };
    if (lower.includes("facebook") || lower.includes("ফেসবুক"))
      return { value: "facebook", label: "Facebook" };
    if (lower.includes("gmail") || lower.includes("জিমেইল"))
      return { value: "gmail", label: "Gmail" };
    if (lower.includes("chatgpt"))
      return { value: "chatgpt", label: "ChatGPT" };
    if (lower.includes("stackoverflow") || lower.includes("stack overflow"))
      return { value: "stackoverflow", label: "Stack Overflow" };
    return null;
  };

  const websiteTarget = getWebsiteTargetFromCommand();

  const getAppTargetFromCommand = (): { value: string; label: string } | null => {
    if (containsDangerousCommandPhrase(commandInput)) return null;
    const key = detectAppKeyFromText(commandInput);
    if (key) {
      const map: Record<string, { value: string; label: string }> = {
        notepad: { value: "notepad", label: "Notepad" },
        calculator: { value: "calculator", label: "Calculator" },
        chrome: { value: "chrome", label: "Google Chrome" },
        file_explorer: { value: "file_explorer", label: "File Explorer" },
        vscode: { value: "vscode", label: "Visual Studio Code" },
      };
      return map[key] ?? null;
    }
    const lower = commandTextForCheck;
    if ((result.intent as string) === "open_app" || lower.includes("notepad") || lower.includes("note pad") || lower.includes("নোটপ্যাড"))
      return { value: "notepad", label: "Notepad" };
    if ((result.intent as string) === "open_app" || lower.includes("calculator") || lower.includes("calc") || lower.includes("ক্যালকুলেটর"))
      return { value: "calculator", label: "Calculator" };
    if (lower.includes("chrome") || lower.includes("google chrome") || lower.includes("ক্রোম"))
      return { value: "chrome", label: "Google Chrome" };
    if (lower.includes("file explorer") || lower.includes("explorer") || lower.includes("files") || lower.includes("ফাইল"))
      return { value: "file_explorer", label: "File Explorer" };
    if (lower.includes("vscode") || lower.includes("vs code") || lower.includes("visual studio code"))
      return { value: "vscode", label: "Visual Studio Code" };
    return null;
  };

  const appTarget = getAppTargetFromCommand();

  const executionTargetLabel =
    result.entities.url ||
    result.entities.website ||
    result.entities.app ||
    websiteTarget?.label ||
    appTarget?.label ||
    null;

  const executionTargetValue =
    result.entities.url ||
    result.entities.website ||
    result.entities.app ||
    websiteTarget?.value ||
    appTarget?.value ||
    null;

  const handleCommandExecutionConfirm = async () => {
    setCommandExecutionLoading(true);
    setCommandExecutionResultMessage(null);
    setCommandExecutionErrorMessage(null);

    try {
      if (isWebsiteExecutionCandidate) {
        const target = getWebsiteTargetFromCommand();
        if (!target) {
          setCommandExecutionErrorMessage("Could not detect a supported website from this command.");
          return;
        }
        const request = buildWebsiteActionRequest({
          targetValue: target.value,
          label: target.label,
          originalText: commandInput,
          normalizedText: result.normalizedText || commandInput.toLowerCase(),
          confidence: result.confidence,
          userConfirmed: true,
          dryRun: false,
          source: "commands_page",
        });
        const response = await requestOpenWebsiteAction(request);
        if (response.executed) {
          setCommandExecutionResultMessage("Website opened successfully.");
        } else if (response.status === "blocked" || response.status === "failed") {
          setCommandExecutionErrorMessage(response.error || response.message);
        } else {
          setCommandExecutionResultMessage(response.message);
        }
      } else if (isAppExecutionCandidate) {
        const target = getAppTargetFromCommand();
        if (!target) {
          setCommandExecutionErrorMessage("Could not detect a supported app from this command.");
          return;
        }
        const request = buildAppActionRequest({
          targetValue: target.value,
          label: target.label,
          originalText: commandInput,
          normalizedText: result.normalizedText || commandInput.toLowerCase(),
          confidence: result.confidence,
          userConfirmed: true,
          dryRun: false,
          source: "commands_page",
        });
        const response = await requestOpenAppAction(request);
        if (response.executed) {
          setCommandExecutionResultMessage("App opened successfully.");
        } else if (response.status === "blocked" || response.status === "failed") {
          setCommandExecutionErrorMessage(response.error || response.message);
        } else {
          setCommandExecutionResultMessage(response.message);
        }
      } else {
        setCommandExecutionErrorMessage("This command is not supported for execution yet.");
      }
    } catch (err) {
      setCommandExecutionErrorMessage(
        err instanceof Error ? err.message : "Execution request failed.",
      );
    } finally {
      setCommandExecutionLoading(false);
    }
  };

  const handleCommandExecutionCancel = () => {
    setCommandExecutionResultMessage(null);
    setCommandExecutionErrorMessage(null);
  };

  const getFileSearchTargetFromCommand = (): { query: string; scope: "desktop" | "downloads" | "documents" | "all_safe"; extensions: string[] } | null => {
    const hints = detectFileSearchHints(commandInput);
    if (!hints.isFileSearch) return null;

    const scope = hints.scope;
    const extensions = hints.extensions;

    const cleanWords = [
      "khuje dao", "khuje ber koro", "khujun", "find", "search",
      "file", "folder", "e", "theke", "koro",
      "খুঁজে দাও", "খুঁজুন", "বের করো", "ফাইল খুঁজে দাও",
      "folder e", "folder theke", "ফোল্ডারে", "থেকে",
      "downloads", "download", "ডাউনলোড", "ডাউনলোডস",
      "desktop", "desk", "ডেস্কটপ",
      "documents", "docs", "document", "ডকুমেন্ট", "ডকুমেন্টস",
      "pdf", "পিডিএফ",
      "doc", "docx", "word", "ওয়ার্ড", "ডক",
      "image", "photo", "png", "jpg", "jpeg", "ছবি", "ইমেজ",
      "excel", "xls", "xlsx", "এক্সেল",
      "ppt", "pptx", "powerpoint", "presentation", "পাওয়ারপয়েন্ট", "প্রেজেন্টেশন",
    ];
    let query = commandTextForCheck;
    for (const word of cleanWords) {
      query = query.replace(word, "");
    }
    query = query.trim();
    if (!query && extensions.length > 0) query = extensions[0];
    if (!query) query = commandInput.toLowerCase();

    return { query, scope, extensions };
  };

  const isFileSearchCandidate = getFileSearchTargetFromCommand() !== null;

  const handleFileSearch = async () => {
    const target = getFileSearchTargetFromCommand();
    if (!target) return;
    setFileSearchLoading(true);
    setFileSearchError(null);
    setFileSearchResponse(null);
    try {
      const request = buildFileSearchRequest({
        query: target.query,
        scope: target.scope,
        extensions: target.extensions,
        maxResults: 20,
        originalText: commandInput,
        source: "commands_page",
        dryRun: false,
      });
      const response = await requestFileSearchAction(request);
      setFileSearchResponse(response);
    } catch (err) {
      setFileSearchError(
        err instanceof Error ? err.message : "File search request failed.",
      );
    } finally {
      setFileSearchLoading(false);
    }
  };

  const handleBackendPreview = async () => {
    setBackendPreviewLoading(true);
    setBackendPreviewError(null);
    setBackendPreview(null);
    try {
      const response = await requestBackendCommandPreview(result);
      setBackendPreview(response);
    } catch (err) {
      setBackendPreviewError(
        err instanceof Error ? err.message : "Backend preview request failed",
      );
    } finally {
      setBackendPreviewLoading(false);
    }
  };

  const [historySaveMessage, setHistorySaveMessage] = useState<string | null>(null);
  const [historySaveError, setHistorySaveError] = useState<string | null>(null);

  const handleSaveToHistory = () => {
    setHistorySaveMessage(null);
    setHistorySaveError(null);
    try {
      const entry = createCommandHistoryEntry({
        source: "commands_page",
        result,
        actionPreview,
        backendPreview: backendPreview ?? undefined,
      });
      saveCommandHistoryEntry(entry);
      setHistorySaveMessage("Saved to local command history.");
    } catch {
      setHistorySaveError("Failed to save command history.");
    }
  };

  const examples = [
    { label: "YouTube Bangla", value: "ইউটিউব খুলে একটা বাংলা গান চালাও" },
    { label: "Find PDF File", value: "Downloads folder theke PDF file khuje dao" },
    { label: "Draft Email", value: "Boss ke email draft koro" },
    { label: "Delete Folder", value: "Delete folder ta clean koro" },
    { label: "Light Off", value: "Light off koro" },
  ];

  const handleInputChange = (value: string) => {
    setCommandInput(value);
    setResult(detectCommandIntent(value));
  };

  const applyExample = (value: string) => {
    setCommandInput(value);
    setResult(detectCommandIntent(value));
  };

  return (
    <section className="page-surface module-enhanced command-lab-layout">
      <PageHero
        icon={<Terminal />}
        eyebrow="Command Understanding"
        title="Commands Lab"
        description="Interactive testing ground for Bengali, English, and Banglish command understanding. Previews never execute real actions."
      />

      <div className="command-input-card">
        <p className="eyebrow">Command input</p>
        <textarea
          className="command-lab-textarea"
          value={commandInput}
          onChange={(event) => handleInputChange(event.target.value)}
          rows={5}
          placeholder="Enter a command to see detection results"
        />

        <div className="command-example-row">
          {examples.map((example) => (
            <button
              key={example.label}
              type="button"
              className="command-example-button"
              onClick={() => applyExample(example.value)}
            >
              {example.label}
            </button>
          ))}
        </div>

        <p className="execution-disabled-note">
          Command execution is disabled in this phase. This is a preview-only command lab.
        </p>
      </div>

      <div className="command-result-card">
        <p className="eyebrow">Result preview</p>
        <div className="command-result-grid">
          <div className="command-result-row">
            <span>Original text</span>
            <strong>{result.originalText || "—"}</strong>
          </div>
          <div className="command-result-row">
            <span>Normalized text</span>
            <strong>{result.normalizedText || "—"}</strong>
          </div>
          <div className="command-result-row">
            <span>Intent label</span>
            <strong>{getIntentLabel(result.intent)}</strong>
          </div>
          <div className="command-result-row">
            <span>Raw intent</span>
            <strong>{result.intent}</strong>
          </div>
          <div className="command-result-row">
            <span>Language</span>
            <strong>{result.language}</strong>
          </div>
          <div className="command-result-row">
            <span>Confidence</span>
            <strong>{result.confidence}%</strong>
          </div>
          <div className="command-result-row">
            <span>Risk level</span>
            <strong className={`command-risk-${result.riskLevel}`}>{result.riskLevel}</strong>
          </div>
          <div className="command-result-row">
            <span>Confirmation required</span>
            <strong>{shouldAskConfirmation(result) ? "Yes" : "No"}</strong>
          </div>
          <div className="command-result-row">
            <span>Sensitive</span>
            <strong>{isCommandSensitive(result) ? "Yes" : "No"}</strong>
          </div>
          <div className="command-result-row">
            <span>Can execute</span>
            <strong>No</strong>
          </div>
          <div className="command-result-row">
            <span>Explanation</span>
            <strong>{result.explanation}</strong>
          </div>
          {result.confirmationReason && (
            <div className="command-result-row">
              <span>Confirmation reason</span>
              <strong>{result.confirmationReason}</strong>
            </div>
          )}
        </div>

        <div className="entities-box">
          <p className="eyebrow">Entities</p>
          {Object.keys(result.entities).length === 0 ? (
            <p>No entities detected yet.</p>
          ) : (
            <div className="command-result-grid">
              {Object.entries(result.entities).map(([key, value]) => (
                <div className="command-result-row" key={key}>
                  <span>{key}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="command-action-preview-wrap">
        <ActionPreviewCard preview={actionPreview} />
      </div>

      <div className="command-preview-note">
        Execution is disabled. Preview only.
      </div>

      <div className="history-save-row">
        <button
          type="button"
          className="history-save-button"
          onClick={handleSaveToHistory}
        >
          Save Preview to History
        </button>
        {historySaveMessage && (
          <span className="history-save-message">{historySaveMessage}</span>
        )}
        {historySaveError && (
          <span className="history-save-error">{historySaveError}</span>
        )}
      </div>

      <div className="backend-preview-card">
        <p className="eyebrow">Backend Preview</p>
        <div className="backend-preview-actions">
          <button
            type="button"
            className="backend-preview-button"
            onClick={handleBackendPreview}
            disabled={backendPreviewLoading}
          >
            {backendPreviewLoading ? "Requesting..." : "Request Backend Preview"}
          </button>
        </div>

        {backendPreviewError && (
          <div className="backend-preview-error">{backendPreviewError}</div>
        )}

        {backendPreview && (
          <div className="backend-preview-grid">
            <div className="backend-preview-row">
              <span>Status</span>
              <strong>{backendPreview.status}</strong>
            </div>
            <div className="backend-preview-row">
              <span>Can execute</span>
              <strong>{String(backendPreview.can_execute)}</strong>
            </div>
            <div className="backend-preview-row">
              <span>Execution mode</span>
              <strong>{backendPreview.execution_mode}</strong>
            </div>
            <div className="backend-preview-row">
              <span>Message</span>
              <strong>{backendPreview.message}</strong>
            </div>
            <div className="backend-preview-row">
              <span>Intent</span>
              <strong>{backendPreview.intent}</strong>
            </div>
            <div className="backend-preview-row">
              <span>Risk level</span>
              <strong>{backendPreview.risk_level}</strong>
            </div>

            {backendPreview.preview_steps.length > 0 && (
              <div className="backend-preview-steps">
                <span>Preview steps</span>
                <ul>
                  {backendPreview.preview_steps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </ul>
              </div>
            )}

            {backendPreview.warning && (
              <div className="backend-preview-row">
                <span>Warning</span>
                <strong>{backendPreview.warning}</strong>
              </div>
            )}

            {backendPreview.blocked_reason && (
              <div className="backend-preview-row">
                <span>Blocked reason</span>
                <strong>{backendPreview.blocked_reason}</strong>
              </div>
            )}
          </div>
        )}

        <div className="backend-preview-note">
          Backend preview is still execution-disabled.
        </div>
      </div>

      <div className="commands-execution-wrap">
        <ActionConfirmationCard
          intent={result.intent}
          targetLabel={executionTargetLabel}
          targetValue={executionTargetValue}
          riskLevel={result.riskLevel}
          disabled={!isSupportedExecutionCandidate}
          loading={commandExecutionLoading}
          resultMessage={commandExecutionResultMessage}
          errorMessage={commandExecutionErrorMessage}
          onConfirm={handleCommandExecutionConfirm}
          onCancel={handleCommandExecutionCancel}
        />
        <div className="commands-execution-note">
          Execution UI is prepared. Real execution will be connected in the next step.
        </div>
      </div>

      <div className="file-search-panel">
        <div className="file-search-header">
          <p className="eyebrow">File Search</p>
          <button
            type="button"
            className="file-search-button"
            onClick={handleFileSearch}
            disabled={fileSearchLoading || !isFileSearchCandidate}
          >
            {fileSearchLoading ? "Searching..." : "Search Files"}
          </button>
        </div>

        {fileSearchError && (
          <div className="file-search-error">{fileSearchError}</div>
        )}

        {fileSearchResponse && (
          <>
            <div className="file-search-meta">
              <span>Status: <strong>{fileSearchResponse.status}</strong></span>
              <span>Scope: <strong>{fileSearchResponse.scope}</strong></span>
              <span>Query: <strong>{fileSearchResponse.query}</strong></span>
              <span>Results: <strong>{fileSearchResponse.result_count}</strong></span>
            </div>
            <p className="file-search-message">{fileSearchResponse.message}</p>
            {fileSearchResponse.safety_notes && fileSearchResponse.safety_notes.length > 0 && (
              <div className="file-search-notes">
                {fileSearchResponse.safety_notes.map((note, i) => (
                  <div key={i} className="file-search-note">{note}</div>
                ))}
              </div>
            )}
            {fileSearchResponse.results.length > 0 && (
              <div className="file-search-list">
                {fileSearchResponse.results.map((item, idx) => (
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
                    </div>
                  </div>
                ))}
              </div>
            )}
            {fileSearchResponse.result_count === 0 && fileSearchResponse.status === "completed" && (
              <div className="file-search-empty">No files found matching your query.</div>
            )}
          </>
        )}

        {!fileSearchResponse && !fileSearchError && (
          <div className="file-search-empty">
            {isFileSearchCandidate
              ? 'Click "Search Files" to search for matching files in safe folders.'
              : 'Type a search-related command (e.g. "find pdf", "search docx in downloads") to enable file search.'}
          </div>
        )}
      </div>

      <div className="module-note">
        Actual command execution will remain disabled until the command engine and confirmation flow are fully implemented.
      </div>
    </section>
  );
}
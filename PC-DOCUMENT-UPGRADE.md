# PC and document improvements — 27 October 2026

The existing Mark engine and native Qt UI are retained.

- file_controller now exposes `open` for folders with explicit OS-request acknowledgement, without claiming visible-window verification. Downloads uses the Windows redirected-folder registry value. Bengali folder aliases resolve Downloads/Desktop/Documents.
- TXT and DOCX extract_text returns document text rather than creating a derived file. It explicitly marks truncation above 40,000 characters.
- TXT/DOCX and PDF summaries default to read-only output rather than silently exporting long answers. Their prompts request Bengali unless another language is explicitly requested and retain the user's instruction.
- PDF empty-page text extraction is null-safe. Scanned files still require OCR; this change does not implement OCR.
- Corrected file_processor's compact schema guidance to use actual file_path/action/instruction fields.
- Native engine instructions route folder requests to file_controller and sourced lookups to web_search. Existing search providers/fallback remain; no new search provider was added.

Validation: six new focused regression tests passed plus seven existing integration tests; compilation passed. New tests use temporary real TXT/DOCX files, mocked OS launching and mocked model/search responses. They verify extraction, absence of unintended exports, summary instruction construction, folder aliases/missing-folder handling and preserved source URLs. They do not certify live model language compliance, actual Explorer visibility, microphone recognition, network search availability or PDF extraction end to end.

Backup: `../backups/before-pc-document-upgrade-20261027.zip`. Restart the assistant to load the updated tools and prompt. Existing FEATURE-TEST-REPORT.md describes the earlier state; its TXT extraction defect is addressed by this update.

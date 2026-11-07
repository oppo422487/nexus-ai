# Nexa AI + Mark feature verification

Date: 25 October 2026 (Asia/Dhaka).

## Result

Partial pass. Real web retrieval and real text summarization work at the service/tool level. The merged native chat flow is **not fully verified**. A document extraction defect and a live gateway timeout prevent a full pass.

Story tested: original Nexa chat interface -> native engine gateway -> search/file tool -> result -> chat rendering. Separate direct service tests distinguish working tools from an unverified interface flow.

| Check | Result | Evidence |
| --- | --- | --- |
| Existing Nexa web service | PASS | Live POST `/api/web/answer`, question `Python programming language`: completed, answered=true, DuckDuckGo Instant Answer, Wikipedia source URL. |
| Existing Nexa document preview | PASS for TXT | Live POST `/api/documents/preview` returned the fixture's complete 157-byte contents, including NEXA-QA-731; previewed=true, truncated=false. |
| Native Mark web_search tool | PASS with fallback | Real query `Python programming language official documentation` returned six linked search results, including python.org/doc and docs.python.org, in 18.64 seconds. Gemini grounding reported model availability/quota failures; DuckDuckGo fallback supplied results. |
| Native file_processor extract_text | FAIL for returning contents | TXT request returned only `Text extracted. Saved: feature-qa_extracted.txt`, without the document text. It created a derived file despite save=false. Original fixture hash was unchanged. |
| Native file_processor summarize | PASS for content, TXT only | Real model call completed in 8.44 seconds. Summary: `Nexa QA: 2/3 tasks complete, budget 1200 taka, deadline 30 October 2026. Code: NEXA-QA-731.` These facts match the fixture. Default tool response was English; Bangla output was not established by this direct test. |
| Live original UI -> engine -> tool -> rendered result | INCOMPLETE | An isolated Playwright browser loaded the native chat input, but its baseline GET `/api/engine/events` timed out after 10 seconds before submitting the first QA prompt. No claim of actual UI tool invocation or rendered answer is made. Another direct snapshot earlier returned connected=true; this does not eliminate intermittent responsiveness issues. |
| Existing targeted automated tests | PASS | `pytest -q tests/test_chat.py -k 'web or summary or document' tests/test_engine_gateway.py`: 7 passed, 87 deselected, one Starlette deprecation warning. These include mocked routing tests and do not prove live model/UI behavior. The keyword filter did not select the gateway tests. |

## Reproduction and fixes needed

1. `actions/file_processor.py`, `_process_text_doc`: its extract_text branch checks `file_type != 'txt'`, but text dispatch passes `'text'`. Consequently TXT input takes the export branch and returns a filename. Return extracted text for read requests, and honor save=false for export behavior. This was identified, not changed, during this report's testing.
2. The live UI test failed at the engine-events boundary. Diagnose gateway responsiveness/host resource pressure before repeating end-to-end assertions. A timeout alone does not establish its root cause. Browser test source: `tests/live_feature_verification.py`.
3. Verify file selection/upload in the modern interface separately. Native chat bypasses the old Nexa `/api/chat/message` flow; preserving backend code does not prove that its file-summary workflow is integrated into native chat.

## Test scope and artifacts

Only synthetic test content was used: 3 tasks, 2 complete, budget 1200 taka, deadline 30 October 2026, code NEXA-QA-731. Original document remained unchanged. No emails or messages were sent to others. Tests used the configured model/network providers and may consume their normal quota.

Runtime evidence: `nexa_suite/runtime/feature-api-results.json`, `native-feature-results.json`, and `feature-qa.txt`. The extraction test also produced `feature-qa_extracted.txt`. No PDF, scanned PDF/OCR, DOCX, large document, physical microphone, or full Bangla summary flow was certified in this run.

Overall: the features are not all broken, but saying that all three work properly throughout the combined application would exceed the evidence.

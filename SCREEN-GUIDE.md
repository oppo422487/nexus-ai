# Screen Guide — read-only accessibility assistance

Open **Screen Guide** in the sidebar or **Settings → Screen Guide**. The interface is native Python/Qt, with no web renderer or continuous screen capture.

## How to use

1. Move the target app to the primary display.
2. Click **Capture screen in 3 seconds**. The settings window hides; use Alt+Tab to show the target app during the countdown. Alternatively choose an existing screenshot file.
3. Inspect the preview. Nothing is uploaded at this stage.
4. Optionally drag a rectangle over the image and click **Use selected area**. Only the resulting cropped preview will be analyzed.
5. Enter a question, for example **Where is Export?**, **Explain this form**, or **What should I do next?**
6. Click **Share preview & explain** and approve sharing the selected preview with the configured Gemini visual API.
7. Read the guide and approximate numbered highlights. Use **Read guide aloud** to ask the existing conversation engine to read the guide in your language.
8. Capture again after the screen changes. **Clear image & guide** removes the current preview/result from this panel.

The image stays in memory and is not saved by this feature. Choosing a screenshot does not modify the original file. Shared images can contain visible private information, so inspect/crop before approving. Guide text read aloud or returned through chat can be retained by the app's existing conversation history; clearing this panel does not erase that history. The configured cloud service has its own data-handling policies.

## Voice/chat route

Ask Nexa: “এই স্ক্রিনটা বুঝিয়ে দাও”, “Export বাটনটা কোথায়?”, or “এই ফর্মে পরের ধাপে কী দেব?” The `nexa_screen_guide` tool captures one requested primary-display screenshot in memory, then requires native physical confirmation before uploading it. For visual inspection/cropping before approval, use the Screen Guide page instead. The spoken answer is Bengali by default unless another language is explicitly requested.

This is guidance only. It does not click, type, submit forms, send messages, infer passwords or run commands. A separate explicit user request is needed for any existing desktop-control feature. Screenshot contents are untrusted data, never instructions. The model is instructed not to invent invisible controls or repeat credentials; recognized token patterns in generated text are redacted, but this is not a universal secret detector. The visual model can still make mistakes. Highlights are approximate, not verified click coordinates.

## Model connection

Screen Guide uses a structured-image `VISION` tier in the existing central Gemini adapter, with JSON output and a short REST visual-model fallback list. It avoids the audio-transcription one-shot path and text-only sidecar providers. Existing conversation, SMART, FAST and SEARCH routing is unchanged. Each visual REST request has a deadline and one SDK attempt; no automatic screen recapture occurs.

**Current live-test limitation (28 October 2026):** the configured account's synthetic visual test returned timeouts/unavailable responses, and a separate minimal generation check returned HTTP 503. Metadata/model listing was reachable, but successful live image analysis has not been verified on this connection. The UI reports analysis failure rather than fabricated guidance. Recheck when the API service/connection is available. No user screenshot was uploaded for these tests.

## Verification

110 automated regression tests passed, including screenshot-sharing approval, declined consent, local crop/clear, bounding-box validation, credential-pattern redaction, invalid-model handling, read-only prompt rules, dedicated vision routing and Qt image-buffer ownership after Pillow buffers are freed. Native preview uses a synthetic form; no real mouse click, typing, email sending or user screen capture was used for testing.

Source files: `core/screen_guide.py`, `core/screen_guide_ui.py`, `plugins/nexa_screen_guide.py`; navigation and read-only guidance instructions are wired into the existing Qt UI and prompt. The private GitHub source backup preserves the preceding Teach mode version before this change. Runtime images/logs and account credentials remain excluded from Git.

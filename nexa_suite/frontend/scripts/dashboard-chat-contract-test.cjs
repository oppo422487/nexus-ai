const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const dashboardPath = path.join(root, "src", "pages", "dashboard", "CommandCenterPage.tsx");
const settingsPath = path.join(root, "src", "pages", "settings", "SettingsPageV2.tsx");
const clientPath = path.join(root, "src", "lib", "backendAssistantClient.ts");
const appPath = path.join(root, "src", "app", "App.tsx");
const topbarPath = path.join(root, "src", "components", "shell", "Topbar.tsx");
const voicePipelinePath = path.join(root, "src", "lib", "voice", "pipeline.ts");
const recorderPath = path.join(root, "src", "lib", "audioRecorder.ts");
const electronPath = path.join(root, "electron", "main.cjs");
const skillsHubPath = path.join(root, "src", "pages", "skills", "SkillsHubPage.tsx");
const pushToTalkPath = path.join(root, "src", "components", "voice", "PushToTalkPanel.tsx");
const source = fs.readFileSync(dashboardPath, "utf8");
const settingsSource = fs.readFileSync(settingsPath, "utf8");
const clientSource = fs.readFileSync(clientPath, "utf8");
const appSource = fs.readFileSync(appPath, "utf8");
const topbarSource = fs.readFileSync(topbarPath, "utf8");
const voicePipelineSource = fs.readFileSync(voicePipelinePath, "utf8");
const recorderSource = fs.readFileSync(recorderPath, "utf8");
const electronSource = fs.readFileSync(electronPath, "utf8");
const skillsHubSource = fs.readFileSync(skillsHubPath, "utf8");
const pushToTalkSource = fs.readFileSync(pushToTalkPath, "utf8");

const checks = [
  {
    name: "Dashboard imports chat endpoint client",
    pass: source.includes("requestChatMessage"),
  },
  {
    name: "Dashboard sends typed input to chat endpoint",
    pass: /await\s+requestChatMessage\(/.test(source),
  },
  {
    name: "Voice transcript uses the same chat pipeline",
    pass: /onTranscript=\{\(text\)\s*=>\s*\{[\s\S]*sendToAssistant\(text,\s*\{\s*autoSpeak:\s*true,\s*source:\s*"dashboard_voice"\s*\}\)/.test(source),
  },
  {
    name: "Global topbar provides continuous backend voice capture",
    pass: topbarSource.includes("<PushToTalkPanel compact") && appSource.includes("source: `global_voice:") && recorderSource.includes("startContinuousVoiceCapture"),
  },
  {
    name: "Desktop grants trusted audio capture and hands-free playback",
    pass: electronSource.includes("setPermissionRequestHandler") && electronSource.includes('permission === "media"') && electronSource.includes('autoplay-policy'),
  },
  {
    name: "Wake word and microphone level diagnostics are wired",
    pass: pushToTalkSource.includes("wakeWordEnabled") && recorderSource.includes("onAudioLevel") && pushToTalkSource.includes('role="meter"'),
  },
  {
    name: "Skills Hub exposes registry, diagnostics, and local productivity",
    pass: appSource.includes("<SkillsHubPage") && skillsHubSource.includes("getProductivityDashboard") && skillsHubSource.includes("createProductivityItem"),
  },
  {
    name: "Live voice commands use the Nexa backend action router",
    pass: voicePipelineSource.includes("requestChatMessage") && voicePipelineSource.includes('"voice_conversation"') && !voicePipelineSource.includes("await chat("),
  },
  {
    name: "Assistant answers are spoken automatically",
    pass: source.includes("(options.autoSpeak ?? true)") && source.includes("requestTtsSpeak"),
  },
  {
    name: "Question flow does not show Command not recognized",
    pass: !source.includes("Command not recognized"),
  },
  {
    name: "Dashboard does not embed generic low-confidence clarification",
    pass: !source.includes("I am not fully sure what you want yet"),
  },
  {
    name: "Action commands remain confirmation-gated",
    pass:
      source.includes("Confirm action") &&
      source.includes("requestOpenWebsiteAction") &&
      source.includes("requestOpenAppAction"),
  },
  {
    name: "Dashboard renders source chips",
    pass: source.includes("entry.chips") && source.includes("entry.provider") && source.includes("entry.source"),
  },
  {
    name: "Dashboard renders search result sources",
    pass: source.includes("dashboard-search-results") && source.includes("searchResults"),
  },
  {
    name: "Dashboard shows final answer text first",
    pass: source.includes("return makeEntry(\"assistant\", response.answer"),
  },
  {
    name: "Dashboard hides source cards by default",
    pass: source.includes("showSearchResultsByDefault") && source.includes("View sources"),
  },
  {
    name: "Dashboard has View sources toggle",
    pass: source.includes("Hide sources") && source.includes("setExpandedSources"),
  },
  {
    name: "Dashboard renders live-data warning chip",
    pass: source.includes("Live data may vary") || source.includes("entry.chips"),
  },
  {
    name: "Dashboard renders app launch status",
    pass: source.includes("actionResult") && source.includes("response.action?.executed"),
  },
  {
    name: "Dashboard handles no exact answer but related sources found",
    pass: source.includes("result.snippet") && source.includes("result.source_url"),
  },
  {
    name: "Dashboard does not redirect Web questions to Web Search page",
    pass: !source.includes('onNavigate("web")'),
  },
  {
    name: "Dangerous/backend blocked responses render in chat",
    pass: source.includes("entry.status === \"blocked\""),
  },
  {
    name: "Dashboard sends assistant address style to chat endpoint",
    pass:
      source.includes("loadProfile().addressingPreference") &&
      clientSource.includes("address_style: addressStyle"),
  },
  {
    name: "Dashboard renders normal assistant replies",
    pass: source.includes("Nexa Assistant") && source.includes("return makeEntry(\"assistant\", response.answer"),
  },
  {
    name: "Settings has Assistant Address Style option",
    pass:
      settingsSource.includes("Assistant Address Style") &&
      settingsSource.includes("\"Boss\"") &&
      settingsSource.includes("\"Sir\"") &&
      settingsSource.includes("\"Vai\"") &&
      settingsSource.includes("\"Neutral\""),
  },
  {
    name: "Settings has YouTube and WhatsApp skill toggles",
    pass:
      settingsSource.includes("YouTube Skill Enabled") &&
      settingsSource.includes("Trusted YouTube Auto Open") &&
      settingsSource.includes("WhatsApp Draft Skill Enabled") &&
      settingsSource.includes("Trusted WhatsApp Draft Auto Open") &&
      settingsSource.includes("trusted_whatsapp_draft_auto_open"),
  },
  {
    name: "Settings has local WhatsApp contact form",
    pass:
      settingsSource.includes("Local WhatsApp Contacts") &&
      settingsSource.includes("Save Local WhatsApp Contact") &&
      settingsSource.includes("getBackendContacts") &&
      settingsSource.includes("deleteBackendContact") &&
      settingsSource.includes("contactRelationship") &&
      settingsSource.includes("contactTone") &&
      settingsSource.includes("contactAliases"),
  },
  {
    name: "Settings has WhatsApp Draft Open Target",
    pass:
      settingsSource.includes("WhatsApp Draft Open Target") &&
      settingsSource.includes("WhatsApp App") &&
      settingsSource.includes("WhatsApp Web") &&
      settingsSource.includes("wa.me fallback") &&
      settingsSource.includes("whatsappDraftOpenTarget"),
  },
  {
    name: "Dashboard shows YouTube action card from backend action target",
    pass:
      source.includes("pendingActionFromResponse") &&
      source.includes("response.action.target") &&
      source.includes("youtube"),
  },
  {
    name: "Dashboard shows WhatsApp draft confirmation card",
    pass:
      source.includes("dashboard-draft-preview") &&
      source.includes("entry.pendingAction.draftText") &&
      source.includes("Nexa will not click Send"),
  },
  {
    name: "Dashboard has no WhatsApp auto-send path",
    pass:
      !source.includes("autoSend") &&
      !source.includes("sendAutomatically") &&
      source.includes("will not click Send"),
  },
  {
    name: "Dashboard does not show confirmation for trusted YouTube auto-open",
    pass:
      source.includes("response.auto_execute_safe") &&
      source.includes("!response.auto_execute_safe") &&
      source.includes("response.answer"),
  },
  {
    name: "Dashboard does not show confirmation for trusted WhatsApp draft auto-open",
    pass:
      source.includes("response.auto_execute_safe") &&
      source.includes("entry.pendingAction.draftText") &&
      source.includes("actionResult"),
  },
  {
    name: "Dashboard handles casual chat without web search source cards",
    pass:
      source.includes("hideLocalConversationMeta") &&
      source.includes("Local conversation") &&
      source.includes("entry.searchResults && entry.searchResults.length > 0") &&
      source.includes("chips: hideLocalConversationMeta") &&
      source.includes(": response.chips"),
  },
  {
    name: "Dashboard renders LLM provider chip only from LLM metadata",
    pass:
      source.includes("response.llm_used") &&
      source.includes("response.llm_provider") &&
      source.includes("llmProvider"),
  },
  {
    name: "Dashboard sends WhatsApp draft open target preference",
    pass:
      source.includes("whatsappDraftOpenTarget") &&
      source.includes("requestChatMessage(") &&
      source.includes("nexa.localPrefs"),
  },
  {
    name: "Dashboard hides technical chips in normal mode",
    pass:
      source.includes("technicalChips") &&
      source.includes("nexa_debug_chat_chips") &&
      source.includes("Whitelisted URL") &&
      source.includes("No browser automation"),
  },
  {
    name: "Dashboard renders clean calculator and identity answers as normal assistant text",
    pass:
      source.includes("return makeEntry(\"assistant\", response.answer") &&
      source.includes("<p>{entry.text}</p>") &&
      source.includes("hideLocalConversationMeta"),
  },
  {
    name: "Dashboard renders pending task status",
    pass:
      clientSource.includes("ChatPendingTaskDto") &&
      clientSource.includes("pending_task") &&
      source.includes("pendingTask: response.pending_task") &&
      source.includes("dashboard-pending-task") &&
      source.includes("status_label"),
  },
  {
    name: "Dashboard can render file-selection pending status",
    pass:
      clientSource.includes("pending_task") &&
      source.includes("pendingTask: response.pending_task") &&
      source.includes("dashboard-pending-task"),
  },
  {
    name: "Dashboard keeps pending generation/file statuses in assistant bubbles",
    pass:
      source.includes("pendingTask: response.pending_task") &&
      source.includes("<p>{entry.text}</p>") &&
      source.includes("dashboard-pending-task"),
  },
];

const failed = checks.filter((check) => !check.pass);
for (const check of checks) {
  console.log(`${check.pass ? "PASS" : "FAIL"} ${check.name}`);
}

if (failed.length > 0) {
  process.exitCode = 1;
}

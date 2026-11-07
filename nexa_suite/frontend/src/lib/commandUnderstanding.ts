export type CommandIntent =
  | "open_app"
  | "open_website"
  | "youtube_search"
  | "web_search"
  | "file_search"
  | "file_organize"
  | "email_draft"
  | "message_draft"
  | "reminder_create"
  | "study_mode"
  | "smart_home"
  | "general_assistant_query"
  | "unknown";

export type CommandRiskLevel = "safe" | "confirmation_required" | "sensitive" | "blocked";

export type CommandLanguage = "Bangla" | "English" | "Banglish" | "Mixed" | "Unknown";

export type CommandUnderstandingResult = {
  originalText: string;
  normalizedText: string;
  intent: CommandIntent;
  language: CommandLanguage;
  confidence: number;
  riskLevel: CommandRiskLevel;
  entities: Record<string, string>;
  explanation: string;
  confirmationReason?: string;
  canExecute: false;
};

export const SUPPORTED_COMMAND_INTENTS: Array<{
  intent: CommandIntent;
  label: string;
  description: string;
  defaultRiskLevel: CommandRiskLevel;
}> = [
  {
    intent: "open_app",
    label: "Open App",
    description: "Launch a desktop application.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "open_website",
    label: "Open Website",
    description: "Open a website in the browser.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "youtube_search",
    label: "YouTube Search",
    description: "Search for videos on YouTube.",
    defaultRiskLevel: "safe",
  },
  {
    intent: "web_search",
    label: "Web Search",
    description: "Search the web for information.",
    defaultRiskLevel: "safe",
  },
  {
    intent: "file_search",
    label: "File Search",
    description: "Find files on the local system.",
    defaultRiskLevel: "safe",
  },
  {
    intent: "file_organize",
    label: "File Organize",
    description: "Move or organize files on the device.",
    defaultRiskLevel: "sensitive",
  },
  {
    intent: "email_draft",
    label: "Email Draft",
    description: "Prepare an email draft.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "message_draft",
    label: "Message Draft",
    description: "Prepare a chat or message draft.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "reminder_create",
    label: "Reminder Create",
    description: "Create a reminder or calendar note.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "study_mode",
    label: "Study Mode",
    description: "Enable study or focus mode.",
    defaultRiskLevel: "safe",
  },
  {
    intent: "smart_home",
    label: "Smart Home",
    description: "Control smart home devices.",
    defaultRiskLevel: "confirmation_required",
  },
  {
    intent: "general_assistant_query",
    label: "General Assistant Query",
    description: "Ask the assistant a general question.",
    defaultRiskLevel: "safe",
  },
  {
    intent: "unknown",
    label: "Unknown",
    description: "The intent could not be determined yet.",
    defaultRiskLevel: "safe",
  },
];

export function normalizeCommandText(input: string): string {
  if (!input || typeof input !== "string") {
    return "";
  }

  return input
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

const banglaRegex = /[\u0980-\u09FF]/;
const englishLetterRegex = /[A-Za-z]/;
const banglishWords = ["koro", "khulo", "chalao", "dao", "dekhaw"];

export function detectCommandLanguage(input: string): CommandLanguage {
  const text = normalizeCommandText(input);
  if (!text) {
    return "Unknown";
  }

  const hasBangla = banglaRegex.test(text);
  const hasEnglish = englishLetterRegex.test(text);
  const hasBanglish = banglishWords.some((word) => text.includes(word));

  if (hasBangla && hasEnglish) return "Mixed";
  if (hasBanglish) return "Banglish";
  if (hasBangla) return "Bangla";
  if (hasEnglish) return "English";
  return "Unknown";
}

const youtubeKeywords = [
  "youtube",
  "you tube",
  "ইউটিউব",
  "song",
  "গান",
  "video",
  "ভিডিও",
  "play song",
  "গান চালাও",
  "চালাও",
  "সার্চ দাও",
  "search dao",
];

const openAppKeywords = [
  "open chrome",
  "chrome খুলো",
  "vscode",
  "vs code",
  "calculator",
  "notepad",
  "browser open",
  "app open koro",
  "software খুলো",
];

const openWebsiteKeywords = [
  "website open",
  "site open",
  "google.com",
  "facebook.com",
  "github.com",
  "open google",
  "google খুলো",
];

const webSearchKeywords = [
  "search",
  "google search",
  "খুঁজে দাও",
  "খবর",
  "news",
  "weather",
  "আবহাওয়া",
  "আজকের খবর",
  "meaning",
  "মানে কী",
  "stock",
  "market",
];

const fileSearchKeywords = [
  "file খুঁজে দাও",
  "ফাইল খুঁজে দাও",
  "folder খুঁজে দাও",
  "ফোল্ডার",
  "pdf খুঁজে দাও",
  "document find",
  "downloads",
  "desktop file",
  "report pdf",
];

const fileOrganizeKeywords = [
  "organize files",
  "clean downloads",
  "sort files",
  "folder clean",
  "ফাইল গুছাও",
  "ফোল্ডার গুছাও",
  "clean folder",
];

const emailDraftKeywords = [
  "email",
  "mail",
  "মেইল",
  "ইমেইল",
  "boss ke mail",
  "sir ke email",
  "draft email",
  "formal email",
];

const messageDraftKeywords = [
  "message",
  "sms",
  "whatsapp",
  "হোয়াটসঅ্যাপ",
  "মেসেজ",
  "text him",
  "friend ke message",
  "send message",
];

const reminderCreateKeywords = [
  "remind me",
  "reminder",
  "মনে করিয়ে দিও",
  "alarm",
  "এক ঘণ্টা পরে",
  "kalke remind",
  "meeting reminder",
];

const studyModeKeywords = [
  "study",
  "পড়া",
  "পড়া",
  "পরীক্ষা",
  "exam",
  "topic বুঝাও",
  "explain",
  "lesson",
  "quiz",
];

const smartHomeKeywords = [
  "light off",
  "লাইট অফ",
  "light on",
  "fan off",
  "ফ্যান অফ",
  "room light",
  "esp32",
  "relay",
  "switch off",
  "switch on",
];

import { detectAppKeyFromText, detectWebsiteKeyFromText, containsDangerousCommandPhrase, detectFileSearchHints } from "./commandPhrases";

const assistantQueryKeywords = [
  "what is",
  "কী",
  "কেন",
  "how",
  "explain generally",
  "question",
  "জিজ্ঞেস",
  "বলো",
];

const riskSensitiveKeywords = [
  "delete",
  "remove",
  "wipe",
  "clean drive",
  "format",
  "shutdown",
  "restart",
  "power off",
  "ডিলিট",
  "মুছে",
  "মুছে ফেল",
  "ফরম্যাট",
  "শাটডাউন",
  "রিস্টার্ট",
];

const riskBlockedKeywords = [
  "format c drive",
  "delete system32",
  "wipe windows",
  "delete windows",
  "registry delete",
  "permanently delete everything",
  "সিস্টেম৩২ ডিলিট",
  "উইন্ডোজ ডিলিট",
];

const strongIntentKeywords: Record<CommandIntent, string[]> = {
  open_app: openAppKeywords,
  open_website: openWebsiteKeywords,
  youtube_search: youtubeKeywords,
  web_search: webSearchKeywords,
  file_search: fileSearchKeywords,
  file_organize: fileOrganizeKeywords,
  email_draft: emailDraftKeywords,
  message_draft: messageDraftKeywords,
  reminder_create: reminderCreateKeywords,
  study_mode: studyModeKeywords,
  smart_home: smartHomeKeywords,
  general_assistant_query: assistantQueryKeywords,
  unknown: [],
};

function containsAny(text: string, phrases: string[]): boolean {
  return phrases.some((phrase) => text.includes(phrase));
}

function countMatchedKeywords(text: string, phrases: string[]): number {
  return phrases.filter((phrase) => text.includes(phrase)).length;
}

export function calculateCommandConfidence(
  input: string,
  intent: CommandIntent,
): number {
  const normalizedText = normalizeCommandText(input);
  if (!normalizedText || intent === "unknown") {
    return 0;
  }

  if (normalizedText.length < 3) {
    return 30;
  }

  if (intent === "general_assistant_query") {
    return 55;
  }

  const strongKeywords = strongIntentKeywords[intent] || [];
  const strongMatches = countMatchedKeywords(normalizedText, strongKeywords);
  let confidence = 65;

  if (strongMatches >= 2) {
    confidence = 90;
  } else if (strongMatches === 1) {
    confidence = 75;
  }

  const language = detectCommandLanguage(input);
  if (language === "Mixed" || language === "Banglish") {
    confidence = Math.min(95, confidence + 5);
  }

  return Math.min(100, Math.max(0, confidence));
}

export function classifyCommandRisk(
  intent: CommandIntent,
  normalizedText: string,
): {
  riskLevel: CommandRiskLevel;
  confirmationReason?: string;
} {
  const lowerText = normalizeCommandText(normalizedText);

  if (containsAny(lowerText, riskBlockedKeywords)) {
    return {
      riskLevel: "blocked",
      confirmationReason:
        "This command is blocked because it appears destructive or unsafe.",
    };
  }

  if (intent === "file_organize" || containsAny(lowerText, riskSensitiveKeywords)) {
    return {
      riskLevel: "sensitive",
      confirmationReason:
        "This command may modify or delete local data and requires confirmation.",
    };
  }

  switch (intent) {
    case "email_draft":
    case "message_draft":
      return {
        riskLevel: "confirmation_required",
        confirmationReason:
          "Drafting is allowed, but sending will require confirmation.",
      };
    case "smart_home":
      return {
        riskLevel: "confirmation_required",
        confirmationReason:
          "Smart home actions will require device confirmation.",
      };
    case "open_app":
    case "open_website":
      return {
        riskLevel: "confirmation_required",
        confirmationReason:
          "Opening external apps or websites requires user confirmation in this phase.",
      };
    case "reminder_create":
      return {
        riskLevel: "confirmation_required",
        confirmationReason:
          "Reminder creation will require confirmation before saving.",
      };
    default:
      return {
        riskLevel: getDefaultRiskLevel(intent),
      };
  }
}

function extractEntity(text: string, options: Array<{ key: string; patterns: string[] }>): string | undefined {
  const found = options.find((item) => containsAny(text, item.patterns));
  return found ? found.key : undefined;
}

export function detectCommandIntent(input: string): CommandUnderstandingResult {
  const normalizedText = normalizeCommandText(input);
  const language = detectCommandLanguage(input);
  const text = normalizedText;
  const entities: Record<string, string> = {};

  const isYoutube = containsAny(text, youtubeKeywords);
  const isFileOrganize = containsAny(text, fileOrganizeKeywords);
  const isFileSearch = containsAny(text, fileSearchKeywords);
  const isEmailDraft = containsAny(text, emailDraftKeywords);
  const isMessageDraft = containsAny(text, messageDraftKeywords);
  const isReminderCreate = containsAny(text, reminderCreateKeywords);
  const isSmartHome = containsAny(text, smartHomeKeywords);
  const isStudyMode = containsAny(text, studyModeKeywords);
  const isOpenWebsite = containsAny(text, openWebsiteKeywords);
  const isOpenApp = containsAny(text, openAppKeywords);
  const isWebSearch = containsAny(text, webSearchKeywords);
  const isAssistantQuery = containsAny(text, assistantQueryKeywords);

  let intent: CommandIntent = "unknown";
  let explanation = "No matching command pattern was found.";

  if (containsDangerousCommandPhrase(input)) {
    return {
      originalText: typeof input === "string" ? input : "",
      normalizedText,
      intent: "unknown",
      language,
      confidence: calculateCommandConfidence(normalizedText, "unknown"),
      riskLevel: "blocked",
      confirmationReason: "This command contains blocked or unsafe terms.",
      entities: {},
      explanation: "Matched blocked/dangerous command phrases.",
      canExecute: false,
    };
  }

  const appKey = detectAppKeyFromText(input);
  if (appKey) {
    entities.target = appKey;
    const riskData = classifyCommandRisk("open_app", normalizedText);
    return {
      originalText: typeof input === "string" ? input : "",
      normalizedText,
      intent: "open_app",
      language,
      confidence: 90,
      riskLevel: riskData.riskLevel,
      confirmationReason: riskData.confirmationReason,
      entities,
      explanation: "Matched app opening phrases.",
      canExecute: false,
    };
  }

  const websiteKey = detectWebsiteKeyFromText(input);
  if (websiteKey) {
    entities.target = websiteKey;
    if (websiteKey === "youtube") {
      return {
        originalText: typeof input === "string" ? input : "",
        normalizedText,
        intent: "youtube_search",
        language,
        confidence: 90,
        riskLevel: "safe",
        entities,
        explanation: "Matched website opening phrases.",
        canExecute: false,
      };
    }
    const riskData = classifyCommandRisk("open_website", normalizedText);
    return {
      originalText: typeof input === "string" ? input : "",
      normalizedText,
      intent: "open_website",
      language,
      confidence: 90,
      riskLevel: riskData.riskLevel,
      confirmationReason: riskData.confirmationReason,
      entities,
      explanation: "Matched website opening phrases.",
      canExecute: false,
    };
  }

  const fileHints = detectFileSearchHints(input);
  if (fileHints.isFileSearch) {
    entities.scope = fileHints.scope;
    entities.extensions = fileHints.extensions.join(",");
    return {
      originalText: typeof input === "string" ? input : "",
      normalizedText,
      intent: "file_search",
      language,
      confidence: 85,
      riskLevel: "safe",
      entities,
      explanation: "Matched file search phrases.",
      canExecute: false,
    };
  }

  if (isYoutube) {
    intent = "youtube_search";
    explanation = "Matched YouTube/music related phrases.";
    entities.query = text;
  } else if (isFileOrganize) {
    intent = "file_organize";
    explanation = "Matched local file organization phrases.";
  } else if (isFileSearch) {
    intent = "file_search";
    explanation = "Matched local file search phrases.";
  } else if (isEmailDraft) {
    intent = "email_draft";
    explanation = "Matched email drafting phrases.";
    const target = extractEntity(text, [
      { key: "boss", patterns: ["boss", "sir"] },
      { key: "friend", patterns: ["friend", "বন্ধু"] },
    ]);
    if (target) entities.target = target;
  } else if (isMessageDraft) {
    intent = "message_draft";
    explanation = "Matched message drafting phrases.";
    const target = extractEntity(text, [
      { key: "boss", patterns: ["boss", "sir"] },
      { key: "friend", patterns: ["friend", "বন্ধু"] },
    ]);
    if (target) entities.target = target;
  } else if (isReminderCreate) {
    intent = "reminder_create";
    explanation = "Matched reminder creation phrases.";
    const timeHint = extractEntity(text, [
      { key: "hour", patterns: ["ঘণ্টা", "hour", "hours"] },
      { key: "tomorrow", patterns: ["kalke", "tomorrow", "আগামীকাল"] },
      { key: "alarm", patterns: ["alarm"] },
    ]);
    if (timeHint) entities.timeHint = timeHint;
  } else if (isSmartHome) {
    intent = "smart_home";
    explanation = "Matched smart home control phrases.";
    const device = extractEntity(text, [
      { key: "light", patterns: ["light", "লাইট", "room light"] },
      { key: "fan", patterns: ["fan", "ফ্যান"] },
      { key: "relay", patterns: ["relay", "esp32"] },
    ]);
    if (device) entities.device = device;
  } else if (isStudyMode) {
    intent = "study_mode";
    explanation = "Matched study and learning phrases.";
  } else if (isOpenWebsite) {
    intent = "open_website";
    explanation = "Matched website opening phrases.";
  } else if (isOpenApp) {
    intent = "open_app";
    explanation = "Matched application opening phrases.";
  } else if (isWebSearch) {
    intent = "web_search";
    explanation = "Matched web search phrases.";
  } else if (isAssistantQuery) {
    intent = "general_assistant_query";
    explanation = "Matched general assistant query phrases.";
  }

  const confidence = calculateCommandConfidence(normalizedText, intent);
  const riskData = classifyCommandRisk(intent, normalizedText);

  return {
    originalText: typeof input === "string" ? input : "",
    normalizedText,
    intent,
    language,
    confidence,
    riskLevel: riskData.riskLevel,
    confirmationReason: riskData.confirmationReason,
    entities,
    explanation,
    canExecute: false,
  };
}

export function getDefaultRiskLevel(intent: CommandIntent): CommandRiskLevel {
  switch (intent) {
    case "open_app":
    case "open_website":
    case "email_draft":
    case "message_draft":
    case "reminder_create":
    case "smart_home":
      return "confirmation_required";
    case "file_organize":
      return "sensitive";
    case "youtube_search":
    case "web_search":
    case "file_search":
    case "study_mode":
    case "general_assistant_query":
    case "unknown":
    default:
      return "safe";
  }
}

export function isCommandSensitive(result: CommandUnderstandingResult): boolean {
  return result.riskLevel === "sensitive" || result.riskLevel === "blocked";
}

export function shouldAskConfirmation(result: CommandUnderstandingResult): boolean {
  return result.riskLevel === "confirmation_required" || result.riskLevel === "sensitive";
}

export function createCommandResult(input: string): CommandUnderstandingResult {
  const normalizedText = normalizeCommandText(input);
  const language = detectCommandLanguage(input);

  return {
    originalText: typeof input === "string" ? input : "",
    normalizedText,
    intent: "unknown",
    language,
    confidence: 0,
    riskLevel: getDefaultRiskLevel("unknown"),
    entities: {},
    explanation: "Command intent has not been detected yet.",
    canExecute: false,
  };
}

export function getIntentLabel(intent: CommandIntent): string {
  const found = SUPPORTED_COMMAND_INTENTS.find((item) => item.intent === intent);
  return found ? found.label : "Unknown";
}

/* Example command understanding outcomes:
- "ইউটিউব খুলে গান চালাও" → youtube_search, safe
- "Downloads folder clean koro" → file_organize, sensitive
- "Boss ke email draft koro" → email_draft, confirmation_required
- "delete system32" → unknown or file_organize, blocked
*/

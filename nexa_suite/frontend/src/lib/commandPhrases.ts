export const WEBSITE_PHRASES: Record<string, string[]> = {
  youtube: [
    "youtube", "you tube", "yt", "ইউটিউব", "ইউটিউবে",
    "youtube kholo", "youtube khulo", "youtube open koro",
    "ইউটিউব খোলো", "ইউটিউব খুলুন",
  ],
  google: [
    "google", "গুগল", "google kholo", "google khulo", "গুগল খোলো",
  ],
  github: [
    "github", "git hub", "গিটহাব", "github kholo",
  ],
  facebook: [
    "facebook", "fb", "ফেসবুক", "facebook kholo", "ফেসবুক খোলো",
  ],
  gmail: [
    "gmail", "email", "mail", "জিমেইল", "gmail kholo",
  ],
  chatgpt: [
    "chatgpt", "chat gpt", "চ্যাটজিপিটি", "chatgpt kholo",
  ],
  stackoverflow: [
    "stackoverflow", "stack overflow", "স্ট্যাক ওভারফ্লো",
  ],
};

export const APP_PHRASES: Record<string, string[]> = {
  notepad: [
    "notepad", "note pad", "নোটপ্যাড", "notepad kholo", "notepad khulo",
  ],
  calculator: [
    "calculator", "calc", "ক্যালকুলেটর", "calculator kholo", "calc kholo",
  ],
  chrome: [
    "chrome", "google chrome", "chrome browser", "ক্রোম", "chrome kholo",
  ],
  file_explorer: [
    "file explorer", "explorer", "files", "folder",
    "ফাইল", "ফোল্ডার", "file explorer kholo",
  ],
  vscode: [
    "vscode", "vs code", "visual studio code", "code editor", "vs code kholo",
  ],
};

export const FILE_SEARCH_PHRASES = {
  general: [
    "find", "search", "khuje dao", "khuje ber koro", "khujun",
    "খুঁজে দাও", "খুঁজুন", "বের করো", "ফাইল খুঁজে দাও",
    "folder e", "folder theke", "ফোল্ডারে", "থেকে",
  ],
  scopes: {
    downloads: [
      "downloads", "download", "download folder",
      "ডাউনলোড", "ডাউনলোডস",
    ],
    desktop: [
      "desktop", "desk", "ডেস্কটপ",
    ],
    documents: [
      "documents", "docs", "document",
      "ডকুমেন্ট", "ডকুমেন্টস",
    ],
  } satisfies Record<string, string[]>,
  extensions: {
    pdf: ["pdf", "পিডিএফ"],
    doc: ["doc", "docx", "word", "ওয়ার্ড", "ডক"],
    image: ["image", "photo", "png", "jpg", "jpeg", "ছবি", "ইমেজ"],
    excel: ["excel", "xls", "xlsx", "এক্সেল"],
    ppt: ["ppt", "pptx", "powerpoint", "presentation", "পাওয়ারপয়েন্ট", "প্রেজেন্টেশন"],
  } satisfies Record<string, string[]>,
};

export const DANGEROUS_COMMAND_PHRASES: string[] = [
  "delete", "remove", "wipe", "format", "shutdown", "restart",
  "power off", "system32", "registry", "permanently delete",
  "cmd", "powershell", "regedit",
  "ডিলিট", "মুছে ফেল", "ফরম্যাট", "শাটডাউন", "রিস্টার্ট",
];

export function normalizeCommandPhrase(value: string | null | undefined): string {
  if (value == null) return "";
  return value
    .toLowerCase()
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[.,!?;:"'()\-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function phraseIncludesAny(text: string, phrases: string[]): boolean {
  const normalized = normalizeCommandPhrase(text);
  if (!normalized) return false;
  return phrases.some((phrase) => {
    const normalizedPhrase = normalizeCommandPhrase(phrase);
    return normalizedPhrase.length > 0 && normalized.includes(normalizedPhrase);
  });
}

export function detectWebsiteKeyFromText(text: string): string | null {
  const normalized = normalizeCommandPhrase(text);
  if (!normalized) return null;
  for (const [key, aliases] of Object.entries(WEBSITE_PHRASES)) {
    if (phraseIncludesAny(normalized, aliases)) return key;
  }
  return null;
}

export function detectAppKeyFromText(text: string): string | null {
  const normalized = normalizeCommandPhrase(text);
  if (!normalized) return null;
  for (const [key, aliases] of Object.entries(APP_PHRASES)) {
    if (phraseIncludesAny(normalized, aliases)) return key;
  }
  return null;
}

export function containsDangerousCommandPhrase(text: string): boolean {
  return phraseIncludesAny(text, DANGEROUS_COMMAND_PHRASES);
}

export function detectFileSearchHints(text: string): {
  isFileSearch: boolean;
  scope: "desktop" | "downloads" | "documents" | "all_safe";
  extensions: string[];
} {
  const normalized = normalizeCommandPhrase(text);
  let isFileSearch = false;
  let scope: "desktop" | "downloads" | "documents" | "all_safe" = "all_safe";
  const extensions: string[] = [];

  if (!normalized) return { isFileSearch: false, scope: "all_safe", extensions: [] };

  if (phraseIncludesAny(normalized, FILE_SEARCH_PHRASES.general)) {
    isFileSearch = true;
  }

  if (phraseIncludesAny(normalized, FILE_SEARCH_PHRASES.scopes.downloads)) {
    scope = "downloads";
    isFileSearch = true;
  } else if (phraseIncludesAny(normalized, FILE_SEARCH_PHRASES.scopes.desktop)) {
    scope = "desktop";
    isFileSearch = true;
  } else if (phraseIncludesAny(normalized, FILE_SEARCH_PHRASES.scopes.documents)) {
    scope = "documents";
    isFileSearch = true;
  }

  for (const [extKey, extAliases] of Object.entries(FILE_SEARCH_PHRASES.extensions)) {
    if (phraseIncludesAny(normalized, extAliases)) {
      if (extKey === "pdf") extensions.push("pdf");
      else if (extKey === "doc") extensions.push("doc", "docx");
      else if (extKey === "image") extensions.push("png", "jpg", "jpeg");
      else if (extKey === "excel") extensions.push("xls", "xlsx");
      else if (extKey === "ppt") extensions.push("ppt", "pptx");
      isFileSearch = true;
    }
  }

  return { isFileSearch, scope, extensions };
}

/**
 * The fixed, whitelist-locked launch targets. These mirror the backend
 * whitelists exactly — the frontend can never add targets beyond them,
 * and the backend re-validates every request server-side.
 */

export type SafeTarget = {
  kind: "website" | "app";
  value: string;
  label: string;
  description: string;
  accent: string;
};

export const WEBSITE_TARGETS: SafeTarget[] = [
  { kind: "website", value: "google", label: "Google", description: "Web search", accent: "#22d3ee" },
  { kind: "website", value: "youtube", label: "YouTube", description: "Videos & music", accent: "#ef4444" },
  { kind: "website", value: "whatsapp", label: "WhatsApp Web", description: "Messages draft only", accent: "#22c55e" },
  { kind: "website", value: "github", label: "GitHub", description: "Code hosting", accent: "#a78bfa" },
  { kind: "website", value: "facebook", label: "Facebook", description: "Social", accent: "#3b82f6" },
  { kind: "website", value: "gmail", label: "Gmail", description: "Email inbox", accent: "#f59e0b" },
  { kind: "website", value: "chatgpt", label: "ChatGPT", description: "AI chat", accent: "#4ade80" },
  { kind: "website", value: "stackoverflow", label: "Stack Overflow", description: "Developer Q&A", accent: "#fb923c" },
];

export const APP_TARGETS: SafeTarget[] = [
  { kind: "app", value: "notepad", label: "Notepad", description: "Desktop app", accent: "#60a5fa" },
  { kind: "app", value: "calculator", label: "Calculator", description: "Desktop app", accent: "#4ade80" },
  { kind: "app", value: "chrome", label: "Google Chrome", description: "Browser", accent: "#22d3ee" },
  { kind: "app", value: "file_explorer", label: "File Explorer", description: "Desktop app", accent: "#fbbf24" },
  { kind: "app", value: "vscode", label: "VS Code", description: "Code editor", accent: "#818cf8" },
];

export const ALL_TARGETS: SafeTarget[] = [...APP_TARGETS, ...WEBSITE_TARGETS];

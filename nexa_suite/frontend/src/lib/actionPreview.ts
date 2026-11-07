import type {
  CommandUnderstandingResult,
  CommandIntent,
  CommandRiskLevel,
} from "./commandUnderstanding";

export type ActionPreviewStatus =
  | "preview_only"
  | "requires_confirmation"
  | "sensitive_warning"
  | "blocked";

export type ActionPreview = {
  id: string;
  title: string;
  description: string;
  intent: CommandIntent;
  riskLevel: CommandRiskLevel;
  status: ActionPreviewStatus;
  primaryActionLabel: string;
  secondaryActionLabel: string;
  warningMessage?: string;
  blockedReason?: string;
  previewSteps: string[];
  canExecute: false;
};

const statusMap: Record<CommandRiskLevel, ActionPreviewStatus> = {
  safe: "preview_only",
  confirmation_required: "requires_confirmation",
  sensitive: "sensitive_warning",
  blocked: "blocked",
};

const titleMap: Record<CommandIntent, string> = {
  youtube_search: "YouTube Search Preview",
  open_app: "App Launch Preview",
  open_website: "Website Open Preview",
  web_search: "Web Search Preview",
  file_search: "File Search Preview",
  file_organize: "File Organization Warning",
  email_draft: "Email Draft Preview",
  message_draft: "Message Draft Preview",
  reminder_create: "Reminder Preview",
  study_mode: "Study Mode Preview",
  smart_home: "Smart Home Preview",
  general_assistant_query: "Assistant Query Preview",
  unknown: "Unknown Command",
};

const descriptionMap: Record<CommandIntent, string> = {
  youtube_search:
    "Nexa AI understood this as a YouTube or media search request.",
  open_app:
    "Nexa AI understood this as an app launch request.",
  open_website:
    "Nexa AI understood this as a website opening request.",
  web_search:
    "Nexa AI understood this as a web/news/weather/search request.",
  file_search:
    "Nexa AI understood this as a local file search request.",
  file_organize:
    "Nexa AI understood this as a local file organization request.",
  email_draft:
    "Nexa AI understood this as an email drafting request.",
  message_draft:
    "Nexa AI understood this as a message drafting request.",
  reminder_create:
    "Nexa AI understood this as a reminder creation request.",
  study_mode:
    "Nexa AI understood this as a study or explanation request.",
  smart_home:
    "Nexa AI understood this as a smart home/device control request.",
  general_assistant_query:
    "Nexa AI understood this as a general assistant question.",
  unknown:
    "Nexa AI could not confidently understand this command.",
};

const primaryActionLabelMap: Record<ActionPreviewStatus, string> = {
  preview_only: "Preview Only",
  requires_confirmation: "Confirmation Required Later",
  sensitive_warning: "Sensitive Preview Only",
  blocked: "Blocked",
};

const secondaryActionLabelMap: Record<ActionPreviewStatus, string> = {
  preview_only: "Edit Command",
  requires_confirmation: "Cancel",
  sensitive_warning: "Cancel",
  blocked: "Rewrite Command",
};

const defaultPreviewSteps = [
  "Analyze command intent.",
  "Show safe preview.",
  "Wait for user confirmation in a future phase.",
  "Do not execute anything in this phase.",
];

function getPreviewSteps(intent: CommandIntent): string[] {
  if (intent === "youtube_search") {
    return [
      "Review requested media/search query.",
      "Confirm before opening YouTube in a later phase.",
      "No website will be opened in this phase.",
    ];
  }

  return defaultPreviewSteps;
}

export function createActionPreview(
  result: CommandUnderstandingResult,
): ActionPreview {
  const status = statusMap[result.riskLevel] ?? "preview_only";
  const warningMessage =
    status === "requires_confirmation"
      ? result.confirmationReason ??
        "This action will require confirmation before execution."
      : status === "sensitive_warning"
      ? "This action may affect files, devices, messages, or external apps and must be confirmed before execution."
      : undefined;
  const blockedReason =
    status === "blocked"
      ? result.confirmationReason ??
        "This command appears unsafe and is blocked."
      : undefined;

  return {
    id: `preview-${result.intent}-${Date.now()}`,
    title: titleMap[result.intent] ?? titleMap.unknown,
    description: descriptionMap[result.intent] ?? descriptionMap.unknown,
    intent: result.intent,
    riskLevel: result.riskLevel,
    status,
    primaryActionLabel: primaryActionLabelMap[status],
    secondaryActionLabel: secondaryActionLabelMap[status],
    warningMessage,
    blockedReason,
    previewSteps: getPreviewSteps(result.intent),
    canExecute: false,
  };
}

export function getActionPreviewStatusLabel(
  status: ActionPreviewStatus,
): string {
  switch (status) {
    case "preview_only":
      return "Preview Only";
    case "requires_confirmation":
      return "Requires Confirmation";
    case "sensitive_warning":
      return "Sensitive Warning";
    case "blocked":
      return "Blocked";
    default:
      return "Preview";
  }
}

export function isActionBlocked(preview: ActionPreview): boolean {
  return preview.status === "blocked";
}

export function isActionConfirmationRequired(
  preview: ActionPreview,
): boolean {
  return (
    preview.status === "requires_confirmation" ||
    preview.status === "sensitive_warning"
  );
}

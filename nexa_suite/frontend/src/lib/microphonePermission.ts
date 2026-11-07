export type MicrophonePermissionStatus =
  | "unsupported"
  | "unknown"
  | "not_requested"
  | "prompt"
  | "granted"
  | "denied"
  | "error";

export const MIC_PERMISSION_STORAGE_KEY = "nexa-ai:microphone-permission";

export type MicrophonePermissionRecord = {
  status: MicrophonePermissionStatus;
  label: string;
  lastCheckedAt: string;
  lastRequestedAt?: string;
  error?: string;
};

export function isMicrophoneSupported(): boolean {
  return typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices !== "undefined" &&
    typeof navigator.mediaDevices.getUserMedia === "function";
}

export async function checkMicrophonePermission(): Promise<MicrophonePermissionStatus> {
  if (!isMicrophoneSupported()) {
    return "unsupported";
  }

  if (typeof navigator.permissions === "undefined") {
    return "unknown";
  }

  try {
    const status = await navigator.permissions.query({ name: "microphone" as PermissionName });
    switch (status.state) {
      case "granted":
        return "granted";
      case "denied":
        return "denied";
      case "prompt":
        return "prompt";
      default:
        return "unknown";
    }
  } catch {
    return "unknown";
  }
}

export async function requestMicrophoneAccess(): Promise<{ status: MicrophonePermissionStatus; error?: string }> {
  if (!isMicrophoneSupported()) {
    return { status: "unsupported" };
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    try {
      stream.getTracks().forEach((track) => track.stop());
    } catch {
      // Ignore cleanup errors.
    }
    return { status: "granted" };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.toLowerCase().includes("denied") || message.toLowerCase().includes("permission")) {
      return { status: "denied" };
    }
    return { status: "error", error: message };
  }
}

export function getMicrophoneStatusLabel(status: MicrophonePermissionStatus): string {
  switch (status) {
    case "unsupported":
      return "Microphone unsupported";
    case "unknown":
      return "Permission unknown";
    case "not_requested":
      return "Not requested";
    case "prompt":
      return "Permission needed";
    case "granted":
      return "Microphone allowed";
    case "denied":
      return "Microphone blocked";
    case "error":
      return "Permission error";
  }
}

export function getDefaultMicrophonePermissionRecord(): MicrophonePermissionRecord {
  return {
    status: "unknown",
    label: "Permission unknown",
    lastCheckedAt: new Date().toISOString(),
  };
}

export function loadMicrophonePermissionRecord(): MicrophonePermissionRecord {
  try {
    if (typeof window === "undefined" || !window.localStorage) {
      return getDefaultMicrophonePermissionRecord();
    }

    const stored = window.localStorage.getItem(MIC_PERMISSION_STORAGE_KEY);
    if (!stored) {
      return getDefaultMicrophonePermissionRecord();
    }

    const parsed = JSON.parse(stored) as MicrophonePermissionRecord;
    if (parsed && parsed.status && parsed.label && parsed.lastCheckedAt) {
      return parsed;
    }

    return getDefaultMicrophonePermissionRecord();
  } catch {
    return getDefaultMicrophonePermissionRecord();
  }
}

export function saveMicrophonePermissionRecord(
  record: Partial<MicrophonePermissionRecord>
): MicrophonePermissionRecord {
  const existing = loadMicrophonePermissionRecord();

  const updated: MicrophonePermissionRecord = {
    ...existing,
    ...record,
    label: record.status ? getMicrophoneStatusLabel(record.status) : existing.label,
    lastCheckedAt: record.lastCheckedAt
      ? record.lastCheckedAt
      : record.status
      ? new Date().toISOString()
      : existing.lastCheckedAt,
  };

  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(MIC_PERMISSION_STORAGE_KEY, JSON.stringify(updated));
    }
  } catch {
    // If localStorage is unavailable, preserve the merged record in memory.
  }

  return updated;
}

export function clearMicrophonePermissionRecord(): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(MIC_PERMISSION_STORAGE_KEY);
    }
  } catch {
    // Ignore error if localStorage is unavailable.
  }
}


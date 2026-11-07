export type AddressingPreference = "Boss" | "Sir" | "Vai" | "Neutral";
export type LanguageMode = "Bangla" | "English" | "Mixed";
export type VoicePreference = "Male voice" | "Female voice" | "System default";

export type UserProfile = {
  userName: string;
  addressingPreference: AddressingPreference;
  languageMode: LanguageMode;
  voicePreference: VoicePreference;
  hasCompletedOnboarding: boolean;
  createdAt: string;
  updatedAt: string;
};

export const PROFILE_STORAGE_KEY = "nexa-ai-mark-plus:user-profile";

function safeGetLocalStorage(): Storage | null {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage;
    }
  } catch {
    // localStorage unavailable
  }
  return null;
}

export function getDefaultProfile(): UserProfile {
  const timestamp = new Date().toISOString();
  return {
    userName: "",
    addressingPreference: "Boss",
    languageMode: "Bangla",
    voicePreference: "System default",
    hasCompletedOnboarding: false,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

export function loadProfile(): UserProfile {
  const storage = safeGetLocalStorage();
  if (!storage) {
    return getDefaultProfile();
  }

  try {
    const raw = storage.getItem(PROFILE_STORAGE_KEY);
    if (!raw) {
      return getDefaultProfile();
    }

    const parsed = JSON.parse(raw) as (Partial<UserProfile> & Record<string, unknown>) | null;
    if (!parsed || typeof parsed !== "object") {
      return getDefaultProfile();
    }
    const rawAddressing = parsed["addressingPreference"];
    const legacyAddressing: string | undefined = typeof rawAddressing === "string" ? rawAddressing : undefined;
    const addressingPreference: AddressingPreference =
      legacyAddressing === "Madam" || legacyAddressing === "Name only"
        ? "Neutral"
        : legacyAddressing === "Sir" || legacyAddressing === "Vai" || legacyAddressing === "Boss"
        ? legacyAddressing
        : getDefaultProfile().addressingPreference;

    return {
      ...getDefaultProfile(),
      ...parsed,
      addressingPreference,
      createdAt: typeof parsed.createdAt === "string" ? parsed.createdAt : getDefaultProfile().createdAt,
      updatedAt: typeof parsed.updatedAt === "string" ? parsed.updatedAt : getDefaultProfile().updatedAt,
    };
  } catch {
    return getDefaultProfile();
  }
}

export function saveProfile(profile: Partial<UserProfile>): UserProfile {
  const existing = loadProfile();
  const merged: UserProfile = {
    ...existing,
    ...profile,
    createdAt: existing.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const storage = safeGetLocalStorage();
  if (storage) {
    try {
      storage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(merged));
    } catch {
      // ignore storage failures
    }
  }

  return merged;
}

export function clearProfile(): void {
  const storage = safeGetLocalStorage();
  if (!storage) {
    return;
  }

  try {
    storage.removeItem(PROFILE_STORAGE_KEY);
  } catch {
    // ignore removal failures
  }
}

export function isOnboardingComplete(): boolean {
  const profile = loadProfile();
  return profile.hasCompletedOnboarding;
}

export function formatAddressingName(profile: Pick<UserProfile, "userName" | "addressingPreference">): string {
  const rawName = profile.userName?.trim() ?? "";
  const name = rawName || "Your Name";

  if (!rawName) {
    return "Your Name";
  }

  if (profile.addressingPreference === "Neutral") {
    return name;
  }

  return `${profile.addressingPreference} ${name}`;
}

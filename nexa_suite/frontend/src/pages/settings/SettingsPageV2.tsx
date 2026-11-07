import { EngineSettings } from "@/lib/engineRuntime";
import { useEffect, useState } from "react";
import {
  Bell,
  Database,
  Languages,
  RotateCcw,
  Settings as SettingsIcon,
  Shield,
  ShieldCheck,
  Trash2,
  User,
  Volume2,
} from "lucide-react";
import {
  loadProfile,
  saveProfile,
  formatAddressingName,
  clearCommandHistory,
  UserProfile,
  AddressingPreference,
  LanguageMode,
} from "@/lib";
import { PageHero } from "@/components/ui";
import { AiModelsSettings } from "@/components/settings/AiModelsSettings";
import { VoiceSettings } from "@/components/settings/VoiceSettings";
import { voiceManager } from "@/lib/voice";
import { BackgroundSettings } from "@/components/settings/BackgroundSettings";
import { EdgeTtsSettings } from "@/components/settings/EdgeTtsSettings";
import { CartesiaSettings } from "@/components/settings/CartesiaSettings";
import { RuntimeReadinessSettings } from "@/components/settings/RuntimeReadinessSettings";
import {
  getBackendPermissions,
  getBackendContacts,
  getBackendTtsStatus,
  ContactItemDto,
  PermissionItemDto,
  saveBackendContact,
  deleteBackendContact,
  requestTtsSpeak,
  updateBackendPermission,
  TtsStatusResponseDto,
} from "@/lib/backendAssistantClient";

type LocalPrefs = {
  saveHistory: boolean;
  dueReminderAlerts: boolean;
  whatsappDraftOpenTarget: "auto" | "app" | "web" | "wa_me";
};

const PREFS_KEY = "nexa.localPrefs";

function loadPrefs(): LocalPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) {
      return {
        saveHistory: true,
        dueReminderAlerts: true,
        whatsappDraftOpenTarget: "auto",
        ...JSON.parse(raw),
      };
    }
  } catch {
    // fall through to defaults
  }
  return { saveHistory: true, dueReminderAlerts: true, whatsappDraftOpenTarget: "auto" };
}

export function SettingsPageV2({
  onResetSetup,
}: {
  onResetSetup: () => void;
}) {
  const [profile, setProfile] = useState<UserProfile>(() => loadProfile());
  const [prefs, setPrefs] = useState<LocalPrefs>(() => loadPrefs());
  const [permissions, setPermissions] = useState<PermissionItemDto[]>([]);
  const [contacts, setContacts] = useState<ContactItemDto[]>([]);
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactNickname, setContactNickname] = useState("");
  const [contactAliases, setContactAliases] = useState("");
  const [contactRelationship, setContactRelationship] = useState("unknown");
  const [contactTone, setContactTone] = useState("normal");
  const [tts, setTts] = useState<TtsStatusResponseDto | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [changeLog, setChangeLog] = useState<Array<{ text: string; at: string }>>([]);
  const [confirmClearHistory, setConfirmClearHistory] = useState(false);

  const refreshBackend = async () => {
    try {
      const [perms, ttsStatus] = await Promise.all([
        getBackendPermissions(),
        getBackendTtsStatus(),
      ]);
      setPermissions(perms.permissions);
      setTts(ttsStatus);
      try {
        const contactResponse = await getBackendContacts();
        setContacts(contactResponse.contacts);
      } catch {
        setContacts([]);
      }
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? `${err.message}. Start the backend to manage permissions.`
          : "Backend settings unavailable.",
      );
    }
  };

  useEffect(() => {
    void refreshBackend();
  }, []);

  const logChange = (text: string) => {
    setChangeLog((prev) => [{ text, at: new Date().toISOString() }, ...prev].slice(0, 6));
  };

  const savePrefs = (next: LocalPrefs) => {
    setPrefs(next);
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify(next));
    } catch {
      // non-fatal
    }
  };

  const updateProfileField = (patch: Partial<UserProfile>, label: string) => {
    const updated = saveProfile(patch);
    if (patch.languageMode === "Bangla") voiceManager.updateSettings({ language: "bn-BD" });
    if (patch.languageMode === "English") voiceManager.updateSettings({ language: "en-US" });
    setProfile(updated);
    logChange(label);
  };

  const togglePermission = async (key: string, label: string) => {
    const current = permissions.find((p) => p.key === key);
    if (!current) return;
    setBusyKey(key);
    try {
      const result = await updateBackendPermission(key, !current.enabled);
      if (!result.updated) setErrorMessage(result.message);
      else logChange(`${label} ${!current.enabled ? "enabled" : "disabled"}`);
      await refreshBackend();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Permission update failed.");
    } finally {
      setBusyKey(null);
    }
  };

  const permissionEnabled = (key: string) =>
    permissions.find((p) => p.key === key)?.enabled ?? false;

  const handleTestVoice = async () => {
    setStatusMessage(null);
    try {
      const result = await requestTtsSpeak(
        `Hello ${formatAddressingName(profile)}, I am Nexa, your desktop assistant.`,
      );
      setStatusMessage(result.spoken ? "Test voice spoken." : (result.error || result.message));
    } catch (err) {
      setStatusMessage(err instanceof Error ? err.message : "Voice test failed.");
    }
  };

  const handleSaveContact = async () => {
    setStatusMessage(null);
    setErrorMessage(null);
    try {
      const result = await saveBackendContact({
        name: contactName.trim(),
        phone_number: contactPhone.trim(),
        email_address: contactEmail.trim() || null,
        nickname: contactNickname.trim() || null,
        aliases: contactAliases.split(",").map((item) => item.trim()).filter(Boolean),
        relationship: contactRelationship,
        default_tone: contactTone,
      });
      if (!result.ok) {
        setErrorMessage(result.error || result.message);
        return;
      }
      setContactName("");
      setContactPhone("");
      setContactEmail("");
      setContactNickname("");
      setContactAliases("");
      setContactRelationship("unknown");
      setContactTone("normal");
      logChange(`WhatsApp contact saved: ${result.contact?.name ?? "contact"}`);
      setStatusMessage(result.message);
      await refreshBackend();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Contact save failed.");
    }
  };

  const handleDeleteContact = async (name: string) => {
    setStatusMessage(null);
    setErrorMessage(null);
    try {
      const result = await deleteBackendContact(name);
      if (!result.ok) {
        setErrorMessage(result.error || result.message);
        return;
      }
      logChange(`WhatsApp contact deleted: ${name}`);
      setStatusMessage(result.message);
      await refreshBackend();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Contact delete failed.");
    }
  };

  const handleExportSettings = () => {
    const payload = {
      exported_at: new Date().toISOString(),
      profile,
      localPrefs: prefs,
      backendPermissions: permissions.map((p) => ({ key: p.key, enabled: p.enabled })),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "nexa-ai-settings.json";
    link.click();
    URL.revokeObjectURL(url);
    logChange("Settings exported to file");
    setStatusMessage("Settings exported as nexa-ai-settings.json");
  };

  const handleClearHistory = () => {
    clearCommandHistory();
    try {
      localStorage.removeItem("nexa.recentSearches");
    } catch {
      // non-fatal
    }
    setConfirmClearHistory(false);
    logChange("Local history cleared");
    setStatusMessage("Local command history and recent searches cleared.");
  };

  const Switch = ({
    on,
    locked,
    onClick,
  }: {
    on: boolean;
    locked?: boolean;
    onClick?: () => void;
  }) => (
    <button
      type="button"
      className={`nx-switch${on ? " on" : ""}${locked ? " locked" : ""}`}
      onClick={locked ? undefined : onClick}
      aria-pressed={on}
      title={locked ? "Locked by safety policy" : undefined}
    />
  );

  return (
    <>
      <div className="nx-page">
        <PageHero
          icon={<SettingsIcon />}
          eyebrow="Preferences"
          title="Settings"
          description="Manage your preferences, assistant behavior, privacy, and system controls."
        />

        <EngineSettings />
        {errorMessage && <div className="nx-result-err">{errorMessage}</div>}
        {statusMessage && <div className="nx-result-ok">{statusMessage}</div>}

        <div className="nx-settings-grid">
          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><User /> 1. Profile & Personalization</div>
            </div>
            <div className="nx-chip-row" style={{ marginBottom: 10 }}>
              <div className="nx-chip muted">Local-only profile settings</div>
            </div>
            <div className="nx-field-row">
              <span>Your name</span>
              <input
                className="nx-input"
                value={profile.userName}
                placeholder="Local User"
                onChange={(event) => {
                  const updated = saveProfile({ userName: event.target.value });
                  setProfile(updated);
                }}
                onBlur={() => logChange("Name updated")}
              />
            </div>
            <div className="nx-field-row"><span>Assistant Address Style</span></div>
            <div className="nx-seg">
              {(["Boss", "Sir", "Vai", "Neutral"] as AddressingPreference[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  className={profile.addressingPreference === option ? "active" : ""}
                  onClick={() => updateProfileField({ addressingPreference: option }, `Addressing set to ${option}`)}
                >
                  {option}
                </button>
              ))}
            </div>
            <div className="nx-field-row" style={{ marginTop: 8 }}><span>Preferred language</span></div>
            <div className="nx-seg">
              {(["Bangla", "English", "Mixed"] as LanguageMode[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  className={profile.languageMode === option ? "active" : ""}
                  onClick={() => updateProfileField({ languageMode: option }, `Language set to ${option}`)}
                >
                  {option === "Bangla" ? "বাংলা" : option}
                </button>
              ))}
            </div>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Volume2 /> 2. Voice & Audio</div>
            </div>
            <div className="nx-switch-row">
              <span>
                Voice replies (TTS)
                <small>Speak through Cartesia Sonic, with Edge neural fallback</small>
              </span>
              <Switch
                on={permissionEnabled("voice_tts")}
                onClick={() => void togglePermission("voice_tts", "Voice replies")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Online Bangla transcription
                <small>Online Bangla STT through Nexa. Always-listening can be disabled separately.</small>
              </span>
              <Switch
                on={permissionEnabled("voice_stt")}
                onClick={() => void togglePermission("voice_stt", "Voice transcription")}
              />
            </div>
            <div className="nx-row">
              <span>Online neural voices</span>
              <strong>{tts ? tts.voices.length : "—"}</strong>
            </div>
            <button
              type="button"
              className="nx-btn ghost"
              style={{ width: "100%", marginTop: 10 }}
              onClick={handleTestVoice}
              disabled={busyKey !== null || !permissionEnabled("voice_tts")}
            >
              ▶ Test Voice
            </button>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><ShieldCheck /> 3. AI Behavior & Command Safety</div>
            </div>
            <div className="nx-field-row"><span>Confirmation level</span></div>
            <div className="nx-seg">
              <button type="button" className="active">Always Ask</button>
              <button type="button" disabled title="Locked by safety policy">Smart Confirm</button>
              <button type="button" disabled title="Locked by safety policy">Auto Execute</button>
            </div>
            <div className="nx-switch-row">
              <span>
                Block dangerous commands
                <small>delete / format / shutdown / system32 / registry + Bangla equivalents</small>
              </span>
              <Switch on locked />
            </div>
            <div className="nx-switch-row">
              <span>
                Whitelist-only real actions
                <small>Unknown apps and websites can never open</small>
              </span>
              <Switch on locked />
            </div>
            <div className="nx-switch-row">
              <span>
                Trusted Quick Launch Mode
                <small>Open recognized safe installed apps without asking every time. Dangerous/system commands remain blocked.</small>
              </span>
              <Switch
                on={permissionEnabled("trusted_quick_launch")}
                onClick={() => void togglePermission("trusted_quick_launch", "Trusted Quick Launch Mode")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                YouTube Skill Enabled
                <small>Open YouTube and safe YouTube search URLs after confirmation</small>
              </span>
              <Switch
                on={permissionEnabled("youtube_skill")}
                onClick={() => void togglePermission("youtube_skill", "YouTube Skill")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Trusted YouTube Auto Open
                <small>Open whitelisted YouTube home/search URLs without a confirmation card</small>
              </span>
              <Switch
                on={permissionEnabled("trusted_youtube_auto_open")}
                onClick={() => void togglePermission("trusted_youtube_auto_open", "Trusted YouTube Auto Open")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                WhatsApp Draft Skill Enabled
                <small>Create message drafts after confirmation. Auto-send remains locked off.</small>
              </span>
              <Switch
                on={permissionEnabled("whatsapp_draft_skill")}
                onClick={() => void togglePermission("whatsapp_draft_skill", "WhatsApp Draft Skill")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Trusted WhatsApp Draft Auto Open
                <small>Open WhatsApp Web/draft URLs without confirmation. Nexa never clicks Send.</small>
              </span>
              <Switch
                on={permissionEnabled("trusted_whatsapp_draft_auto_open")}
                onClick={() => void togglePermission("trusted_whatsapp_draft_auto_open", "Trusted WhatsApp Draft Auto Open")}
              />
            </div>
            <label className="nx-field">
              <span>WhatsApp Draft Open Target</span>
              <select
                value={prefs.whatsappDraftOpenTarget}
                onChange={(event) => {
                  const value = event.target.value as LocalPrefs["whatsappDraftOpenTarget"];
                  savePrefs({ ...prefs, whatsappDraftOpenTarget: value });
                  logChange(`WhatsApp Draft Open Target set to ${event.target.options[event.target.selectedIndex].text}`);
                }}
              >
                <option value="auto">Auto</option>
                <option value="app">WhatsApp App</option>
                <option value="web">WhatsApp Web</option>
                <option value="wa_me">wa.me fallback</option>
              </select>
              <small>Auto tries the WhatsApp app protocol first, then safe web fallbacks. Nexa never presses Send.</small>
            </label>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Shield /> 4. Privacy & Security</div>
            </div>
            <div className="nx-switch-row">
              <span>
                Store data locally (no cloud sync)
                <small>All data stays on this machine</small>
              </span>
              <Switch on locked />
            </div>
            <div className="nx-switch-row">
              <span>
                Web answers
                <small>DuckDuckGo / Wikipedia instant answers</small>
              </span>
              <Switch
                on={permissionEnabled("web_answers")}
                onClick={() => void togglePermission("web_answers", "Web answers")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Read-only file search
                <small>Desktop, Downloads, Documents — metadata only</small>
              </span>
              <Switch
                on={permissionEnabled("file_search")}
                onClick={() => void togglePermission("file_search", "File search")}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Document preview
                <small>Read-only PDF/TXT/MD text preview</small>
              </span>
              <Switch
                on={permissionEnabled("documents")}
                onClick={() => void togglePermission("documents", "Document preview")}
              />
            </div>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Bell /> 5. Notifications</div>
            </div>
            <div className="nx-switch-row">
              <span>
                Due reminder alerts
                <small>Show a badge when reminders are due</small>
              </span>
              <Switch
                on={prefs.dueReminderAlerts}
                onClick={() => {
                  savePrefs({ ...prefs, dueReminderAlerts: !prefs.dueReminderAlerts });
                  logChange(`Reminder alerts ${!prefs.dueReminderAlerts ? "enabled" : "disabled"}`);
                }}
              />
            </div>
            <div className="nx-switch-row">
              <span>
                Save command history
                <small>Keep local preview history on this device</small>
              </span>
              <Switch
                on={prefs.saveHistory}
                onClick={() => {
                  savePrefs({ ...prefs, saveHistory: !prefs.saveHistory });
                  logChange(`History saving ${!prefs.saveHistory ? "enabled" : "disabled"}`);
                }}
              />
            </div>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><User /> 6. Local WhatsApp Contacts & Email</div>
            </div>
            <div className="nx-chip-row" style={{ marginBottom: 10 }}>
              <div className="nx-chip muted">Local-only</div>
              <div className="nx-chip muted">WhatsApp drafts</div>
              <div className="nx-chip warn">Email requires confirmation</div>
            </div>
            <div className="nx-field-row">
              <span>Name</span>
              <input
                className="nx-input"
                value={contactName}
                placeholder="Rahim"
                onChange={(event) => setContactName(event.target.value)}
              />
            </div>
            <div className="nx-field-row">
              <span>Phone number</span>
              <input
                className="nx-input"
                value={contactPhone}
                placeholder="017xxxxxxxx"
                onChange={(event) => setContactPhone(event.target.value)}
              />
            </div>
            <div className="nx-field-row">
              <span>Nickname</span>
              <input
                className="nx-input"
                value={contactNickname}
                placeholder="Optional"
                onChange={(event) => setContactNickname(event.target.value)}
              />
            </div>
            <div className="nx-field-row">
              <span>Email address</span>
              <input
                className="nx-input"
                type="email"
                value={contactEmail}
                placeholder="boss@company.com"
                onChange={(event) => setContactEmail(event.target.value)}
              />
            </div>
            <div className="nx-field-row">
              <span>Aliases</span>
              <input
                className="nx-input"
                value={contactAliases}
                placeholder="Rohim, office boss"
                onChange={(event) => setContactAliases(event.target.value)}
              />
            </div>
            <div className="nx-field-row">
              <span>Relationship</span>
              <select
                className="nx-input"
                value={contactRelationship}
                onChange={(event) => setContactRelationship(event.target.value)}
              >
                <option value="unknown">Unknown</option>
                <option value="boss">Boss</option>
                <option value="client">Client</option>
                <option value="friend">Friend</option>
                <option value="family">Family</option>
              </select>
            </div>
            <div className="nx-field-row">
              <span>Default tone</span>
              <select
                className="nx-input"
                value={contactTone}
                onChange={(event) => setContactTone(event.target.value)}
              >
                <option value="normal">Normal</option>
                <option value="formal">Formal</option>
                <option value="friendly">Friendly</option>
              </select>
            </div>
            <button
              type="button"
              className="nx-btn"
              style={{ width: "100%", marginTop: 8 }}
              onClick={() => void handleSaveContact()}
              disabled={!contactName.trim() || !contactPhone.trim()}
            >
              Save Local WhatsApp Contact
            </button>
            <div className="nx-list" style={{ marginTop: 12 }}>
              {contacts.length === 0 ? (
                <div className="nx-empty">No local WhatsApp contacts saved yet.</div>
              ) : (
                contacts.map((contact) => (
                  <div className="nx-list-row" key={contact.name}>
                    <div className="nx-list-main">
                      <strong>{contact.name}</strong>
                      <small>
                        {contact.phone_number}
                        {contact.email_address ? ` / ${contact.email_address}` : ""}
                        {contact.nickname ? ` / ${contact.nickname}` : ""}
                        {contact.aliases?.length ? ` / aliases: ${contact.aliases.join(", ")}` : ""}
                        {` / ${contact.relationship} / ${contact.default_tone}`}
                      </small>
                    </div>
                    <button
                      type="button"
                      className="nx-link-btn"
                      onClick={() => void handleDeleteContact(contact.name)}
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="nx-card">
            <div className="nx-card-head">
              <div className="nx-card-title"><Database /> 7. Backup & Reset</div>
            </div>
            <div className="nx-confirm-actions" style={{ marginBottom: 10 }}>
              <button type="button" className="nx-btn ghost" onClick={handleExportSettings}>
                Export Settings
              </button>
              <button type="button" className="nx-btn amber" onClick={onResetSetup}>
                <RotateCcw size={13} style={{ marginRight: 6, verticalAlign: "-2px" }} />
                Reset Onboarding
              </button>
            </div>
            {!confirmClearHistory ? (
              <button
                type="button"
                className="nx-btn danger"
                onClick={() => setConfirmClearHistory(true)}
              >
                <Trash2 size={13} style={{ marginRight: 6, verticalAlign: "-2px" }} />
                Clear Local History
              </button>
            ) : (
              <div className="nx-confirm" style={{ marginTop: 0 }}>
                <h5>Clear local history?</h5>
                <p>This removes locally saved command history and recent searches. No files are touched.</p>
                <div className="nx-confirm-actions">
                  <button type="button" className="nx-btn danger" onClick={handleClearHistory}>
                    Yes, Clear History
                  </button>
                  <button type="button" className="nx-btn ghost" onClick={() => setConfirmClearHistory(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </section>

          <AiModelsSettings />

          <VoiceSettings />

          <CartesiaSettings />
          <EdgeTtsSettings />

          <RuntimeReadinessSettings />

          <BackgroundSettings />
        </div>
      </div>

      <aside className="nx-rail">
        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><User /> Profile Summary</div>
          </div>
          <div className="nx-row"><span>Name</span><strong>{profile.userName || "Local User"}</strong></div>
          <div className="nx-row"><span>Addressing</span><strong>{formatAddressingName(profile)}</strong></div>
          <div className="nx-row"><span>Language</span><strong>{profile.languageMode}</strong></div>
          <div className="nx-row"><span>Privacy mode</span><strong className="nx-status-ok">Local First</strong></div>
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><ShieldCheck /> Quick Toggles</div>
          </div>
          {["actions_website", "actions_app", "trusted_quick_launch", "youtube_skill", "trusted_youtube_auto_open", "whatsapp_draft_skill", "trusted_whatsapp_draft_auto_open", "always_on_microphone", "voice_stt", "voice_tts", "web_answers", "reminders"].map((key) => {
            const permission = permissions.find((p) => p.key === key);
            if (!permission) return null;
            return (
              <div className="nx-switch-row" key={key}>
                <span>{permission.label}</span>
                <Switch
                  on={permission.enabled}
                  onClick={() => void togglePermission(key, permission.label)}
                />
              </div>
            );
          })}
          {permissions.length === 0 && (
            <div className="nx-empty">Backend offline — toggles unavailable.</div>
          )}
        </section>

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><RotateCcw /> Recent Setting Changes</div>
          </div>
          {changeLog.length === 0 ? (
            <div className="nx-empty">No changes this session.</div>
          ) : (
            <div className="nx-list">
              {changeLog.map((entry) => (
                <div className="nx-list-row" key={entry.at + entry.text}>
                  <div className="nx-list-main">
                    <strong>{entry.text}</strong>
                    <small>{new Date(entry.at).toLocaleTimeString()}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </aside>
    </>
  );
}

import { useEngine, EngineParticles } from "@/lib/engineRuntime";
﻿import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Mic, Clock, Terminal } from "lucide-react";
import { PageHero } from "@/components/ui";
import { SplashScreen, useStartupSequence } from "@/components/splash";
import { AIGlobeBackground } from "@/background";
import { WelcomeOnboarding } from "@/components/onboarding";
import { useVoiceSession, VoiceCommandDraft, VoiceModeSelector, VoiceStatusPanel, VoiceTranscriptPanel } from "@/components/voice";
import { ActionPreviewCard } from "@/components/action-preview";
import { ActionConfirmationCard } from "@/components/action-confirmation";
import { PushToTalkPanel } from "@/components/voice/PushToTalkPanel";
import { AuditEventsPanel } from "@/components/history/AuditEventsPanel";
import { TtsSettingsCard } from "@/components/settings/TtsSettingsCard";
import { WebAnswersPage } from "@/pages/web/WebAnswersPage";
import { ChatPage } from "@/pages/chat/ChatPage";
import { RemindersPage } from "@/pages/automation/RemindersPage";
import { SecurityCenterPage } from "@/pages/security/SecurityCenterPage";
import { FilesPage } from "@/pages/files/FilesPage";
import { Sidebar, NavId } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { CommandCenterPage } from "@/pages/dashboard/CommandCenterPage";
import { LauncherHubPage } from "@/pages/launcher/LauncherHubPage";
import { SettingsPageV2 } from "@/pages/settings/SettingsPageV2";
import { AutomationsPage } from "@/pages/automation/AutomationsPage";
import { VoicePage } from "@/pages/voice/VoicePage";
import { CommandsPage } from "@/pages/commands/CommandsPage";
import { HistoryPage } from "@/pages/history/HistoryPage";
import { SkillsHubPage } from "@/pages/skills/SkillsHubPage";
import { getBackendReminders } from "@/lib/backendAssistantClient";
import { clearProfile, checkMicrophonePermission, clearMicrophonePermissionRecord, formatAddressingName, getMicrophoneStatusLabel, getIntentLabel, isCommandSensitive, shouldAskConfirmation, createActionPreview, detectCommandIntent, loadMicrophonePermissionRecord, loadProfile, isOnboardingComplete, MicrophonePermissionStatus, requestMicrophoneAccess, saveMicrophonePermissionRecord, UserProfile, CommandUnderstandingResult, CommandIntent, CommandRiskLevel, requestBackendCommandPreview, BackendCommandPreviewResponse, createCommandHistoryEntry, saveCommandHistoryEntry, loadCommandHistory, clearCommandHistory, getLatestCommandHistory, deleteCommandHistoryEntry, CommandHistoryEntry, BackendAuditPreviewResponse, requestBackendAuditPreview, BackendAuditHealthResponse, getBackendAuditHealth, BackendAuditMigrationPreviewResponse, getBackendAuditMigrationPreview, BackendDatabaseStatusResponse, getBackendDatabaseStatus, BackendSystemStatusSummary, getBackendSystemStatus, useAutoRefresh, requestOpenWebsiteAction, buildWebsiteActionRequest, requestOpenAppAction, buildAppActionRequest, FileSearchResponseDto, requestFileSearchAction, buildFileSearchRequest, detectAppKeyFromText, containsDangerousCommandPhrase, detectFileSearchHints, getSpeechRecognitionSupportStatus, SpeechRecognitionSupportStatus, useSpeechRecognition } from "@/lib";

type BackendStatus = "checking" | "connected" | "offline";

type BackendHealth = {
  status?: string;
  app?: string;
  version?: string;
  environment?: string;
  phase?: string;
  message?: string;
};

type PageId =
  | "dashboard"
  | "voice"
  | "commands"
  | "automations"
  | "files"
  | "launcher"
  | "web"
  | "chat"
  | "history"
  | "settings"
  | "security"
  | "skills";

const navItems: Array<{ id: PageId; label: string; description: string }> = [
  { id: "dashboard", label: "Dashboard", description: "Main command center" },
  { id: "voice", label: "Voice", description: "Voice assistant interface" },
  { id: "commands", label: "Commands", description: "Intent and command testing" },
  { id: "automations", label: "Automations", description: "Workflow builder" },
  { id: "files", label: "File Organizer", description: "Search and organize files" },
  { id: "launcher", label: "App Launcher", description: "Open apps and websites" },
  { id: "web", label: "Web Search", description: "News, weather, dictionary" },
  { id: "chat", label: "AI Chat", description: "Assistant conversation" },
  { id: "history", label: "History", description: "Command activity logs" },
  { id: "settings", label: "Settings", description: "Profile and preferences" },
  { id: "security", label: "Security", description: "Permissions and safety" },
  { id: "skills", label: "Skills", description: "Capabilities and productivity" },
];






export default function App() {
  const engine = useEngine();
  const platform = window.nexa?.platform ?? "win32";
  const appMode = window.nexa?.appMode ?? "desktop";
  const backendUrl = window.nexa?.backendUrl ?? "http://127.0.0.1:8766";

  const [showSplash, setShowSplash] = useState(true);
  const [profile, setProfile] = useState<UserProfile>(() => loadProfile());
  const [showOnboarding, setShowOnboarding] = useState(() => !isOnboardingComplete());
  const startup = useStartupSequence();

  const [activePage, setActivePage] = useState<PageId>("dashboard");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [draftCommand, setDraftCommand] = useState("Open YouTube and play a relaxing Bangla song");
  const [commandSeed, setCommandSeed] = useState<{ text: string; ts: number; autoSpeak?: boolean; source?: string } | null>(null);
  const [dueReminderCount, setDueReminderCount] = useState(0);

  useEffect(() => {
    const checkDueReminders = async () => {
      try {
        const response = await getBackendReminders();
        setDueReminderCount(response.due_now.length);
      } catch {
        setDueReminderCount(0);
      }
    };
    checkDueReminders();
    const timer = window.setInterval(checkDueReminders, 60000);
    return () => window.clearInterval(timer);
  }, []);

  const activeNav = navItems.find((item) => item.id === activePage) ?? navItems[0];
  const backendConnected = backendStatus === "connected";

  const commandPreview = useMemo(() => {
    if (!draftCommand.trim()) return "Waiting for your command...";
    return draftCommand.trim();
  }, [draftCommand]);

  useEffect(() => {
    let timeout: number | undefined;
    if (startup.isComplete) {
      timeout = window.setTimeout(() => {
        setShowSplash(false);
      }, 400);
    }
    return () => {
      if (timeout !== undefined) {
        window.clearTimeout(timeout);
      }
    };
  }, [startup.isComplete]);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/health`);
        if (!response.ok) throw new Error("Backend health request failed");
        const data = (await response.json()) as BackendHealth;
        setBackendHealth(data);
        setBackendStatus("connected");
      } catch {
        setBackendHealth(null);
        setBackendStatus("offline");
      }
    };

    checkBackend();
    const timer = window.setInterval(checkBackend, 10000);
    return () => window.clearInterval(timer);
  }, [backendUrl]);

  const handleResetSetup = () => {
    clearProfile();
    const freshProfile = loadProfile();
    setProfile(freshProfile);
    setShowOnboarding(true);
    setActivePage("dashboard");
  };

  if (showSplash) {
    return (
      <SplashScreen
        progress={startup.progress}
        statusText={startup.statusText}
        activeStep={startup.activeStep}
        steps={startup.steps}
      />
    );
  }

  if (showOnboarding) {
    return (
      <WelcomeOnboarding
        onContinue={(savedProfile) => {
          if (savedProfile) {
            setProfile(savedProfile);
          }
          setShowOnboarding(false);
        }}
      />
    );
  }

  const railPages: PageId[] = ["dashboard", "launcher", "web", "settings"];
  const hasRail = railPages.includes(activePage);

  const pageContent =
    (activePage === "dashboard" || (engine.enabled && (activePage === "voice" || activePage === "chat"))) ? (
      <CommandCenterPage
        backendConnected={backendConnected}
        commandSeed={commandSeed}
        onNavigate={(page) => setActivePage(page as PageId)}
      />
    ) : activePage === "launcher" ? (
      <LauncherHubPage />
    ) : activePage === "web" ? (
      <WebAnswersPage />
    ) : activePage === "chat" ? (
      <ChatPage />
    ) : activePage === "voice" ? (
      <VoicePage onBack={() => setActivePage("dashboard")} />
    ) : activePage === "settings" ? (
      <SettingsPageV2 onResetSetup={handleResetSetup} />
    ) : activePage === "automations" ? (
      <AutomationsPage />
    ) : activePage === "skills" ? (
      <SkillsHubPage />
    ) : (
      <div className="nx-page">
        <ModulePage page={activePage} />
      </div>
    );

  return (
    <>
      <AIGlobeBackground />
      <EngineParticles />
      <main className="nx-shell dashboard-enter">
      <Sidebar
        active={activePage as NavId}
        backendConnected={backendConnected}
        onSelect={(id) => setActivePage(id as PageId)}
      />

      <section className="nx-main">
        <Topbar
          profileName={profile.userName || "Local User"}
          voiceReady={backendConnected}
          dueReminderCount={dueReminderCount}
          onCommandSubmit={(text) => {
            setCommandSeed({ text, ts: Date.now(), source: `dashboard_text:${activePage}` });
            setActivePage("dashboard");
          }}
          onVoiceTranscript={(text) => new Promise<void>((resolve) => {
            let timeoutId = 0;
            const done = () => {
              window.clearTimeout(timeoutId);
              window.removeEventListener("nexa:voice-turn-complete", done);
              resolve();
            };
            window.addEventListener("nexa:voice-turn-complete", done, { once: true });
            timeoutId = window.setTimeout(done, 45_000);
            setCommandSeed({ text, ts: Date.now(), autoSpeak: true, source: `global_voice:${activePage}` });
            setActivePage("dashboard");
          })}
          onOpenVoice={() => setActivePage("voice")}
          onOpenSettings={() => setActivePage("settings")}
        />

        {/* Keyed on the active page so each view glides in on mount. The motion
            element *is* the .nx-content grid, preserving the main+rail
            two-column layout emitted by pages as fragment children. Enter-only
            (remount per key) — no exit/AnimatePresence, so page swaps can never
            deadlock waiting on an exit animation. */}
        <motion.div
          key={activePage}
          className={hasRail ? "nx-content" : "nx-content full"}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
        >
          {pageContent}
        </motion.div>

        <footer className="nx-footer">
          <span><ShieldCheckIcon /> Private</span>
          <span><ShieldCheckIcon /> Secure</span>
          <span><ShieldCheckIcon /> Whitelist + Confirmation</span>
          <span><ShieldCheckIcon /> {appMode.toUpperCase()} · {platform}</span>
        </footer>
      </section>
      </main>
    </>
  );
}

function ShieldCheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
      <path d="M20 13c0 5-3.5 7.5-8 8.5-4.5-1-8-3.5-8-8.5V6l8-3 8 3z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}



function ModulePage({ page }: { page: PageId }) {
  // Only these routes reach ModulePage; the rest are handled by the App switch.
  if (page === "commands") return <CommandsPage />;
  if (page === "files") return <FilesPage />;
  if (page === "history") return <HistoryPage />;
  if (page === "security") return <SecurityCenterPage />;
  return null;
}

















export { App };

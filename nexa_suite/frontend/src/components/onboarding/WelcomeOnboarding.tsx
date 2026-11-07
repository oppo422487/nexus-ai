import { useState } from "react";
import {
  saveProfile,
  formatAddressingName,
  UserProfile,
  AddressingPreference,
  LanguageMode,
  VoicePreference,
} from "@/lib";

type WelcomeOnboardingProps = {
  onContinue?: (profile?: UserProfile) => void;
};

const addressingOptions = ["Boss", "Sir", "Vai", "Neutral"] as const;
const languageModeOptions = ["Bangla", "English", "Mixed"] as const;
const voicePreferenceOptions = ["Male voice", "Female voice", "System default"] as const;

type AddressingOption = (typeof addressingOptions)[number] & AddressingPreference;
type LanguageModeType = (typeof languageModeOptions)[number] & LanguageMode;
type VoicePreferenceType = (typeof voicePreferenceOptions)[number] & VoicePreference;

export function WelcomeOnboarding({ onContinue }: WelcomeOnboardingProps) {
  const [userName, setUserName] = useState("");
  const [addressingPreference, setAddressingPreference] = useState<AddressingOption>("Boss");
  const [languageMode, setLanguageMode] = useState<LanguageModeType>("Mixed");
  const [voicePreference, setVoicePreference] = useState<VoicePreferenceType>("System default");

  const features = [
    {
      title: "Voice-first desktop assistant",
      description: "Speak naturally and let Nexa control your PC like a personal companion.",
    },
    {
      title: "Bangla + English understanding",
      description: "Switch languages seamlessly for commands, search, and workflow control.",
    },
    {
      title: "File, app, web, and automation control",
      description: "Open files, launch apps, browse web content, and orchestrate future automations.",
    },
    {
      title: "Future ESP32 smart home support",
      description: "Prepare for next-gen local device control from your desktop assistant.",
    },
  ];

  const trimmedName = userName.trim();
  const previewName = formatAddressingName({
    userName: trimmedName,
    addressingPreference,
  });

  const handleContinue = () => {
    const savedProfile = saveProfile({
      userName: trimmedName,
      addressingPreference,
      languageMode,
      voicePreference,
      hasCompletedOnboarding: true,
    });

    if (onContinue) {
      onContinue(savedProfile);
    }
  };

  return (
    <div className="onboarding-screen">
      <div className="onboarding-grid">
        <div className="onboarding-card">
          <p className="onboarding-eyebrow">Welcome</p>
          <h1 className="onboarding-title">
            Welcome to <span>Nexa AI</span>
          </h1>
          <p className="onboarding-subtitle">
            Your Windows desktop personal AI assistant is ready to guide you through a smarter workflow.
          </p>

          <div className="onboarding-form">
            <div className="onboarding-field">
              <label className="onboarding-label" htmlFor="onboarding-name">
                Your name
              </label>
              <input
                id="onboarding-name"
                className="onboarding-input"
                type="text"
                placeholder="Enter your name"
                value={userName}
                onChange={(event) => setUserName(event.target.value)}
              />
            </div>

            <div className="onboarding-field">
              <p className="onboarding-label">Addressing preference</p>
              <div className="addressing-grid">
                {addressingOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`addressing-card ${option === addressingPreference ? "active" : ""}`}
                    onClick={() => setAddressingPreference(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="addressing-preview">
              Nexa will address you as: <strong>{previewName}</strong>
            </div>

            <div className="preference-section">
              <h3 className="preference-title">Language mode</h3>
              <div className="preference-grid">
                {languageModeOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`preference-card ${option === languageMode ? "active" : ""}`}
                    onClick={() => setLanguageMode(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="preference-section">
              <h3 className="preference-title">Voice preference</h3>
              <div className="preference-grid">
                {voicePreferenceOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={`preference-card ${option === voicePreference ? "active" : ""}`}
                    onClick={() => setVoicePreference(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="setup-summary">
              <div className="setup-summary-row">
                <span>Addressing:</span>
                <strong>{previewName}</strong>
              </div>
              <div className="setup-summary-row">
                <span>Language:</span>
                <strong>{languageMode}</strong>
              </div>
              <div className="setup-summary-row">
                <span>Voice:</span>
                <strong>{voicePreference}</strong>
              </div>
            </div>
          </div>

          <div className="onboarding-feature-grid">
            {features.map((feature, index) => (
              <article className="onboarding-feature-card" key={feature.title}>
                <span className="onboarding-feature-number">{index + 1}</span>
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </article>
            ))}
          </div>

          <div className="onboarding-action-row">
            <button
              type="button"
              className="onboarding-primary-button"
              onClick={handleContinue}
            >
              Continue Setup
            </button>
            <p className="onboarding-note">Your setup will be saved locally on this device.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WelcomeOnboarding;

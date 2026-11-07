import { VoiceConversation } from "@/components/voice/VoiceConversation";

export function VoicePage({ onBack }: { onBack: () => void }) {
  return <div className="nx-voice-page"><VoiceConversation onBack={onBack} autoStart /></div>;
}

export default VoicePage;

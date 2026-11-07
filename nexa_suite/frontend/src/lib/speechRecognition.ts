export type SpeechRecognitionSupportStatus = {
  supported: boolean;
  apiName: "SpeechRecognition" | "webkitSpeechRecognition" | "none";
  message: string;
};

export function getSpeechRecognitionConstructor(): any | null {
  if (typeof window === "undefined") return null;
  if (typeof (window as any).SpeechRecognition !== "undefined") {
    return (window as any).SpeechRecognition;
  }
  if (typeof (window as any).webkitSpeechRecognition !== "undefined") {
    return (window as any).webkitSpeechRecognition;
  }
  return null;
}

export function getSpeechRecognitionSupportStatus(): SpeechRecognitionSupportStatus {
  const ctor = getSpeechRecognitionConstructor();
  if (ctor === null) {
    return {
      supported: false,
      apiName: "none",
      message: "Speech recognition is not supported in this environment.",
    };
  }
  if (typeof (window as any).SpeechRecognition !== "undefined") {
    return {
      supported: true,
      apiName: "SpeechRecognition",
      message: "Speech recognition is supported.",
    };
  }
  return {
    supported: true,
    apiName: "webkitSpeechRecognition",
    message: "WebKit speech recognition is supported.",
  };
}

export function isSpeechRecognitionSupported(): boolean {
  return getSpeechRecognitionConstructor() !== null;
}

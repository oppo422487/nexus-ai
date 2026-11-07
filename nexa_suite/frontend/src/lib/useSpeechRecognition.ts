import { useCallback, useEffect, useRef, useState } from "react";
import { getSpeechRecognitionConstructor } from "./speechRecognition";

export type SpeechListeningStatus =
  | "idle"
  | "listening"
  | "stopped"
  | "unsupported"
  | "error";

export type UseSpeechRecognitionOptions = {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  onFinalTranscript?: (text: string) => void;
  onInterimTranscript?: (text: string) => void;
};

export function useSpeechRecognition(options?: UseSpeechRecognitionOptions) {
  const RecognitionConstructor = getSpeechRecognitionConstructor();
  const supported = RecognitionConstructor !== null;

  const [status, setStatus] = useState<SpeechListeningStatus>("idle");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const manuallyStoppedRef = useRef(false);
  const finalRef = useRef("");
  const interimRef = useRef("");

  const {
    language = "bn-BD",
    continuous = true,
    interimResults = true,
    onFinalTranscript,
    onInterimTranscript,
  } = options ?? {};

  const startListening = useCallback(() => {
    if (!supported) {
      setStatus("unsupported");
      setErrorMessage("Speech recognition is not supported in this environment.");
      return;
    }

    setErrorMessage(null);
    manuallyStoppedRef.current = false;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
    }

    const recognition = new RecognitionConstructor();
    recognition.lang = language;
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;

    recognition.onresult = (event: any) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        finalRef.current += final;
        setFinalTranscript(finalRef.current);
        onFinalTranscript?.(final);
      }

      if (interim) {
        interimRef.current = interim;
        setInterimTranscript(interim);
        onInterimTranscript?.(interim);
      }
    };

    recognition.onerror = (event: any) => {
      setStatus("error");
      const err = event.error ?? "unknown";
      switch (err) {
        case "network":
          setErrorMessage(
            "Speech recognition network service is unavailable. Check internet connection or use demo transcript controls.",
          );
          break;
        case "not-allowed":
          setErrorMessage(
            "Microphone permission was denied. Please allow microphone access and try again.",
          );
          break;
        case "no-speech":
          setErrorMessage(
            "No speech was detected. Try speaking closer to the microphone.",
          );
          break;
        case "audio-capture":
          setErrorMessage(
            "No microphone was found or microphone is unavailable.",
          );
          break;
        default:
          setErrorMessage(`Recognition error: ${err}`);
          break;
      }
    };

    recognition.onend = () => {
      if (!manuallyStoppedRef.current) {
        setStatus("stopped");
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
      setStatus("listening");
    } catch (err: any) {
      setStatus("error");
      setErrorMessage(`Failed to start recognition: ${err.message ?? "unknown"}`);
    }
  }, [supported, language, continuous, interimResults, onFinalTranscript, onInterimTranscript]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      manuallyStoppedRef.current = true;
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    setStatus("stopped");
  }, []);

  const resetTranscript = useCallback(() => {
    finalRef.current = "";
    interimRef.current = "";
    setFinalTranscript("");
    setInterimTranscript("");
  }, []);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    supported,
    status,
    finalTranscript,
    interimTranscript,
    errorMessage,
    startListening,
    stopListening,
    resetTranscript,
  };
}

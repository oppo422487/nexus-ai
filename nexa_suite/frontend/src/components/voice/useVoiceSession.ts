import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type VoiceSessionStatus =
  | "idle"
  | "listening"
  | "processing"
  | "stopped"
  | "error";

export type VoiceSessionState = {
  status: VoiceSessionStatus;
  transcript: string;
  interimTranscript: string;
  errorMessage: string | null;
  startedAt: string | null;
  stoppedAt: string | null;
  elapsedSeconds: number;
  isListening: boolean;
  isProcessing: boolean;
};

const INITIAL_STATE: VoiceSessionState = {
  status: "idle",
  transcript: "",
  interimTranscript: "",
  errorMessage: null,
  startedAt: null,
  stoppedAt: null,
  elapsedSeconds: 0,
  isListening: false,
  isProcessing: false,
};

export function useVoiceSession() {
  const [status, setStatus] = useState<VoiceSessionStatus>("idle");
  const [transcript, setTranscriptState] = useState("");
  const [interimTranscript, setInterimTranscriptState] = useState("");
  const [errorMessage, setErrorMessageState] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<string | null>(null);
  const [stoppedAt, setStoppedAt] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const intervalRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const isListening = useMemo(() => status === "listening", [status]);
  const isProcessing = useMemo(() => status === "processing", [status]);

  const clearTimers = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const startSession = useCallback(() => {
    clearTimers();
    const now = new Date().toISOString();
    setStatus("listening");
    setStartedAt(now);
    setStoppedAt(null);
    setErrorMessageState(null);
    setElapsedSeconds(0);
  }, [clearTimers]);

  const stopSession = useCallback(() => {
    clearTimers();
    setStatus("stopped");
    setStoppedAt(new Date().toISOString());
  }, [clearTimers]);

  const resetSession = useCallback(() => {
    clearTimers();
    setStatus("idle");
    setTranscriptState("");
    setInterimTranscriptState("");
    setErrorMessageState(null);
    setStartedAt(null);
    setStoppedAt(null);
    setElapsedSeconds(0);
  }, [clearTimers]);

  const setError = useCallback((message: string) => {
    clearTimers();
    setStatus("error");
    setErrorMessageState(message);
  }, [clearTimers]);

  const simulateProcessing = useCallback(() => {
    clearTimers();
    setStatus("processing");
    setErrorMessageState(null);
    timeoutRef.current = window.setTimeout(() => {
      setStatus("stopped");
      setStoppedAt(new Date().toISOString());
      timeoutRef.current = null;
    }, 800);
  }, [clearTimers]);

  useEffect(() => {
    if (status === "listening") {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
      }
      intervalRef.current = window.setInterval(() => {
        setElapsedSeconds((current) => current + 1);
      }, 1000);
      return () => {
        if (intervalRef.current !== null) {
          window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }

    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return undefined;
  }, [status]);

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  const state: VoiceSessionState = useMemo(
    () => ({
      status,
      transcript,
      interimTranscript,
      errorMessage,
      startedAt,
      stoppedAt,
      elapsedSeconds,
      isListening,
      isProcessing,
    }),
    [status, transcript, interimTranscript, errorMessage, startedAt, stoppedAt, elapsedSeconds, isListening, isProcessing]
  );

  return {
    state,
    startSession,
    stopSession,
    resetSession,
    setTranscript: setTranscriptState,
    setInterimTranscript: setInterimTranscriptState,
    setError,
    simulateProcessing,
  };
}

import { useCallback, useEffect, useRef, useState } from "react";

export type AutoRefreshStatus = "idle" | "running" | "paused" | "error";

export type UseAutoRefreshOptions = {
  enabled?: boolean;
  intervalMs?: number;
  pauseWhenHidden?: boolean;
  runImmediately?: boolean;
  onRefresh: () => Promise<void> | void;
};

export type UseAutoRefreshReturn = {
  enabled: boolean;
  status: AutoRefreshStatus;
  lastRunAt: string | null;
  errorMessage: string | null;
  runNow: () => Promise<void>;
  setEnabled: (value: boolean) => void;
  pause: () => void;
  resume: () => void;
};

export function useAutoRefresh(
  options: UseAutoRefreshOptions,
): UseAutoRefreshReturn {
  const {
    enabled: initialEnabled = false,
    intervalMs = 30000,
    pauseWhenHidden = true,
    runImmediately = false,
    onRefresh,
  } = options;

  const [enabled, setEnabled] = useState(initialEnabled);
  const [status, setStatus] = useState<AutoRefreshStatus>(
    initialEnabled ? "running" : "idle",
  );
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const enabledRef = useRef(enabled);
  const onRefreshRef = useRef(onRefresh);

  enabledRef.current = enabled;
  onRefreshRef.current = onRefresh;

  const clearRefreshInterval = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const runNow = useCallback(async () => {
    setErrorMessage(null);
    setStatus("running");
    try {
      await onRefreshRef.current();
      setLastRunAt(new Date().toISOString());
      setStatus(enabledRef.current ? "running" : "idle");
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Auto-refresh failed unexpectedly.";
      setErrorMessage(msg);
      setStatus("error");
    }
  }, []);

  const pause = useCallback(() => {
    clearRefreshInterval();
    setStatus("paused");
  }, [clearRefreshInterval]);

  const resume = useCallback(() => {
    if (!enabledRef.current) return;
    clearRefreshInterval();
    intervalRef.current = setInterval(runNow, intervalMs);
    setStatus("running");
  }, [clearRefreshInterval, intervalMs, runNow]);

  useEffect(() => {
    if (enabled) {
      if (runImmediately) {
        runNow();
      }
      intervalRef.current = setInterval(runNow, intervalMs);
      setStatus("running");
    } else {
      clearRefreshInterval();
      setStatus("idle");
    }

    return () => {
      clearRefreshInterval();
    };
  }, [enabled, intervalMs, runImmediately, runNow, clearRefreshInterval]);

  useEffect(() => {
    if (!pauseWhenHidden || !enabled) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        clearRefreshInterval();
        setStatus("paused");
      } else {
        intervalRef.current = setInterval(runNow, intervalMs);
        setStatus("running");
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [pauseWhenHidden, enabled, intervalMs, runNow, clearRefreshInterval]);

  return {
    enabled,
    status,
    lastRunAt,
    errorMessage,
    runNow,
    setEnabled,
    pause,
    resume,
  };
}

import { useEffect, useState } from "react";

export type StartupStep = {
  id: string;
  label: string;
  durationMs: number;
  progressTarget: number;
};

export type StartupSequenceState = {
  progress: number;
  statusText: string;
  activeStep: number;
  isComplete: boolean;
  steps: StartupStep[];
};

const DEFAULT_STEPS: StartupStep[] = [
  {
    id: "desktop-shell",
    label: "Loading desktop shell",
    durationMs: 700,
    progressTarget: 25,
  },
  {
    id: "react-renderer",
    label: "Preparing React renderer",
    durationMs: 900,
    progressTarget: 50,
  },
  {
    id: "backend-check",
    label: "Checking local backend",
    durationMs: 900,
    progressTarget: 75,
  },
  {
    id: "command-center",
    label: "Initializing command center",
    durationMs: 900,
    progressTarget: 100,
  },
];

export function useStartupSequence(): StartupSequenceState {
  const [progress, setProgress] = useState(0);
  const [activeStep, setActiveStep] = useState(1);
  const [statusText, setStatusText] = useState(DEFAULT_STEPS[0].label);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    let startTime = performance.now();
    let frameId: number;

    const totalDuration = DEFAULT_STEPS.reduce((acc, step) => acc + step.durationMs, 0);

    const tick = (now: number) => {
      const elapsed = Math.min(now - startTime, totalDuration);
      const nextProgress = Math.round((elapsed / totalDuration) * 100);

      setProgress(nextProgress);

      const currentStepIndex = DEFAULT_STEPS.findIndex(
        (step) => nextProgress <= step.progressTarget
      );
      const nextActiveStep = currentStepIndex === -1 ? DEFAULT_STEPS.length : currentStepIndex + 1;
      setActiveStep(nextActiveStep);
      setStatusText(DEFAULT_STEPS[nextActiveStep - 1]?.label ?? DEFAULT_STEPS[DEFAULT_STEPS.length - 1].label);

      if (elapsed < totalDuration) {
        frameId = requestAnimationFrame(tick);
      } else {
        setProgress(100);
        setActiveStep(DEFAULT_STEPS.length);
        setStatusText(DEFAULT_STEPS[DEFAULT_STEPS.length - 1].label);
        setIsComplete(true);
      }
    };

    frameId = requestAnimationFrame(tick);

    // requestAnimationFrame is paused for hidden/background windows, which
    // would leave the splash stuck forever. Guarantee completion on a timer.
    const fallbackId = window.setTimeout(() => {
      setProgress(100);
      setActiveStep(DEFAULT_STEPS.length);
      setStatusText(DEFAULT_STEPS[DEFAULT_STEPS.length - 1].label);
      setIsComplete(true);
    }, totalDuration + 600);

    return () => {
      cancelAnimationFrame(frameId);
      window.clearTimeout(fallbackId);
    };
  }, []);

  return {
    progress,
    statusText,
    activeStep,
    isComplete,
    steps: DEFAULT_STEPS,
  };
}

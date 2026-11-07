type SplashStep = {
  id: string;
  label: string;
};

type SplashScreenProps = {
  progress?: number;
  statusText?: string;
  activeStep?: number;
  steps?: SplashStep[];
};

export function SplashScreen({
  progress = 35,
  statusText = "Starting Nexa AI workspace...",
  activeStep = 1,
  steps,
}: SplashScreenProps) {
  const defaultSteps: SplashStep[] = [
    { id: "desktop-shell", label: "Loading desktop shell" },
    { id: "react-renderer", label: "Preparing React renderer" },
    { id: "backend-check", label: "Checking local backend" },
    { id: "command-center", label: "Initializing command center" },
  ];

  const stepList = steps && steps.length > 0 ? steps : defaultSteps;
  const normalizedProgress = Math.min(100, Math.max(0, progress));
  const safeActiveStep = Math.min(stepList.length, Math.max(1, activeStep));

  return (
    <div className="splash-screen">
      <div className="splash-grid">
        <div className="splash-card">
          <p className="splash-eyebrow">Desktop Assistant Boot Sequence</p>
          <h1>Nexa AI</h1>
          <p className="splash-subtitle">{statusText}</p>

          <div className="splash-orb" aria-hidden="true">
            <div className="splash-orb-ring">
              <div className="splash-orb-core" />
            </div>
          </div>

          <div className="splash-progress-wrap">
            <div className="splash-progress-top">
              <span>Boot progress</span>
              <span>{normalizedProgress}%</span>
            </div>
            <div className="splash-progress-track">
              <div
                className="splash-progress-fill"
                style={{ width: `${normalizedProgress}%` }}
              />
            </div>
          </div>

          <ul className="splash-steps">
            {stepList.map((step, index) => {
              const stepIndex = index + 1;
              const status =
                stepIndex < safeActiveStep
                  ? "completed"
                  : stepIndex === safeActiveStep
                  ? "active"
                  : "pending";

              return (
                <li key={step.id} className={`splash-step ${status}`}>
                  <span>{stepIndex}.</span>
                  <span>{step.label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default SplashScreen;

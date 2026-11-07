/* Public surface of the environment layer. The app root imports only
   EnvironmentEngine; everything else is internal to this module. */
export { EnvironmentEngine } from "./EnvironmentEngine";
export type { QualityTier } from "./config";
export { usePerformance } from "./hooks/usePerformance";

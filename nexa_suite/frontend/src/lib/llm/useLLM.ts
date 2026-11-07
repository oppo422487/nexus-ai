/* ============================================================================
   MULTI-LLM · useLLM
   ----------------------------------------------------------------------------
   React binding for the manager. Subscribes via useSyncExternalStore against a
   monotonic version counter, so any settings/status/analytics change re-renders
   consumers without prop drilling.
   ========================================================================== */
import { useSyncExternalStore } from "react";
import { llmManager } from "./manager";
import type { LLMAnalytics, LLMSettings, ProviderId, ProviderMeta, ProviderStatus } from "./types";

export interface UseLLM {
  settings: LLMSettings;
  analytics: LLMAnalytics;
  metas: ProviderMeta[];
  statusOf: (id: ProviderId) => ProviderStatus;
  manager: typeof llmManager;
}

export function useLLM(): UseLLM {
  useSyncExternalStore(
    (cb) => llmManager.subscribe(cb),
    () => llmManager.version,
    () => llmManager.version,
  );

  return {
    settings: llmManager.getSettings(),
    analytics: llmManager.getAnalytics(),
    metas: llmManager.allMeta(),
    statusOf: (id) => llmManager.getStatus(id),
    manager: llmManager,
  };
}

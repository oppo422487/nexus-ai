/* ============================================================================
   ENVIRONMENT · PerformanceManager
   ----------------------------------------------------------------------------
   Pure, framework-agnostic performance logic: WebGL capability detection,
   initial quality-tier estimation from device signals, and tier stepping used
   by the adaptive quality loop. No React, no Three.js imports — safe to unit
   test and reuse.
   ========================================================================== */

import type { QualityTier } from "../config";

export const QUALITY_ORDER: QualityTier[] = ["low", "medium", "high"];

/** Returns true if a WebGL context can be created at all. */
export function isWebGLAvailable(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const canvas = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext("webgl2") || canvas.getContext("webgl"))
    );
  } catch {
    return false;
  }
}

interface DeviceSignals {
  cores: number;
  memoryGB: number;
  /** Lowercased GPU renderer string, when exposed. */
  renderer: string;
  mobile: boolean;
}

function readDeviceSignals(): DeviceSignals {
  const nav = typeof navigator !== "undefined" ? navigator : ({} as Navigator);
  const cores = nav.hardwareConcurrency || 4;
  const memoryGB = (nav as Navigator & { deviceMemory?: number }).deviceMemory || 4;
  const mobile = /Mobi|Android|iPhone|iPad/i.test(nav.userAgent || "");

  let renderer = "";
  try {
    const canvas = document.createElement("canvas");
    const gl = (canvas.getContext("webgl") ||
      canvas.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (gl) {
      const dbg = gl.getExtension("WEBGL_debug_renderer_info");
      if (dbg) renderer = String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || "").toLowerCase();
    }
  } catch {
    /* ignore — renderer probing is best-effort */
  }
  return { cores, memoryGB, renderer, mobile };
}

/** Estimate a safe starting tier from device capability. */
export function detectInitialTier(): QualityTier {
  const { cores, memoryGB, renderer, mobile } = readDeviceSignals();

  if (mobile) return "low";

  const weakGpu = /(intel|uhd|hd graphics|swiftshader|llvmpipe|apple gpu|mali|adreno)/.test(renderer);
  const strongGpu = /(rtx|radeon rx|geforce|nvidia|arc|m1|m2|m3|m4|apple m)/.test(renderer);

  if (strongGpu && cores >= 8 && memoryGB >= 8) return "high";
  if (weakGpu || cores <= 4 || memoryGB <= 4) return "low";
  return "medium";
}

/** Step the tier up or down one step, clamped to the available range. */
export function stepTier(current: QualityTier, direction: 1 | -1): QualityTier {
  const idx = QUALITY_ORDER.indexOf(current);
  const next = Math.min(QUALITY_ORDER.length - 1, Math.max(0, idx + direction));
  return QUALITY_ORDER[next];
}

/* ============================================================================
   AI GLOBE BACKGROUND · Quality
   ----------------------------------------------------------------------------
   Three presets (High / Medium / Low) + automatic GPU-tier detection so the
   background scales down on weak hardware. Pure, no side effects at import.
   ========================================================================== */

export type QualityTier = "high" | "medium" | "low";
export type QualitySetting = "auto" | QualityTier;

export interface QualityPreset {
  tier: QualityTier;
  /** Renderer pixel-ratio cap. */
  dpr: number;
  /** Floating particle count. */
  particles: number;
  /** Neural-network node count. */
  neuralNodes: number;
  /** Neural-network connection (arc) count. */
  neuralLinks: number;
  /** Pulse travel time along a connection (ms). */
  arcDashAnimateTime: number;
  antialias: boolean;
  bloom: boolean;
  bloomStrength: number;
  bloomRadius: number;
  bloomThreshold: number;
  /** Auto-rotate speed (deg/frame-ish, OrbitControls units). */
  autoRotateSpeed: number;
  /** Hex-polygon (dotted countries) resolution — higher = denser dots. */
  hexResolution: number;
  hexMargin: number;
}

function dprCap(max: number): number {
  const raw = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
  return Math.min(raw, max);
}

export function qualityPresets(): Record<QualityTier, QualityPreset> {
  return {
    high: {
      tier: "high",
      dpr: dprCap(2),
      particles: 4000,
      neuralNodes: 60,
      neuralLinks: 90,
      arcDashAnimateTime: 3200,
      antialias: true,
      bloom: true,
      bloomStrength: 0.9,
      bloomRadius: 0.6,
      bloomThreshold: 0.08,
      autoRotateSpeed: 0.35,
      hexResolution: 3,
      hexMargin: 0.28,
    },
    medium: {
      tier: "medium",
      dpr: dprCap(1.5),
      particles: 1800,
      neuralNodes: 42,
      neuralLinks: 58,
      arcDashAnimateTime: 3600,
      antialias: true,
      bloom: true,
      bloomStrength: 0.7,
      bloomRadius: 0.5,
      bloomThreshold: 0.12,
      autoRotateSpeed: 0.3,
      hexResolution: 2,
      hexMargin: 0.3,
    },
    low: {
      tier: "low",
      dpr: 1,
      particles: 700,
      neuralNodes: 26,
      neuralLinks: 32,
      arcDashAnimateTime: 4200,
      antialias: false,
      bloom: false,
      bloomStrength: 0,
      bloomRadius: 0,
      bloomThreshold: 0,
      autoRotateSpeed: 0.28,
      hexResolution: 1,
      hexMargin: 0.4,
    },
  };
}

/** Best-effort GPU tier detection (renderer string + core/memory heuristics). */
export function detectQualityTier(): QualityTier {
  if (typeof window === "undefined" || typeof document === "undefined") return "low";

  // Coarse device signals first.
  const nav = navigator as Navigator & { deviceMemory?: number };
  const cores = nav.hardwareConcurrency ?? 4;
  const memory = nav.deviceMemory ?? 4;
  const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(nav.userAgent);

  // GPU renderer string (software renderers → low).
  let renderer = "";
  try {
    const canvas = document.createElement("canvas");
    const gl = (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (gl) {
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      if (ext) renderer = String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || "").toLowerCase();
      const lose = gl.getExtension("WEBGL_lose_context");
      lose?.loseContext();
    } else {
      return "low"; // no WebGL at all
    }
  } catch {
    /* ignore — fall through to heuristics */
  }

  const software = /swiftshader|llvmpipe|software|microsoft basic|paravirtual/.test(renderer);
  if (software) return "low";
  if (mobile || cores <= 4 || memory <= 4) return "medium";
  return "high";
}

export function resolvePreset(setting: QualitySetting): QualityPreset {
  const presets = qualityPresets();
  const tier: QualityTier = setting === "auto" ? detectQualityTier() : setting;
  return presets[tier];
}

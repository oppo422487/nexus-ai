/* ============================================================================
   ENVIRONMENT · CONFIG  (Phase E — cinematic AI universe)
   ----------------------------------------------------------------------------
   Single source of truth for the environment. Every scene component reads from
   here — no component hardcodes a colour, count, speed, or radius. Values that
   scale with device capability live in QUALITY_PRESETS keyed by tier.
   ========================================================================== */

export type QualityTier = "low" | "medium" | "high";

/** Palette for the WebGL layer (mirrors the CSS design tokens). */
export const ENV_PALETTE = {
  deepSpace: "#04060e",
  earthCore: "#08192e",
  earthGrid: "#5ff2ff",
  coreGlow: "#2ef2ff",
  atmosphere: "#3b82f6",
  atmosphereGlow: "#2ef2ff",
  cloud: "#8fb8ff",
  moon: "#8ea0c8",
  satellite: "#7dd3fc",
  satellitePacket: "#d4fbff",
  ring: "#2f76d6",
  star: "#cfe4ff",
  particle: "#6f9bff",
  debris: "#4a6099",
  neuralNode: "#2ef2ff",
  neuralLink: "#3b82f6",
  neuralPacket: "#d4fbff",
  nebulaA: "#4a3ee0",
  nebulaB: "#0e8ad6",
  nebulaC: "#c13dff",
  shootingStar: "#dff2ff",
  energyRing: "#2ef2ff",
  ambient: "#12304f",
  keyLight: "#dff2ff",
  rimLight: "#3b7bff",
  backLight: "#b24dff",
  fog: "#050912",
} as const;

/** Per-tier quality budget. Higher tiers add geometry/particles/effects + DPR. */
export interface QualityPreset {
  dpr: [number, number];
  antialias: boolean;
  earthSegments: number;
  earthPoints: number;
  cloudsEnabled: boolean;
  moonEnabled: boolean;
  satelliteEnabled: boolean;
  starCount: number;
  particleCount: number;
  neuralNodes: number;
  neuralMaxLinks: number;
  // ---- Phase E cinematic systems ----
  neuralPackets: number;
  nebulaEnabled: boolean;
  shootingStarsEnabled: boolean;
  energyRingsEnabled: boolean;
  orbitRingsEnabled: boolean;
  commSatellites: number;
  dataPackets: number;
  debrisCount: number;
  bloom: boolean;
  bloomIntensity: number;
  /** Number of energy beams radiating from the Core toward the UI. */
  energyBeams: number;
}

export const QUALITY_PRESETS: Record<QualityTier, QualityPreset> = {
  low: {
    dpr: [1, 1],
    antialias: false,
    earthSegments: 40,
    earthPoints: 1500,
    cloudsEnabled: false,
    moonEnabled: false,
    satelliteEnabled: false,
    starCount: 1600,
    particleCount: 700,
    neuralNodes: 260,
    neuralMaxLinks: 2,
    neuralPackets: 0,
    nebulaEnabled: false,
    shootingStarsEnabled: false,
    energyRingsEnabled: true,
    orbitRingsEnabled: false,
    commSatellites: 0,
    dataPackets: 0,
    debrisCount: 0,
    bloom: false,
    bloomIntensity: 0,
    energyBeams: 6,
  },
  medium: {
    dpr: [1, 1.5],
    antialias: true,
    earthSegments: 56,
    earthPoints: 2800,
    cloudsEnabled: true,
    moonEnabled: true,
    satelliteEnabled: true,
    starCount: 3200,
    particleCount: 1700,
    neuralNodes: 900,
    neuralMaxLinks: 3,
    neuralPackets: 44,
    nebulaEnabled: true,
    shootingStarsEnabled: true,
    energyRingsEnabled: true,
    orbitRingsEnabled: true,
    commSatellites: 3,
    dataPackets: 10,
    debrisCount: 60,
    bloom: false,
    bloomIntensity: 0,
    energyBeams: 12,
  },
  high: {
    dpr: [1, 1.75],
    antialias: true,
    earthSegments: 72,
    earthPoints: 4200,
    cloudsEnabled: true,
    moonEnabled: true,
    satelliteEnabled: true,
    starCount: 5000,
    particleCount: 2600,
    neuralNodes: 2000,
    neuralMaxLinks: 3,
    neuralPackets: 74,
    nebulaEnabled: true,
    shootingStarsEnabled: true,
    energyRingsEnabled: true,
    orbitRingsEnabled: true,
    commSatellites: 4,
    dataPackets: 16,
    debrisCount: 120,
    /* HDR glow is achieved with additive-blended geometry + filmic tone mapping
       (transparency-safe for this overlay canvas), not a fullscreen composer.
       These flags are reserved for a future opaque bloom pass. */
    bloom: false,
    bloomIntensity: 0,
    energyBeams: 18,
  },
};

/** Tier-independent scene composition (positions, speeds, sizes, camera, fog). */
export const ENV_CONFIG = {
  /** The holographic AI Core — the visual anchor, framed right-of-centre so it
      never sits directly behind text-dense content. */
  earth: {
    /* The dominant centrepiece — a massive holographic Core filling ~35% of the
       frame, framed right-of-centre so text stays clear of its densest region. */
    radius: 4.1,
    position: [2.4, -1.4, -1] as [number, number, number],
    rotationSpeed: 0.014,
    tilt: 0.41,
    coreOpacity: 0.72,
    gridOpacity: 0.92,
    pointSize: 0.03,
    fresnelPower: 2.4,
    fresnelIntensity: 2.4,
    scanSpeed: 0.7,
    /** Vertex-displacement amplitude — the surface breathes/distorts in-shader. */
    distort: 0.14,
  },
  /** The canonical AI-Core heartbeat. Both the Earth shader and the DOM read a
      pulse derived from `sin(elapsedTime * pulseSpeed)` off the same render
      clock, so the UI stays phase-locked to the Core. */
  core: {
    pulseSpeed: 0.9,
  },
  /** Energy beams radiating from the Core toward the UI regions. Endpoints are
      spread across the visible frame (left/upper toward sidebar + top). */
  beams: {
    samples: 26,
    opacity: 0.6,
    packetSpeed: 0.72,
    curveLift: 1.2,
    targets: [
      [-4.2, 2.4, 0.2],
      [-4.0, -0.6, 0.4],
      [-2.2, 3.2, 0.0],
      [-0.5, -3.2, 0.3],
      [-3.6, 0.8, -0.2],
      [1.2, 3.4, 0.1],
      [-1.5, 2.6, 0.5],
      [-3.0, -2.4, 0.2],
    ] as Array<[number, number, number]>,
  },
  atmosphere: {
    innerScale: 1.06,
    outerScale: 1.38,
    intensity: 1.9,
    power: 2.8,
    opacity: 1.2,
  },
  clouds: {
    scale: 1.045,
    rotationSpeed: 0.02,
    opacity: 0.06,
  },
  moon: {
    radius: 0.42,
    position: [-3.8, 2.2, -4] as [number, number, number],
    orbitRadius: 4.3,
    orbitSpeed: 0.02,
    rotationSpeed: 0.01,
  },
  /** Orbit rings + communication satellites + data packets around the core. */
  orbit: {
    rings: [
      { radius: 3.5, inclination: 0.55, tilt: 0.1, opacity: 0.18, speed: 0.14 },
      { radius: 4.15, inclination: -0.4, tilt: 0.3, opacity: 0.12, speed: 0.1 },
      { radius: 4.8, inclination: 0.75, tilt: -0.2, opacity: 0.08, speed: 0.07 },
    ],
    satSize: 0.055,
    packetSize: 0.045,
    packetSpeed: 0.5,
  },
  /** AI scan / circular pulse rings that expand from the core. */
  energyRings: {
    position: [2.5, -1.7, -1] as [number, number, number],
    count: 4,
    maxRadius: 5.0,
    startRadius: 2.85,
    period: 6.5,
    tilt: 1.35,
    opacity: 0.8,
  },
  stars: {
    radius: 70,
    depth: 48,
    factor: 3.6,
    saturation: 0.12,
    speed: 0.12,
    fade: true,
  },
  nebula: {
    layers: [
      { pos: [-8, 4, -22] as [number, number, number], scale: 26, color: "nebulaA", opacity: 0.27, drift: 0.006 },
      { pos: [10, -6, -26] as [number, number, number], scale: 32, color: "nebulaB", opacity: 0.23, drift: -0.004 },
      { pos: [2, 8, -30] as [number, number, number], scale: 30, color: "nebulaC", opacity: 0.19, drift: 0.005 },
    ],
  },
  shootingStars: {
    interval: 3.4, // avg seconds between streaks
    speed: 26,
    length: 2.2,
    spread: 34,
    depth: [-18, -34] as [number, number],
  },
  particles: {
    spread: 20,
    depth: 12,
    size: 0.046,
    driftSpeed: 0.012,
    opacity: 0.62,
  },
  debris: {
    spread: 26,
    depth: 16,
    size: 0.05,
    driftSpeed: 0.03,
    opacity: 0.3,
  },
  neural: {
    /** A large, deep field behind everything — the "infinite" AI graph. */
    spread: 30,
    depthBack: -10,
    linkDistance: 2.4,
    driftSpeed: 0.01,
    nodeSize: 0.028,
    nodeOpacity: 0.82,
    linkOpacity: 0.18,
    packetSize: 0.085,
    packetSpeed: 0.46,
  },
  lighting: {
    ambientIntensity: 0.4,
    keyIntensity: 2.8,
    keyPosition: [7, 4, 6] as [number, number, number],
    rimIntensity: 3.3,
    rimPosition: [-7, -1, 2] as [number, number, number],
    backIntensity: 1.6,
    backPosition: [0, 3, -10] as [number, number, number],
    exposure: 1.16,
  },
  fog: {
    near: 12,
    far: 42,
  },
  camera: {
    position: [0, 0, 9] as [number, number, number],
    fov: 46,
    parallaxStrength: 0.6,
    parallaxDamping: 0.02,
    idleDriftStrength: 0.38,
    idleDriftSpeed: 0.05,
    /** Slow depth "breathing" along Z. */
    breatheAmp: 0.28,
    breatheSpeed: 0.16,
  },
  /** A holographic scanning hex grid far behind the scene (TRON/JARVIS floor). */
  hexGrid: {
    position: [0, -1, -16] as [number, number, number],
    rotation: [-1.1, 0, 0] as [number, number, number],
    size: 60,
    cell: 26,
    lineWidth: 0.045,
    opacity: 0.16,
    scanSpeed: 0.35,
  },
  presentation: {
    opacity: 1.0,
    fadeInMs: 2000,
  },
};

export type EnvConfig = typeof ENV_CONFIG;

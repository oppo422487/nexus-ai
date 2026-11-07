/* ============================================================================
   AI GLOBE BACKGROUND · GlobeEngine
   ----------------------------------------------------------------------------
   Imperative globe.gl + Three.js scene: holographic blue Earth, cyan atmosphere,
   procedural neural-network connections with travelling light pulses, slow
   auto-rotation, and damped mouse parallax. Framework-agnostic — the React
   component owns its lifecycle.

   This is the ONLY module that imports globe.gl/three, so it is loaded lazily
   (dynamic import) and never touches the bundle when the background is disabled.
   ========================================================================== */
import Globe, { type GlobeInstance } from "globe.gl";
import type { QualityPreset } from "./quality";

interface LatLng {
  lat: number;
  lng: number;
}
interface NeuralArc {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
}

const SPACE = "#050816";
const CYAN = "#38bdf8";
const BLUE = "#3b82f6";

/* Approximate coordinates of major US hub cities — the "outbound" origins,
   mirroring the globe.gl us-international-outbound example (all connections
   radiate from the US). Hardcoded coords → no external airport data needed. */
const US_HUBS: LatLng[] = [
  { lat: 40.71, lng: -74.01 },  // New York
  { lat: 34.05, lng: -118.24 }, // Los Angeles
  { lat: 41.88, lng: -87.63 },  // Chicago
  { lat: 29.76, lng: -95.37 },  // Houston
  { lat: 25.76, lng: -80.19 },  // Miami
  { lat: 37.77, lng: -122.42 }, // San Francisco
  { lat: 47.61, lng: -122.33 }, // Seattle
  { lat: 33.75, lng: -84.39 },  // Atlanta
  { lat: 32.78, lng: -96.8 },   // Dallas
  { lat: 38.9, lng: -77.04 },   // Washington DC
  { lat: 42.36, lng: -71.06 },  // Boston
  { lat: 39.74, lng: -104.99 }, // Denver
];

/** A random international destination (anywhere outside the US bounding box). */
function internationalDestination(): LatLng {
  for (let tries = 0; tries < 12; tries += 1) {
    const lat = (Math.random() - 0.5) * 150; // avoid the poles a little
    const lng = (Math.random() - 0.5) * 360;
    const inUS = lat > 24 && lat < 49 && lng > -125 && lng < -66;
    if (!inUS) return { lat, lng };
  }
  return { lat: 0, lng: 0 };
}

/** US-outbound arcs: every connection starts at a US hub and fans out
   internationally — the us-international-outbound example's signature pattern. */
function buildOutboundArcs(destinations: number, links: number): NeuralArc[] {
  const dests = Array.from({ length: Math.max(destinations, 8) }, internationalDestination);
  const arcs: NeuralArc[] = [];
  for (let i = 0; i < links; i += 1) {
    const src = US_HUBS[Math.floor(Math.random() * US_HUBS.length)];
    const dst = dests[Math.floor(Math.random() * dests.length)];
    arcs.push({ startLat: src.lat, startLng: src.lng, endLat: dst.lat, endLng: dst.lng });
  }
  return arcs;
}

export class GlobeEngine {
  private globe: GlobeInstance | null = null;
  private inner: HTMLElement;
  private preset: QualityPreset | null = null;

  // damped parallax
  private rafId = 0;
  private running = false;
  private pointer = { x: 0, y: 0 };
  private eased = { x: 0, y: 0 };
  private onPointerMove = (e: PointerEvent) => {
    this.pointer.x = (e.clientX / window.innerWidth - 0.5) * 2;
    this.pointer.y = (e.clientY / window.innerHeight - 0.5) * 2;
  };

  constructor(inner: HTMLElement) {
    this.inner = inner;
  }

  init(preset: QualityPreset): void {
    this.preset = preset;
    const width = this.inner.clientWidth || window.innerWidth;
    const height = this.inner.clientHeight || window.innerHeight;

    const globe = new Globe(this.inner, {
      animateIn: false,
      waitForGlobeReady: false,
      rendererConfig: { antialias: preset.antialias, alpha: false, powerPreference: "high-performance" },
    });

    globe
      .width(width)
      .height(height)
      .backgroundColor(SPACE)
      .showGlobe(true)
      .showAtmosphere(true)
      .atmosphereColor(CYAN)
      .atmosphereAltitude(0.28)
      // US-outbound connections (cyan-themed replacement for airline routes):
      // every arc starts at a US hub and fans out internationally.
      .arcsData(buildOutboundArcs(preset.neuralNodes, preset.neuralLinks))
      .arcColor(() => [CYAN, BLUE])
      .arcStroke(0.5)
      .arcAltitude(() => 0.2 + Math.random() * 0.28)
      .arcDashLength(0.4)
      .arcDashGap(0.16)
      .arcDashInitialGap(() => Math.random())
      .arcDashAnimateTime(preset.arcDashAnimateTime)
      .arcsTransitionDuration(0)
      // glowing cyan origin dots at the US hubs
      .pointsData(US_HUBS)
      .pointColor(() => CYAN)
      .pointAltitude(0.01)
      .pointRadius(0.32)
      .pointResolution(6)
      .pointsMerge(true);

    const renderer = globe.renderer();
    renderer.setPixelRatio(preset.dpr);

    // camera + controls: slow auto-rotate, no user manipulation (canvas is
    // pointer-events:none anyway); damping for smooth motion.
    globe.pointOfView({ lat: 12, lng: 0, altitude: 2.6 });
    const controls = globe.controls();
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.enableRotate = false;
    controls.autoRotate = true;
    controls.autoRotateSpeed = preset.autoRotateSpeed;
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    this.globe = globe;
  }

  /** Start the render loop + parallax + auto-rotate. */
  start(): void {
    if (!this.globe || this.running) return;
    this.running = true;
    this.globe.resumeAnimation();
    window.addEventListener("pointermove", this.onPointerMove, { passive: true });
    this.tick();
  }

  /** Pause everything (window hidden/minimised). Cheap to resume. */
  stop(): void {
    this.running = false;
    if (this.rafId) cancelAnimationFrame(this.rafId);
    this.rafId = 0;
    window.removeEventListener("pointermove", this.onPointerMove);
    this.globe?.pauseAnimation();
  }

  private tick = (): void => {
    if (!this.running) return;
    // damped parallax on the wrapper (GPU transform, never touches the scene
    // graph so it can't fight OrbitControls; canvas is scaled to hide edges).
    this.eased.x += (this.pointer.x - this.eased.x) * 0.05;
    this.eased.y += (this.pointer.y - this.eased.y) * 0.05;
    this.inner.style.transform = `scale(1.06) translate3d(${(-this.eased.x * 12).toFixed(2)}px, ${(-this.eased.y * 12).toFixed(2)}px, 0)`;
    this.rafId = requestAnimationFrame(this.tick);
  };

  resize(): void {
    if (!this.globe) return;
    const width = this.inner.clientWidth || window.innerWidth;
    const height = this.inner.clientHeight || window.innerHeight;
    this.globe.width(width).height(height);
  }

  dispose(): void {
    this.stop();
    const globe = this.globe;
    this.globe = null;
    if (globe) {
      try {
        const renderer = globe.renderer();
        renderer.dispose();
        renderer.forceContextLoss();
      } catch {
        /* ignore */
      }
      // remove any canvas globe.gl attached
      while (this.inner.firstChild) this.inner.removeChild(this.inner.firstChild);
    }
    this.inner.style.transform = "";
  }
}

/* ============================================================================
   ENVIRONMENT ENGINE  (Phase E — cinematic AI universe)
   ----------------------------------------------------------------------------
   The single mount point for the environment. Owns the WebGL <Canvas>, feeds it
   the active quality preset, drives adaptive quality (drei PerformanceMonitor),
   pauses when hidden/blurred, honours reduced motion, applies filmic tone
   mapping for an HDR feel, and falls back silently if WebGL errors.

   Pages never import Three.js — they inherit this layer automatically.
   ========================================================================== */
import { Component, useEffect, useMemo, useRef, type ReactNode } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import { motion } from "framer-motion";
import * as THREE from "three";

import { ENV_CONFIG } from "./config";
import { EnvironmentContext } from "./context";
import { initAiActivity } from "./activity";
import { isWebGLAvailable } from "./components/PerformanceManager";
import { usePerformance } from "./hooks/usePerformance";
import { ActivityDriver } from "./components/ActivityDriver";
import { World } from "./components/World";
import { Stars } from "./components/Stars";
import { Nebula } from "./components/Nebula";
import { Particles } from "./components/Particles";
import { Debris } from "./components/Debris";
import { NeuralNetwork } from "./components/NeuralNetwork";
import { ShootingStars } from "./components/ShootingStars";
import { Lighting } from "./components/Lighting";
import { Fog } from "./components/Fog";
import { CameraController } from "./components/CameraController";
import { EnergyBeams } from "./components/EnergyBeams";
import { HexGrid } from "./components/HexGrid";

/** WebGL/render errors must never take down the app — fall back to CSS. */
class SafeBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    /* swallow — the CSS shell background is always present as a floor */
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

/** Filmic tone mapping + exposure for the cinematic HDR look. */
function SceneSetup() {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    gl.toneMapping = THREE.ACESFilmicToneMapping;
    gl.toneMappingExposure = ENV_CONFIG.lighting.exposure;
  }, [gl]);
  return null;
}

/** R3F can settle on its 300x150 default measure at mount; nudge until the
    buffer fills the fixed container, then stop. Self-terminating. */
function useCanvasSizeKick() {
  useEffect(() => {
    let tries = 0;
    const id = window.setInterval(() => {
      window.dispatchEvent(new Event("resize"));
      const canvas = document.querySelector<HTMLCanvasElement>(".nx-env canvas");
      tries += 1;
      if ((canvas && canvas.width > 400) || tries > 24) window.clearInterval(id);
    }, 140);
    return () => window.clearInterval(id);
  }, []);
}

export function EnvironmentEngine() {
  const { paused, reducedMotion, preset, adjustQuality } = usePerformance();
  const webgl = useMemo(() => isWebGLAvailable(), []);
  const ctx = useMemo(() => ({ preset, reducedMotion }), [preset, reducedMotion]);
  const declining = useRef(false);

  useCanvasSizeKick();

  // Wire the interaction bus → AI activity signal (once). Independent of the
  // render loop so it stays live even while the scene is paused.
  useEffect(() => initAiActivity(), []);

  if (!webgl) return null;

  const frameloop = paused ? "never" : reducedMotion ? "demand" : "always";

  return (
    <motion.div
      className="nx-env"
      aria-hidden="true"
      initial={{ opacity: 0 }}
      animate={{ opacity: ENV_CONFIG.presentation.opacity }}
      transition={{ duration: ENV_CONFIG.presentation.fadeInMs / 1000, ease: "easeOut" }}
    >
      <SafeBoundary>
        <Canvas
          frameloop={frameloop}
          dpr={preset.dpr}
          camera={{ position: ENV_CONFIG.camera.position, fov: ENV_CONFIG.camera.fov }}
          gl={{
            antialias: preset.antialias,
            alpha: true,
            powerPreference: "high-performance",
            failIfMajorPerformanceCaveat: false,
          }}
          style={{ width: "100%", height: "100%" }}
        >
          <EnvironmentContext.Provider value={ctx}>
            <SceneSetup />
            <ActivityDriver />
            <PerformanceMonitor
              onDecline={() => {
                if (!declining.current) {
                  declining.current = true;
                  adjustQuality(-1);
                }
              }}
              onIncline={() => {
                declining.current = false;
                adjustQuality(1);
              }}
            />
            <Fog />
            <Lighting />
            <CameraController />

            {/* Deep space (back to front) */}
            <Nebula />
            <HexGrid />
            <Stars />
            <ShootingStars />
            <Debris />
            <NeuralNetwork />
            <Particles />

            {/* The AI Core system */}
            <World />
            <EnergyBeams />
          </EnvironmentContext.Provider>
        </Canvas>
      </SafeBoundary>
    </motion.div>
  );
}

export default EnvironmentEngine;

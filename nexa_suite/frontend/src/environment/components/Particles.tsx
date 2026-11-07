/* Particles — floating "AI" motes drifting slowly through the foreground for
   depth. Additive, GPU-friendly single points buffer; count from quality. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { voiceLevel } from "../activity";

export function Particles() {
  const { particles } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const ref = useRef<THREE.Points>(null);
  const mat = useRef<THREE.PointsMaterial>(null);

  const positions = useMemo(() => {
    const arr = new Float32Array(preset.particleCount * 3);
    for (let i = 0; i < preset.particleCount; i += 1) {
      arr[i * 3] = (Math.random() - 0.5) * particles.spread;
      arr[i * 3 + 1] = (Math.random() - 0.5) * particles.spread * 0.7;
      arr[i * 3 + 2] = (Math.random() - 0.5) * particles.depth - 2;
    }
    return arr;
  }, [preset.particleCount, particles.spread, particles.depth]);

  useFrame((state, delta) => {
    if (reducedMotion || !ref.current) return;
    const d = Math.min(delta, 0.05);
    // Particles are the "voice" organ — they shimmer up while listening/speaking.
    const vo = voiceLevel();
    ref.current.rotation.y += d * particles.driftSpeed * (1 + vo * 0.8);
    ref.current.position.y = Math.sin(state.clock.elapsedTime * 0.06) * 0.3;
    if (mat.current) mat.current.opacity = particles.opacity * (1 + vo * 0.9);
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        ref={mat}
        color={ENV_PALETTE.particle}
        size={particles.size}
        transparent
        opacity={particles.opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

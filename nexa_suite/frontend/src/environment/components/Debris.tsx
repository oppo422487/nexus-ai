/* Debris — larger, slower cosmic motes drifting through the mid-depth for
   parallax and scale. Additive points; count from the quality preset. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { commandBurst } from "../activity";

export function Debris() {
  const { debris } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const ref = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const arr = new Float32Array(Math.max(preset.debrisCount, 1) * 3);
    for (let i = 0; i < preset.debrisCount; i += 1) {
      arr[i * 3] = (Math.random() - 0.5) * debris.spread;
      arr[i * 3 + 1] = (Math.random() - 0.5) * debris.spread * 0.7;
      arr[i * 3 + 2] = (Math.random() - 0.5) * debris.depth - 4;
    }
    return arr;
  }, [preset.debrisCount, debris.spread, debris.depth]);

  useFrame((state, delta) => {
    if (reducedMotion || !ref.current) return;
    // Debris scatters faster on a command burst.
    ref.current.rotation.y += Math.min(delta, 0.05) * debris.driftSpeed * (1 + commandBurst() * 2.5);
    ref.current.position.y = Math.sin(state.clock.elapsedTime * 0.04) * 0.4;
  });

  if (preset.debrisCount <= 0) return null;

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={ENV_PALETTE.debris}
        size={debris.size}
        transparent
        opacity={debris.opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

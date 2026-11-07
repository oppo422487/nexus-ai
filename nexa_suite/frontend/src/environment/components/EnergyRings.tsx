/* EnergyRings — holographic AI scan waves: thin rings that expand outward from
   the core and fade, on a continuous loop. Reads as circular pulse/scan waves.
   Additive, depth-write off; disabled under reduced motion. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { thinkingLevel, commandBurst } from "../activity";

export function EnergyRings() {
  const { energyRings } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const meshes = useRef<Array<THREE.Mesh | null>>([]);

  const phases = useMemo(
    () => Array.from({ length: energyRings.count }, (_, i) => (i / energyRings.count) * energyRings.period),
    [energyRings.count, energyRings.period],
  );

  useFrame((state) => {
    if (reducedMotion) return;
    const t = state.clock.elapsedTime;
    // Rings scan steadily with thinking; a bright fast ripple on command.
    const th = thinkingLevel();
    const cm = commandBurst();
    const period = energyRings.period / (1 + th * 0.9 + cm * 1.6);
    for (let i = 0; i < phases.length; i += 1) {
      const mesh = meshes.current[i];
      if (!mesh) continue;
      const progress = ((t + phases[i]) % period) / period;
      const radius = energyRings.startRadius + (energyRings.maxRadius - energyRings.startRadius) * progress;
      mesh.scale.setScalar(radius);
      const mat = mesh.material as THREE.MeshBasicMaterial;
      mat.opacity = (1 - progress) * energyRings.opacity * (1 + th * 0.5 + cm * 1.4);
    }
  });

  if (!preset.energyRingsEnabled) return null;

  return (
    <group position={energyRings.position} rotation={[energyRings.tilt, 0, 0]}>
      {phases.map((_, i) => (
        <mesh key={i} ref={(el) => { meshes.current[i] = el; }}>
          <ringGeometry args={[0.97, 1.0, 96]} />
          <meshBasicMaterial
            color={ENV_PALETTE.energyRing}
            transparent
            opacity={0}
            side={THREE.DoubleSide}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}

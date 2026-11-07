/* Moon — a small, softly lit companion body drifting on a slow, wide orbit.
   Disabled on the low quality tier. */
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";

export function Moon() {
  const { moon } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const group = useRef<THREE.Group>(null);
  const body = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (reducedMotion) return;
    const d = Math.min(delta, 0.05);
    if (group.current) group.current.rotation.y += d * moon.orbitSpeed;
    if (body.current) body.current.rotation.y += d * moon.rotationSpeed * 10;
    // subtle bob for parallax depth
    if (group.current) group.current.position.y = Math.sin(state.clock.elapsedTime * 0.1) * 0.2;
  });

  if (!preset.moonEnabled) return null;

  return (
    <group ref={group}>
      <mesh ref={body} position={moon.position}>
        <sphereGeometry args={[moon.radius, 32, 32]} />
        <meshStandardMaterial
          color={ENV_PALETTE.moon}
          emissive={ENV_PALETTE.ambient}
          emissiveIntensity={0.15}
          roughness={0.95}
          metalness={0.05}
        />
      </mesh>
    </group>
  );
}

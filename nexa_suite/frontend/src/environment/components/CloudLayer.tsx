/* CloudLayer — a faint additive shell that rotates slightly faster than the
   globe, suggesting drifting cloud cover without heavy textures. Disabled on
   the low quality tier. */
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";

export function CloudLayer() {
  const { earth, clouds } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const mesh = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (reducedMotion || !mesh.current) return;
    mesh.current.rotation.y += Math.min(delta, 0.05) * clouds.rotationSpeed * 10;
  });

  if (!preset.cloudsEnabled) return null;

  return (
    <mesh ref={mesh} position={earth.position} rotation={[earth.tilt, 0, 0]} scale={clouds.scale}>
      <sphereGeometry args={[earth.radius, preset.earthSegments, preset.earthSegments]} />
      <meshBasicMaterial
        color={ENV_PALETTE.cloud}
        transparent
        opacity={clouds.opacity}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  );
}

/* Nebula — soft additive colour clouds far behind the scene, giving the space a
   living, volumetric depth. Each layer is a large billboard with a soft radial
   shader; they drift very slowly. Disabled below the medium tier. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";

const VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAG = /* glsl */ `
  varying vec2 vUv;
  uniform vec3 uColor;
  uniform float uOpacity;
  void main() {
    vec2 p = vUv - 0.5;
    float soft = smoothstep(0.5, 0.0, length(p));
    float lobeA = smoothstep(0.34, 0.0, length(p - vec2(0.13, 0.08)));
    float lobeB = smoothstep(0.40, 0.0, length(p + vec2(0.10, 0.13)));
    float a = (soft * 0.6 + lobeA * 0.25 + lobeB * 0.22) * uOpacity;
    gl_FragColor = vec4(uColor, a);
  }
`;

export function Nebula() {
  const { nebula } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const group = useRef<THREE.Group>(null);

  const layers = useMemo(
    () =>
      nebula.layers.map((l) => ({
        ...l,
        material: new THREE.ShaderMaterial({
          uniforms: {
            uColor: { value: new THREE.Color((ENV_PALETTE as unknown as Record<string, string>)[l.color] ?? ENV_PALETTE.nebulaA) },
            uOpacity: { value: l.opacity },
          },
          vertexShader: VERT,
          fragmentShader: FRAG,
          transparent: true,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          depthTest: false,
        }),
      })),
    [nebula.layers],
  );

  useFrame((_, delta) => {
    if (reducedMotion || !group.current) return;
    const d = Math.min(delta, 0.05);
    group.current.children.forEach((child, i) => {
      child.rotation.z += d * (layers[i]?.drift ?? 0);
    });
  });

  if (!preset.nebulaEnabled) return null;

  return (
    <group ref={group}>
      {layers.map((l, i) => (
        <mesh key={i} position={l.pos} material={l.material}>
          <planeGeometry args={[l.scale, l.scale]} />
        </mesh>
      ))}
    </group>
  );
}

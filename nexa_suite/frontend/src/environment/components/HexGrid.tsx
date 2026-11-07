/* HexGrid — a large holographic scanning grid far behind the scene (a TRON/
   JARVIS "floor"). Shader-drawn glowing lines with a sweeping scan band and a
   radial fade so it dissolves at the edges. Additive; scan accelerates + glows
   with AI activity. Static under reduced motion. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { activityLevel } from "../activity";

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
  uniform float uTime;
  uniform float uOpacity;
  uniform float uCells;
  uniform float uLineWidth;
  uniform float uScanSpeed;
  uniform float uActivity;
  void main() {
    vec2 g = fract(vUv * uCells);
    float gx = max(smoothstep(uLineWidth, 0.0, g.x), smoothstep(1.0 - uLineWidth, 1.0, g.x));
    float gy = max(smoothstep(uLineWidth, 0.0, g.y), smoothstep(1.0 - uLineWidth, 1.0, g.y));
    float grid = max(gx, gy);
    float scan = smoothstep(0.04, 0.0, abs(fract(vUv.y - uTime * uScanSpeed) - 0.5) - 0.02);
    float fade = smoothstep(0.62, 0.0, length(vUv - 0.5));
    float a = (grid * (0.45 + uActivity * 0.4) + scan * (0.8 + uActivity)) * uOpacity * fade;
    gl_FragColor = vec4(uColor + uColor * scan, a);
  }
`;

export function HexGrid() {
  const { hexGrid } = ENV_CONFIG;
  const { reducedMotion } = useEnvironment();
  const mat = useRef<THREE.ShaderMaterial>(null);

  const uniforms = useMemo(
    () => ({
      uColor: { value: new THREE.Color(ENV_PALETTE.energyRing) },
      uTime: { value: 0 },
      uOpacity: { value: hexGrid.opacity },
      uCells: { value: hexGrid.cell },
      uLineWidth: { value: hexGrid.lineWidth },
      uScanSpeed: { value: hexGrid.scanSpeed },
      uActivity: { value: 0 },
    }),
    [hexGrid.opacity, hexGrid.cell, hexGrid.lineWidth, hexGrid.scanSpeed],
  );

  useFrame((state) => {
    if (reducedMotion || !mat.current) return;
    const act = activityLevel();
    mat.current.uniforms.uTime.value = state.clock.elapsedTime;
    mat.current.uniforms.uActivity.value = act;
    mat.current.uniforms.uScanSpeed.value = hexGrid.scanSpeed * (1 + act);
  });

  return (
    <mesh position={hexGrid.position} rotation={hexGrid.rotation}>
      <planeGeometry args={[hexGrid.size, hexGrid.size]} />
      <shaderMaterial
        ref={mat}
        uniforms={uniforms}
        vertexShader={VERT}
        fragmentShader={FRAG}
        transparent
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

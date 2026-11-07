/* Atmosphere — a two-layer fresnel halo around the core: a tight inner rim and
   a broad outer bloom-like glow. Additive, back-side, depth-write off. Gives the
   AI Core a volumetric, HDR-ish atmosphere without post-processing. */
import { useMemo } from "react";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";

const VERT = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

const FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uPower;
  uniform float uIntensity;
  uniform float uOpacity;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float fres = pow(1.0 - abs(dot(vNormal, vView)), uPower);
    float a = clamp(fres * uIntensity, 0.0, 1.0) * uOpacity;
    gl_FragColor = vec4(uColor * fres * uIntensity, a);
  }
`;

function makeMaterial(color: string, power: number, intensity: number, opacity: number) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(color) },
      uPower: { value: power },
      uIntensity: { value: intensity },
      uOpacity: { value: opacity },
    },
    vertexShader: VERT,
    fragmentShader: FRAG,
    transparent: true,
    blending: THREE.AdditiveBlending,
    side: THREE.BackSide,
    depthWrite: false,
  });
}

export function Atmosphere() {
  const { earth, atmosphere } = ENV_CONFIG;

  const inner = useMemo(
    () => makeMaterial(ENV_PALETTE.atmosphereGlow, atmosphere.power, atmosphere.intensity, atmosphere.opacity),
    [atmosphere.power, atmosphere.intensity, atmosphere.opacity],
  );
  const outer = useMemo(
    () => makeMaterial(ENV_PALETTE.atmosphere, atmosphere.power * 0.6, atmosphere.intensity * 0.6, atmosphere.opacity * 0.6),
    [atmosphere.power, atmosphere.intensity, atmosphere.opacity],
  );

  return (
    <group position={earth.position}>
      <mesh scale={atmosphere.innerScale} material={inner}>
        <sphereGeometry args={[earth.radius, 48, 48]} />
      </mesh>
      <mesh scale={atmosphere.outerScale} material={outer}>
        <sphereGeometry args={[earth.radius, 48, 48]} />
      </mesh>
    </group>
  );
}

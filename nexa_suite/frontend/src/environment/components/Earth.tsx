/* Earth — the holographic AI Core. A shader sphere (fresnel rim + animated
   lat/long grid + vertical scan sweep, additive) wrapped in a glowing fibonacci
   point shell. No texture assets; reads as a JARVIS-style energy globe. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { activityLevel, commandBurst } from "../activity";

function fibonacciSphere(count: number, radius: number): Float32Array {
  const arr = new Float32Array(count * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i += 1) {
    const y = 1 - (i / Math.max(count - 1, 1)) * 2;
    const r = Math.sqrt(Math.max(1 - y * y, 0));
    const theta = golden * i;
    arr[i * 3] = Math.cos(theta) * r * radius;
    arr[i * 3 + 1] = y * radius;
    arr[i * 3 + 2] = Math.sin(theta) * r * radius;
  }
  return arr;
}

const VERT = /* glsl */ `
  uniform float uTime;
  uniform float uDistort;
  uniform float uActivity;
  varying vec3 vNormal;
  varying vec3 vView;
  varying vec3 vPos;

  // cheap layered trig noise — enough for an organic holographic ripple
  float ripple(vec3 p, float t) {
    float n = sin(p.x * 3.0 + t * 0.9) * sin(p.y * 3.4 - t * 0.7) * sin(p.z * 3.2 + t * 0.8);
    n += 0.5 * sin(p.y * 6.0 + t * 1.3) * sin(p.x * 5.0 - t * 1.1);
    return n;
  }

  void main() {
    vPos = normalize(position);
    float amp = uDistort * (1.0 + uActivity * 1.4);
    float disp = ripple(vPos, uTime) * amp;
    vec3 displaced = position + normal * disp;

    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(displaced, 1.0);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

const FRAG = /* glsl */ `
  uniform float uTime;
  uniform vec3 uColor;
  uniform vec3 uGlow;
  uniform float uFresnelPower;
  uniform float uFresnelIntensity;
  uniform float uOpacity;
  uniform float uScanSpeed;
  uniform float uActivity;
  uniform float uPulse;
  uniform float uCommand;
  varying vec3 vNormal;
  varying vec3 vView;
  varying vec3 vPos;
  void main() {
    float act = uActivity;
    float pulse = 0.9 + 0.18 * uPulse;
    float fres = pow(1.0 - abs(dot(vNormal, vView)), uFresnelPower);
    float lat = asin(clamp(vPos.y, -1.0, 1.0));
    float lon = atan(vPos.x, vPos.z) + uTime * (0.15 + act * 0.2);
    float latLines = smoothstep(0.86, 1.0, abs(sin(lat * 18.0)));
    float lonLines = smoothstep(0.86, 1.0, abs(sin(lon * 18.0)));
    float grid = max(latLines, lonLines);
    float scan = smoothstep(0.04, 0.0, abs(fract(vPos.y * 0.5 - uTime * (uScanSpeed + act * 0.5)) - 0.5) - 0.02);
    vec3 col = (mix(uColor, uGlow, fres) + uGlow * (grid * (0.6 + act * 0.5) + scan * (0.9 + act * 0.7))) * pulse;
    float alpha = clamp(0.12 + grid * 0.4 + fres * uFresnelIntensity * (1.0 + act * 0.35) + scan * 0.5, 0.0, 1.0) * uOpacity * (1.0 + act * 0.18) * pulse;
    // command flash — a warm-white confirmation surge
    col = mix(col, vec3(1.0, 0.96, 0.86), uCommand * 0.6);
    alpha = clamp(alpha + uCommand * 0.28, 0.0, 1.0);
    gl_FragColor = vec4(col, alpha);
  }
`;

export function Earth() {
  const { earth } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const group = useRef<THREE.Group>(null);
  const mat = useRef<THREE.ShaderMaterial>(null);

  const points = useMemo(
    () => fibonacciSphere(preset.earthPoints, earth.radius * 1.01),
    [preset.earthPoints, earth.radius],
  );

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor: { value: new THREE.Color(ENV_PALETTE.earthCore) },
      uGlow: { value: new THREE.Color(ENV_PALETTE.coreGlow) },
      uFresnelPower: { value: earth.fresnelPower },
      uFresnelIntensity: { value: earth.fresnelIntensity },
      uOpacity: { value: earth.coreOpacity + 0.35 },
      uScanSpeed: { value: earth.scanSpeed },
      uActivity: { value: 0 },
      uPulse: { value: 0 },
      uCommand: { value: 0 },
      uDistort: { value: earth.distort },
    }),
    [earth.fresnelPower, earth.fresnelIntensity, earth.coreOpacity, earth.scanSpeed, earth.distort],
  );

  useFrame((state, delta) => {
    if (reducedMotion) {
      if (mat.current) mat.current.uniforms.uTime.value = 0;
      return;
    }
    const d = Math.min(delta, 0.05);
    const act = activityLevel();
    if (group.current) group.current.rotation.y += d * earth.rotationSpeed * 10 * (1 + act * 0.7);
    if (mat.current) {
      mat.current.uniforms.uTime.value = state.clock.elapsedTime;
      mat.current.uniforms.uActivity.value = act;
      mat.current.uniforms.uPulse.value = 0.5 + 0.5 * Math.sin(state.clock.elapsedTime * ENV_CONFIG.core.pulseSpeed);
      mat.current.uniforms.uCommand.value = commandBurst();
    }
  });

  return (
    <group ref={group} position={earth.position} rotation={[earth.tilt, 0, 0]}>
      <mesh>
        <sphereGeometry args={[earth.radius, preset.earthSegments, preset.earthSegments]} />
        <shaderMaterial
          ref={mat}
          uniforms={uniforms}
          vertexShader={VERT}
          fragmentShader={FRAG}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[points, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color={ENV_PALETTE.earthGrid}
          size={earth.pointSize}
          transparent
          opacity={earth.gridOpacity}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  );
}

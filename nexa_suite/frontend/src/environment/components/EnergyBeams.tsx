/* EnergyBeams — the Core's power lines. Each beam is a curved additive line
   fading out from the Earth toward a UI region, with bright packets streaming
   outward along it. GPU-only (WebGL), no SVG, pointer-events already disabled by
   the canvas. Count scales by quality tier; speed/brightness scale with AI
   activity so the whole OS visibly draws power from the Core. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { activityLevel, thinkingLevel, commandBurst } from "../activity";

const PACKETS_PER_BEAM = 2;

const VERT = /* glsl */ `
  attribute float aProgress;
  varying float vP;
  void main() {
    vP = aProgress;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uOpacity;
  uniform float uActivity;
  varying float vP;
  void main() {
    float fade = pow(1.0 - vP, 1.5);            // brightest at the Core end
    float a = uOpacity * fade * (0.7 + uActivity * 0.9);
    gl_FragColor = vec4(uColor, a);
  }
`;

interface Beam {
  line: THREE.Line;
  curve: THREE.QuadraticBezierCurve3;
  material: THREE.ShaderMaterial;
}

export function EnergyBeams() {
  const { earth, beams: cfg } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const packetsRef = useRef<THREE.Points>(null);

  const beams = useMemo<Beam[]>(() => {
    const P0 = new THREE.Vector3(...earth.position);
    const list: Beam[] = [];
    for (let i = 0; i < preset.energyBeams; i += 1) {
      const target = cfg.targets[i % cfg.targets.length];
      const P2 = new THREE.Vector3(...target);
      const dir = P2.clone().sub(P0).normalize();
      const perp = new THREE.Vector3(-dir.y, dir.x, 0).multiplyScalar(cfg.curveLift * (i % 2 === 0 ? 1 : -1));
      const P1 = P0.clone().lerp(P2, 0.5).add(perp).add(new THREE.Vector3(0, 0, 0.4));
      const curve = new THREE.QuadraticBezierCurve3(P0, P1, P2);

      const pts = curve.getPoints(cfg.samples);
      const positions = new Float32Array(pts.length * 3);
      const progress = new Float32Array(pts.length);
      pts.forEach((p, j) => {
        positions[j * 3] = p.x;
        positions[j * 3 + 1] = p.y;
        positions[j * 3 + 2] = p.z;
        progress[j] = j / (pts.length - 1);
      });
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geo.setAttribute("aProgress", new THREE.BufferAttribute(progress, 1));

      const material = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: new THREE.Color(ENV_PALETTE.coreGlow) },
          uOpacity: { value: cfg.opacity },
          uActivity: { value: 0 },
        },
        vertexShader: VERT,
        fragmentShader: FRAG,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      list.push({ line: new THREE.Line(geo, material), curve, material });
    }
    return list;
  }, [preset.energyBeams, earth.position, cfg.targets, cfg.samples, cfg.opacity, cfg.curveLift]);

  const packets = useMemo(
    () =>
      beams.flatMap((b, bi) =>
        Array.from({ length: PACKETS_PER_BEAM }, (_, k) => ({
          curve: b.curve,
          phase: (k / PACKETS_PER_BEAM + bi * 0.13) % 1,
          speed: 0.7 + Math.random() * 0.6,
        })),
      ),
    [beams],
  );
  const packetPositions = useMemo(() => new Float32Array(Math.max(packets.length, 1) * 3), [packets.length]);

  useFrame((state) => {
    if (reducedMotion) return;
    // Beams are the "power lines" — brighten with activity, BURST on command.
    const act = activityLevel();
    const cm = commandBurst();
    for (const b of beams) b.material.uniforms.uActivity.value = act + cm * 0.8;

    if (packetsRef.current && packets.length) {
      const attr = packetsRef.current.geometry.getAttribute("position") as THREE.BufferAttribute;
      const t = state.clock.elapsedTime;
      const speedMul = cfg.packetSpeed * (1 + thinkingLevel() * 1.2 + cm * 3.2);
      const p = new THREE.Vector3();
      for (let i = 0; i < packets.length; i += 1) {
        const f = (packets[i].phase + t * packets[i].speed * speedMul) % 1;
        packets[i].curve.getPoint(f, p);
        attr.setXYZ(i, p.x, p.y, p.z);
      }
      attr.needsUpdate = true;
    }
  });

  if (preset.energyBeams <= 0) return null;

  return (
    <group>
      {beams.map((b, i) => (
        <primitive key={i} object={b.line} />
      ))}
      <points ref={packetsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[packetPositions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          color={ENV_PALETTE.satellitePacket}
          size={0.07}
          transparent
          opacity={0.9}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  );
}

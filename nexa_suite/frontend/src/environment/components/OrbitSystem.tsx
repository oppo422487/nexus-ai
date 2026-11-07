/* OrbitSystem — orbit rings around the AI Core with communication satellites and
   bright data packets travelling along them. Ring geometry is precomputed; each
   orbiter is a small pivot rotated in useFrame. Counts come from the quality
   preset (disabled entirely on the low tier). */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { thinkingLevel, commandBurst } from "../activity";

type Orbiter = {
  ringIndex: number;
  angle: number;
  speed: number;
  size: number;
  color: string;
};

function ringGeometry(radius: number): THREE.BufferGeometry {
  const curve = new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0);
  const pts = curve.getPoints(120).map((p) => new THREE.Vector3(p.x, 0, p.y));
  return new THREE.BufferGeometry().setFromPoints(pts);
}

export function OrbitSystem() {
  const { earth, orbit } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const pivots = useRef<Array<THREE.Group | null>>([]);

  const rings = orbit.rings;
  const ringGeoms = useMemo(() => rings.map((r) => ringGeometry(r.radius)), [rings]);

  const orbiters = useMemo(() => {
    const list: Orbiter[] = [];
    for (let i = 0; i < preset.commSatellites; i += 1) {
      const ringIndex = i % rings.length;
      list.push({ ringIndex, angle: Math.random() * Math.PI * 2, speed: rings[ringIndex].speed, size: orbit.satSize, color: ENV_PALETTE.satellite });
    }
    for (let i = 0; i < preset.dataPackets; i += 1) {
      const ringIndex = i % rings.length;
      list.push({
        ringIndex,
        angle: Math.random() * Math.PI * 2,
        speed: orbit.packetSpeed * (0.7 + Math.random() * 0.6),
        size: orbit.packetSize,
        color: ENV_PALETTE.satellitePacket,
      });
    }
    return list;
  }, [preset.commSatellites, preset.dataPackets, rings, orbit.satSize, orbit.packetSize, orbit.packetSpeed]);

  useFrame((_, delta) => {
    if (reducedMotion) return;
    const d = Math.min(delta, 0.05);
    // Orbit accelerates gently with thinking, surges on command.
    const mul = 1 + thinkingLevel() * 0.9 + commandBurst() * 2.6;
    for (let i = 0; i < orbiters.length; i += 1) {
      const pivot = pivots.current[i];
      if (pivot) pivot.rotation.y += d * orbiters[i].speed * mul;
    }
  });

  return (
    <group position={earth.position}>
      {preset.orbitRingsEnabled &&
        rings.map((r, i) => (
          <lineLoop key={`ring-${i}`} geometry={ringGeoms[i]} rotation={[r.inclination, 0, r.tilt]}>
            <lineBasicMaterial
              color={ENV_PALETTE.ring}
              transparent
              opacity={r.opacity}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </lineLoop>
        ))}

      {orbiters.map((o, i) => {
        const r = rings[o.ringIndex];
        return (
          <group key={`orb-${i}`} rotation={[r.inclination, 0, r.tilt]}>
            <group ref={(el) => { pivots.current[i] = el; }} rotation={[0, o.angle, 0]}>
              <mesh position={[r.radius, 0, 0]}>
                <sphereGeometry args={[o.size, 10, 10]} />
                <meshBasicMaterial color={o.color} />
              </mesh>
            </group>
          </group>
        );
      })}
    </group>
  );
}

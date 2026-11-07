/* ShootingStars — occasional streaks crossing deep space. A small fixed pool of
   line segments; each streak spawns at a random point, travels, then respawns
   after a randomised delay. Cheap (a handful of segments). Reduced-motion off. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";

const POOL = 5;

type Streak = { pos: THREE.Vector3; vel: THREE.Vector3; life: number; next: number };

export function ShootingStars() {
  const { shootingStars: cfg } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const lineRef = useRef<THREE.LineSegments>(null);

  const positions = useMemo(() => new Float32Array(POOL * 2 * 3), []);
  const streaks = useMemo<Streak[]>(
    () =>
      Array.from({ length: POOL }, () => ({
        pos: new THREE.Vector3(),
        vel: new THREE.Vector3(),
        life: 0,
        next: Math.random() * cfg.interval * 2,
      })),
    [cfg.interval],
  );

  const spawn = (s: Streak) => {
    const [dMin, dMax] = cfg.depth;
    s.pos.set((Math.random() - 0.5) * cfg.spread, (Math.random() - 0.4) * cfg.spread * 0.6, dMin + Math.random() * (dMax - dMin));
    s.vel.set(-(0.5 + Math.random()), -(0.2 + Math.random() * 0.4), 0.1 * (Math.random() - 0.5)).normalize().multiplyScalar(cfg.speed);
    s.life = 0.6 + Math.random() * 0.5;
  };

  useFrame((_, delta) => {
    if (reducedMotion || !lineRef.current) return;
    const d = Math.min(delta, 0.05);
    const attr = lineRef.current.geometry.getAttribute("position") as THREE.BufferAttribute;
    for (let i = 0; i < POOL; i += 1) {
      const s = streaks[i];
      if (s.life > 0) {
        s.pos.addScaledVector(s.vel, d);
        s.life -= d;
        const tailX = s.pos.x - (s.vel.x / cfg.speed) * cfg.length;
        const tailY = s.pos.y - (s.vel.y / cfg.speed) * cfg.length;
        const tailZ = s.pos.z - (s.vel.z / cfg.speed) * cfg.length;
        attr.setXYZ(i * 2, s.pos.x, s.pos.y, s.pos.z);
        attr.setXYZ(i * 2 + 1, tailX, tailY, tailZ);
      } else {
        s.next -= d;
        if (s.next <= 0) {
          spawn(s);
          s.next = cfg.interval * (0.5 + Math.random() * 1.5);
        } else {
          // collapse segment (invisible)
          attr.setXYZ(i * 2, 0, 0, 9999);
          attr.setXYZ(i * 2 + 1, 0, 0, 9999);
        }
      }
    }
    attr.needsUpdate = true;
  });

  if (!preset.shootingStarsEnabled) return null;

  return (
    <lineSegments ref={lineRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={ENV_PALETTE.shootingStar}
        transparent
        opacity={0.85}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  );
}

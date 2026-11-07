/* NeuralNetwork — a huge, deep AI graph behind the whole scene: thousands of
   nodes, links between neighbours, and energy packets travelling along the
   links. Links are built with a bounded windowed scan so it stays cheap even at
   thousands of nodes. Purely additive; drifts very slowly for an infinite feel. */
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { thinkingLevel, commandBurst, voiceLevel } from "../activity";

export function NeuralNetwork() {
  const { neural } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();
  const group = useRef<THREE.Group>(null);
  const packetsRef = useRef<THREE.Points>(null);
  const nodeMat = useRef<THREE.PointsMaterial>(null);

  const { nodes, links, packetLinks } = useMemo(() => {
    const count = preset.neuralNodes;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i < count; i += 1) {
      pts.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * neural.spread,
          (Math.random() - 0.5) * neural.spread * 0.6,
          (Math.random() - 0.5) * neural.spread * 0.5 + neural.depthBack,
        ),
      );
    }
    const nodePos = new Float32Array(count * 3);
    pts.forEach((p, i) => {
      nodePos[i * 3] = p.x;
      nodePos[i * 3 + 1] = p.y;
      nodePos[i * 3 + 2] = p.z;
    });

    // Windowed neighbour scan — O(n * window), not O(n^2).
    const segs: number[] = [];
    const edges: Array<[THREE.Vector3, THREE.Vector3]> = [];
    const linkCount = new Array(count).fill(0);
    const window = 46;
    for (let i = 0; i < count; i += 1) {
      for (let j = i + 1; j < Math.min(i + window, count); j += 1) {
        if (linkCount[i] >= preset.neuralMaxLinks) break;
        if (linkCount[j] >= preset.neuralMaxLinks) continue;
        if (pts[i].distanceTo(pts[j]) <= neural.linkDistance) {
          segs.push(pts[i].x, pts[i].y, pts[i].z, pts[j].x, pts[j].y, pts[j].z);
          edges.push([pts[i], pts[j]]);
          linkCount[i] += 1;
          linkCount[j] += 1;
        }
      }
    }

    // Pick a subset of edges to carry travelling packets.
    const packetLinks: Array<{ a: THREE.Vector3; b: THREE.Vector3; phase: number; speed: number }> = [];
    for (let k = 0; k < preset.neuralPackets && edges.length > 0; k += 1) {
      const e = edges[Math.floor(Math.random() * edges.length)];
      packetLinks.push({ a: e[0], b: e[1], phase: Math.random(), speed: 0.5 + Math.random() });
    }

    return { nodes: nodePos, links: new Float32Array(segs), packetLinks };
  }, [preset.neuralNodes, preset.neuralMaxLinks, preset.neuralPackets, neural.spread, neural.linkDistance, neural.depthBack]);

  const packetPositions = useMemo(() => new Float32Array(Math.max(packetLinks.length, 1) * 3), [packetLinks.length]);

  useFrame((state, delta) => {
    if (reducedMotion) return;
    const t = state.clock.elapsedTime;
    // Neural graph is the "thinking" organ — it leads on thinking, spikes on command.
    const th = thinkingLevel();
    const cm = commandBurst();
    const vo = voiceLevel();
    if (group.current) group.current.rotation.y += Math.min(delta, 0.05) * neural.driftSpeed * (1 + th + vo * 0.4);
    if (nodeMat.current) nodeMat.current.opacity = neural.nodeOpacity * (1 + th * 0.7 + cm * 0.5);

    if (packetsRef.current && packetLinks.length) {
      const attr = packetsRef.current.geometry.getAttribute("position") as THREE.BufferAttribute;
      const speedMul = neural.packetSpeed * (1 + th * 1.5 + cm * 2.2 + vo * 0.6);
      for (let i = 0; i < packetLinks.length; i += 1) {
        const p = packetLinks[i];
        const f = (p.phase + t * p.speed * speedMul) % 1;
        attr.setXYZ(i, p.a.x + (p.b.x - p.a.x) * f, p.a.y + (p.b.y - p.a.y) * f, p.a.z + (p.b.z - p.a.z) * f);
      }
      attr.needsUpdate = true;
    }
  });

  return (
    <group ref={group}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[nodes, 3]} />
        </bufferGeometry>
        <pointsMaterial
          ref={nodeMat}
          color={ENV_PALETTE.neuralNode}
          size={neural.nodeSize}
          transparent
          opacity={neural.nodeOpacity}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {links.length > 0 && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[links, 3]} />
          </bufferGeometry>
          <lineBasicMaterial
            color={ENV_PALETTE.neuralLink}
            transparent
            opacity={neural.linkOpacity}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </lineSegments>
      )}

      {packetLinks.length > 0 && (
        <points ref={packetsRef}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[packetPositions, 3]} />
          </bufferGeometry>
          <pointsMaterial
            color={ENV_PALETTE.neuralPacket}
            size={neural.packetSize}
            transparent
            opacity={0.95}
            sizeAttenuation
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </points>
      )}
    </group>
  );
}

/* CameraController — the camera never sits perfectly still. It drifts a fraction
   toward the pointer (parallax), sways autonomously (idle breathing), and eases
   in/out along Z (depth breathing). All lerped for smoothness; static under
   reduced motion. Subtle by design — no motion sickness. */
import { useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG } from "../config";
import { useEnvironment } from "../context";
import { activityLevel, commandBurst } from "../activity";

export function CameraController() {
  const { camera: cam } = ENV_CONFIG;
  const { reducedMotion } = useEnvironment();
  const camera = useThree((s) => s.camera);
  const target = useRef(new THREE.Vector3(...cam.position));

  useFrame((state) => {
    if (reducedMotion) return;
    const t = state.clock.elapsedTime;
    const act = activityLevel();
    const cm = commandBurst();

    const idleX = Math.sin(t * cam.idleDriftSpeed) * cam.idleDriftStrength;
    const idleY = Math.cos(t * cam.idleDriftSpeed * 0.8) * cam.idleDriftStrength * 0.6;
    const breatheZ = Math.sin(t * cam.breatheSpeed * (1 + act * 0.4)) * cam.breatheAmp * (1 + act * 0.3);
    const pushIn = cm * 0.5; // gentle dolly-in on command confirmation

    const px = state.pointer.x * cam.parallaxStrength + idleX;
    const py = state.pointer.y * cam.parallaxStrength * 0.6 + idleY;

    target.current.set(cam.position[0] + px, cam.position[1] + py, cam.position[2] + breatheZ - pushIn);
    camera.position.lerp(target.current, cam.parallaxDamping);
    // micro focus shift toward the Core on command
    camera.lookAt(cm * 0.5, -cm * 0.35, 0);
  });

  return null;
}

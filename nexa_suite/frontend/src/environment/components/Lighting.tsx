/* Lighting — cinematic 3-point setup that shifts with the AI mode:
     • thinking → cool cyan rim emphasis
     • command  → warm-white key flash (confirmation)
     • voice    → blue back-light breathing
     • idle     → balanced
   Colours/intensities are lerped every frame from the activity channels (never
   over-exposed). Static base under reduced motion. */
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { ENV_CONFIG, ENV_PALETTE } from "../config";
import { useEnvironment } from "../context";
import { thinkingLevel, commandBurst, voiceLevel } from "../activity";

export function Lighting() {
  const { lighting } = ENV_CONFIG;
  const { reducedMotion } = useEnvironment();
  const key = useRef<THREE.DirectionalLight>(null);
  const rim = useRef<THREE.PointLight>(null);
  const back = useRef<THREE.PointLight>(null);

  const cols = useRef({
    keyBase: new THREE.Color(ENV_PALETTE.keyLight),
    keyWarm: new THREE.Color("#fff1da"),
    rimBase: new THREE.Color(ENV_PALETTE.rimLight),
    rimCyan: new THREE.Color(ENV_PALETTE.coreGlow),
    backBase: new THREE.Color(ENV_PALETTE.backLight),
    backBlue: new THREE.Color("#3f6bff"),
  });

  useFrame((state, delta) => {
    if (reducedMotion) return;
    const d = Math.min(delta, 0.05);
    const th = thinkingLevel();
    const cm = commandBurst();
    const vo = voiceLevel();
    const co = cols.current;

    if (key.current) {
      const target = lighting.keyIntensity * (1 + cm * 0.9);
      key.current.intensity += (target - key.current.intensity) * Math.min(1, d * 4);
      key.current.color.lerp(cm > 0.06 ? co.keyWarm : co.keyBase, Math.min(1, d * 3));
    }
    if (rim.current) {
      const target = lighting.rimIntensity * (1 + th * 0.9 + vo * 0.4);
      rim.current.intensity += (target - rim.current.intensity) * Math.min(1, d * 3);
      rim.current.color.lerp(th > 0.06 ? co.rimCyan : co.rimBase, Math.min(1, d * 3));
    }
    if (back.current) {
      const breathe = 0.6 + 0.4 * Math.sin(state.clock.elapsedTime * 0.8);
      const target = lighting.backIntensity * (1 + vo * (0.4 + breathe * 0.6));
      back.current.intensity += (target - back.current.intensity) * Math.min(1, d * 3);
      back.current.color.lerp(vo > 0.06 ? co.backBlue : co.backBase, Math.min(1, d * 3));
    }
  });

  return (
    <>
      <ambientLight color={ENV_PALETTE.ambient} intensity={lighting.ambientIntensity} />
      <directionalLight ref={key} color={ENV_PALETTE.keyLight} intensity={lighting.keyIntensity} position={lighting.keyPosition} />
      <pointLight ref={rim} color={ENV_PALETTE.rimLight} intensity={lighting.rimIntensity} position={lighting.rimPosition} distance={45} />
      <pointLight ref={back} color={ENV_PALETTE.backLight} intensity={lighting.backIntensity} position={lighting.backPosition} distance={45} />
    </>
  );
}

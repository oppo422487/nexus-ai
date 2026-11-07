/* Fog — depth cue for the scene. Applies THREE.Fog to the scene via R3F's
   declarative <fog> element; colour/near/far from config. */
import { ENV_CONFIG, ENV_PALETTE } from "../config";

export function Fog() {
  const { fog } = ENV_CONFIG;
  return <fog attach="fog" args={[ENV_PALETTE.fog, fog.near, fog.far]} />;
}

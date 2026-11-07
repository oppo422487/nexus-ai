/* World — composes the celestial bodies around the AI Core: the holographic
   Earth, its atmosphere halo and cloud shell, the moon, the orbit system
   (rings + comm satellites + data packets), and the energy scan rings. Each
   child positions itself from config, so World is a pure composition unit. */
import { Atmosphere } from "./Atmosphere";
import { CloudLayer } from "./CloudLayer";
import { Earth } from "./Earth";
import { Moon } from "./Moon";
import { OrbitSystem } from "./OrbitSystem";
import { EnergyRings } from "./EnergyRings";

export function World() {
  return (
    <group>
      <Earth />
      <Atmosphere />
      <CloudLayer />
      <EnergyRings />
      <OrbitSystem />
      <Moon />
    </group>
  );
}

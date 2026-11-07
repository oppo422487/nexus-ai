/* Stars — the dynamic star field. Uses drei's Stars for a well-optimised,
   fading point field; count and motion come from config/quality preset. */
import { Stars as DreiStars } from "@react-three/drei";
import { ENV_CONFIG } from "../config";
import { useEnvironment } from "../context";

export function Stars() {
  const { stars } = ENV_CONFIG;
  const { preset, reducedMotion } = useEnvironment();

  return (
    <DreiStars
      radius={stars.radius}
      depth={stars.depth}
      count={preset.starCount}
      factor={stars.factor}
      saturation={stars.saturation}
      fade={stars.fade}
      speed={reducedMotion ? 0 : stars.speed}
    />
  );
}

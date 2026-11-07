import { cx } from "./cx";
import { Surface, type SurfaceProps } from "./Surface";

/** GlassPanel — a Surface with frosted backdrop blur. */
export function GlassPanel({ className, ...rest }: SurfaceProps) {
  return <Surface className={cx("nxui-glass", className)} {...rest} />;
}

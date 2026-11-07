/* ============================================================================
   CINEMATIC HUD  (Go-full-cinematic overlay)
   ----------------------------------------------------------------------------
   A single, always-on decorative overlay that frames the whole OS in a JARVIS /
   Vision-Pro style: corner brackets, a sweeping scan line, an ambient waveform,
   a radar sweep, and abstract "core telemetry" glyphs.

   It is purely presentational: `pointer-events: none` so it never intercepts a
   click, `aria-hidden` so it is invisible to assistive tech, and driven entirely
   by CSS variables the Environment's ActivityDriver already publishes
   (--nx-core-pulse / --nx-core-energy + the real [data-ai-mode]/[data-ai-state]
   root attributes). No fabricated system metrics — every readout is an ambient,
   abstract signal, not a claim about CPU/RAM/network.
   ========================================================================== */

const WAVE_BARS = Array.from({ length: 14 });
const GLYPHS = ["◇", "△", "○", "▷", "◈", "□", "◁", "▽"];
const STREAM = Array.from({ length: 10 });
const RAIN_GLYPHS = "◇△○▷◈□◁▽↯⟠⌁⎔⟁⌖".split("");
const RAIN_COLUMNS = 3;
const RAIN_PER_COL = 16;
const rainColumn = (seed: number) =>
  Array.from({ length: RAIN_PER_COL }, (_, i) => RAIN_GLYPHS[(seed * 7 + i * 3) % RAIN_GLYPHS.length]);

export function CinematicHud() {
  return (
    <div className="nx-hud" aria-hidden="true">
      {/* Cursor-reactive lighting — a soft spotlight that tracks the pointer */}
      <span className="nx-hud-spotlight" />

      {/* Fine holographic scanlines raking the whole surface */}
      <span className="nx-hud-scanlines" />

      {/* Fullscreen energy flash — driven by the AI mode (command/thinking) */}
      <span className="nx-hud-flash" />

      {/* Corner brackets — the frame of the interface */}
      <span className="nx-hud-corner nx-hud-corner--tl" />
      <span className="nx-hud-corner nx-hud-corner--tr" />
      <span className="nx-hud-corner nx-hud-corner--bl" />
      <span className="nx-hud-corner nx-hud-corner--br" />

      {/* A slow scan line raking down the whole surface */}
      <span className="nx-hud-scan" />

      {/* Ambient waveform — reacts to Core energy via CSS var */}
      <div className="nx-hud-wave">
        {WAVE_BARS.map((_, i) => (
          <span key={i} style={{ ["--i" as string]: i }} />
        ))}
      </div>

      {/* Radar sweep + core-sync readout */}
      <div className="nx-hud-radar">
        <span className="nx-hud-radar-sweep" />
        <span className="nx-hud-radar-ping" />
      </div>

      {/* Drifting AI glyph ticks down the right rail */}
      <div className="nx-hud-glyphs">
        {GLYPHS.map((g, i) => (
          <span key={i} style={{ ["--i" as string]: i }}>{g}</span>
        ))}
      </div>

      {/* Flowing AI glyph streams (matrix-style) down the far right edge */}
      <div className="nx-hud-rain">
        {Array.from({ length: RAIN_COLUMNS }, (_, c) => (
          <div key={c} className="nx-hud-rain-col" style={{ ["--c" as string]: c }}>
            {rainColumn(c + 1).map((g, i) => (
              <span key={i}>{g}</span>
            ))}
          </div>
        ))}
      </div>

      {/* Abstract telemetry label cluster (top-left, under the bracket) */}
      <div className="nx-hud-telemetry">
        <span className="nx-hud-telemetry-row">
          <em />CORE SYNC
        </span>
        <span className="nx-hud-telemetry-row">
          <em />NEURAL LINK
        </span>
        <span className="nx-hud-telemetry-row">
          <em />ENV STREAM
        </span>
      </div>

      {/* Floating holographic processing arc (top-right, under the bracket) */}
      <div className="nx-hud-arc">
        <span className="nx-hud-arc-ring" />
        <span className="nx-hud-arc-ring nx-hud-arc-ring--2" />
        <span className="nx-hud-arc-dot" />
      </div>

      {/* Vertical data-stream column (left rail) */}
      <div className="nx-hud-stream">
        {STREAM.map((_, i) => (
          <span key={i} style={{ ["--i" as string]: i }} />
        ))}
      </div>
    </div>
  );
}

export default CinematicHud;

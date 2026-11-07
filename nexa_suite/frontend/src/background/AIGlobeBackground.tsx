/* ============================================================================
   <AIGlobeBackground /> — the mount point for the premium globe background.
   ----------------------------------------------------------------------------
   • Renders NOTHING when disabled (no container, no dynamic import → the heavy
     three/globe bundle never loads and the fast UI is byte-for-byte unchanged).
   • When enabled: a fixed, pointer-events:none layer behind the whole app.
   • Lazy-loads the engine and only boots once the browser is idle (after the UI
     has painted).
   • Pauses rendering when the window is hidden/minimised or blurred.
   • Re-inits cleanly on a quality change; disposes fully on unmount/disable.
   • Any failure degrades to a calm #050816 backdrop — it can never crash the UI.
   ========================================================================== */
import { useEffect, useRef, useState } from "react";
import { useBackgroundSettings } from "./useBackgroundSettings";
import type { GlobeEngine } from "./globeEngine";

type IdleWindow = Window & {
  requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
  cancelIdleCallback?: (handle: number) => void;
};

export function AIGlobeBackground() {
  const { settings } = useBackgroundSettings();
  const outerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  // Toggle the root flag that makes the shell/chrome glassy so the globe shows
  // through. Removed on disable → the opaque fast UI is restored exactly.
  useEffect(() => {
    const root = document.documentElement;
    if (settings.enabled) root.setAttribute("data-ai-globe", "on");
    else root.removeAttribute("data-ai-globe");
    return () => root.removeAttribute("data-ai-globe");
  }, [settings.enabled]);

  useEffect(() => {
    if (!settings.enabled) return;
    setFailed(false);

    let disposed = false;
    let engine: GlobeEngine | null = null;
    let idleHandle: number | null = null;
    let resizeObserver: ResizeObserver | null = null;
    const idleWin = window as IdleWindow;

    const onVisibility = () => {
      if (!engine) return;
      if (document.hidden || !document.hasFocus()) engine.stop();
      else engine.start();
    };

    const boot = async () => {
      try {
        const [{ GlobeEngine }, { resolvePreset }] = await Promise.all([
          import("./globeEngine"),
          import("./quality"),
        ]);
        if (disposed || !innerRef.current) return;
        engine = new GlobeEngine(innerRef.current);
        engine.init(resolvePreset(settings.quality));
        engine.start();
        document.addEventListener("visibilitychange", onVisibility);
        window.addEventListener("focus", onVisibility);
        window.addEventListener("blur", onVisibility);
        resizeObserver = new ResizeObserver(() => engine?.resize());
        if (outerRef.current) resizeObserver.observe(outerRef.current);
      } catch (err) {
        console.warn("[AIGlobeBackground] initialisation failed:", err);
        setFailed(true);
      }
    };

    // Defer until the UI has painted and the browser is idle.
    if (typeof idleWin.requestIdleCallback === "function") {
      idleHandle = idleWin.requestIdleCallback(() => void boot(), { timeout: 1500 });
    } else {
      idleHandle = window.setTimeout(() => void boot(), 400);
    }

    return () => {
      disposed = true;
      if (idleHandle != null) {
        if (typeof idleWin.cancelIdleCallback === "function") idleWin.cancelIdleCallback(idleHandle);
        else clearTimeout(idleHandle);
      }
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", onVisibility);
      window.removeEventListener("blur", onVisibility);
      resizeObserver?.disconnect();
      engine?.dispose();
      engine = null;
    };
  }, [settings.enabled, settings.quality]);

  if (!settings.enabled) return null;

  return (
    <div ref={outerRef} className="nx-globe-bg" aria-hidden="true" data-failed={failed || undefined}>
      <div ref={innerRef} className="nx-globe-bg-inner" />
    </div>
  );
}

export default AIGlobeBackground;

/* ============================================================================
   INTERACTION · useMicLevel  (opt-in, never auto-started)
   ----------------------------------------------------------------------------
   Returns a smoothed microphone amplitude (0..1) for the Voice Orb — but ONLY
   while `active` is true. It never requests the microphone on its own, keeping
   the app's "no always-on microphone" safety guarantee intact. The existing
   push-to-talk flow remains the sole owner of real capture; this is a visual
   utility a future voice integration can opt into explicitly.
   ========================================================================== */

import { useEffect, useRef, useState } from "react";

export function useMicLevel(active: boolean): number {
  const [level, setLevel] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    if (!active) {
      setLevel(0);
      return;
    }
    let stream: MediaStream | null = null;
    let ctx: AudioContext | null = null;
    let cancelled = false;

    const start = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (cancelled) return;
        ctx = new AudioContext();
        const src = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        src.connect(analyser);
        const buf = new Uint8Array(analyser.frequencyBinCount);

        const tick = () => {
          analyser.getByteTimeDomainData(buf);
          let sum = 0;
          for (let i = 0; i < buf.length; i += 1) {
            const v = (buf[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / buf.length);
          setLevel((prev) => prev + (Math.min(1, rms * 2.2) - prev) * 0.3);
          raf.current = requestAnimationFrame(tick);
        };
        tick();
      } catch {
        setLevel(0);
      }
    };
    void start();

    return () => {
      cancelled = true;
      if (raf.current) cancelAnimationFrame(raf.current);
      stream?.getTracks().forEach((t) => t.stop());
      void ctx?.close();
    };
  }, [active]);

  return level;
}

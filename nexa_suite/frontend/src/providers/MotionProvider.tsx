import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { MotionConfig } from "framer-motion";
import { motionTokens, type MotionTokens } from "@/design/motion";

const MotionContext = createContext<MotionTokens>({ ...motionTokens, reduced: false });

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener?.("change", update);
    return () => mq.removeEventListener?.("change", update);
  }, []);
  return reduced;
}

/**
 * MotionProvider — exposes the motion tokens to the tree and configures
 * framer-motion globally (honouring prefers-reduced-motion). Centralising this
 * keeps all motion consistent and gives later phases a single place to evolve.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();
  const value = useMemo<MotionTokens>(() => ({ ...motionTokens, reduced }), [reduced]);

  return (
    <MotionContext.Provider value={value}>
      <MotionConfig reducedMotion="user" transition={motionTokens.transition.base}>
        {children}
      </MotionConfig>
    </MotionContext.Provider>
  );
}

export function useMotionTokens(): MotionTokens {
  return useContext(MotionContext);
}

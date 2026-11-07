import { createContext, useContext, useMemo, type ReactNode } from "react";
import { ThemeProvider, type ThemeName } from "./ThemeProvider";
import { MotionProvider } from "./MotionProvider";

export type Density = "comfortable" | "compact";

type DesignContextValue = {
  density: Density;
};

const DesignContext = createContext<DesignContextValue>({ density: "comfortable" });

/**
 * DesignProvider — the single design-system entry point. Composes Theme +
 * Motion and carries global design preferences (e.g. density) for future
 * scalability. Wrap the app once with this; do not nest.
 */
export function DesignProvider({
  theme = "nexa-dark",
  density = "comfortable",
  children,
}: {
  theme?: ThemeName;
  density?: Density;
  children: ReactNode;
}) {
  const value = useMemo(() => ({ density }), [density]);
  return (
    <DesignContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <MotionProvider>{children}</MotionProvider>
      </ThemeProvider>
    </DesignContext.Provider>
  );
}

export function useDesign(): DesignContextValue {
  return useContext(DesignContext);
}

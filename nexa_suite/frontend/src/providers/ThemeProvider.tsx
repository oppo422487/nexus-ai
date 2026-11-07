import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

export type ThemeName = "nexa-dark";

type ThemeContextValue = {
  theme: ThemeName;
};

const ThemeContext = createContext<ThemeContextValue>({ theme: "nexa-dark" });

/**
 * ThemeProvider — stamps the active theme onto the document root and exposes it
 * via context. Phase A ships a single dark AI-OS theme; the provider exists so
 * future themes/light-mode can be added without touching component trees.
 */
export function ThemeProvider({
  theme = "nexa-dark",
  children,
}: {
  theme?: ThemeName;
  children: ReactNode;
}) {
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", theme);
    root.style.colorScheme = "dark";
    return () => {
      root.removeAttribute("data-theme");
    };
  }, [theme]);

  const value = useMemo(() => ({ theme }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Moon, Sun } from "lucide-react";

export type Theme = "dark" | "light";
export const THEME_STORAGE_KEY = "mandatetrail-theme";
const ThemeContext = createContext<{ theme: Theme; toggleTheme: () => void }>({
  theme: "dark",
  toggleTheme: () => {},
});

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    // The pre-paint script already applied storage before hydration. Only the
    // toggle icon needs to synchronize here; application colors never flash.
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
    const sync = (event: StorageEvent) => {
      if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
      const next = event.newValue === "light" ? "light" : "dark";
      applyTheme(next);
      setTheme(next);
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    applyTheme(next);
    setTheme(next);
    try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch {
      // Storage restrictions must never prevent switching in the current tab.
    }
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() { return useContext(ThemeContext); }

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const action = theme === "dark" ? "Switch to Lunar Mist light theme" : "Switch to Orbital Intelligence dark theme";
  return (
    <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label={action} title={action}>
      <Sun className="theme-icon-sun" size={18} aria-hidden="true" />
      <Moon className="theme-icon-moon" size={18} aria-hidden="true" />
    </button>
  );
}

"use client";

import { useEffect, useState } from "react";
import { applyTheme, getStoredTheme, setStoredTheme, type ThemeChoice } from "@/lib/theme";

const ORDER: ThemeChoice[] = ["system", "light", "dark"];
const ICON: Record<ThemeChoice, string> = { system: "◐", light: "☀", dark: "☾" };
const LABEL: Record<ThemeChoice, string> = { system: "System theme", light: "Light theme", dark: "Dark theme" };

/** Cycles system → light → dark → system. Reads the stored choice on mount
 * (not during render) since it depends on localStorage, which doesn't exist
 * during server rendering — this avoids a hydration mismatch. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeChoice>("system");

  useEffect(() => {
    // Reading localStorage — an external system — on mount, exactly what
    // effects are for; can't be a lazy useState initializer because the
    // server render (no localStorage) must match the client's first render
    // to avoid a hydration mismatch, so the real value is only safe to read
    // once mounted.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(getStoredTheme());
  }, []);

  function cycle() {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    setTheme(next);
    setStoredTheme(next);
  }

  // Reapply whenever the palette (or anything else) changes theme out from under us.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return (
    <button
      onClick={cycle}
      aria-label={`Theme: ${LABEL[theme]}. Click to change.`}
      title={LABEL[theme]}
      className="flex h-8 w-8 items-center justify-center rounded-full text-sm transition-colors hover:bg-[var(--surface-2)]"
      style={{ color: "var(--text-muted)" }}
    >
      {ICON[theme]}
    </button>
  );
}

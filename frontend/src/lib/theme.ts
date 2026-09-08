"use client";

/**
 * Explicit light/dark toggle on top of the OS-driven default (globals.css).
 * "system" removes the `data-theme` attribute entirely so `prefers-color-scheme`
 * decides, matching how the app already behaved before this toggle existed —
 * "system" is a real third state, not a synonym for "light".
 */
export type ThemeChoice = "light" | "dark" | "system";

const STORAGE_KEY = "theme";

export function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}

export function getStoredTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    // localStorage can throw in a private/locked-down context — fall through to system.
  }
  return "system";
}

export function setStoredTheme(choice: ThemeChoice) {
  try {
    localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // best-effort; the app still works for this tab even if it can't persist
  }
  applyTheme(choice);
}

/** Inlined into <head> via layout.tsx so the theme is set before first paint —
 * without this, a stored "dark" choice flashes light for one frame on load. */
export const THEME_INIT_SCRIPT = `
try {
  var t = localStorage.getItem('${STORAGE_KEY}');
  if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
} catch (e) {}
`;

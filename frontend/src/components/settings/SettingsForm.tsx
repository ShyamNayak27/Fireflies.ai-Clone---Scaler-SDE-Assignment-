"use client";

import { useEffect, useState } from "react";
import { useToast } from "@/components/layout/ToastProvider";
import { applyTheme, getStoredTheme, setStoredTheme, type ThemeChoice } from "@/lib/theme";

const DISPLAY_NAME_KEY = "settings.displayName";
const DEFAULT_NAME = "Shyam Narayan Nayak";

const THEME_OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

/**
 * The one part of Settings that's real, not a placeholder: theme (shared with
 * the TopBar toggle / ⌘K) and a display name persisted per-browser via
 * localStorage — this app has no real auth (README §Assumptions), so
 * per-browser is the honest scope rather than faking a backend profile.
 */
export function SettingsForm() {
  const { show } = useToast();
  const [theme, setTheme] = useState<ThemeChoice>("system");
  const [name, setName] = useState(DEFAULT_NAME);
  const [savedName, setSavedName] = useState(DEFAULT_NAME);

  useEffect(() => {
    // Reads localStorage on mount, not during render — same reasoning as
    // ThemeToggle.tsx (server render has no localStorage, so the real value
    // is only safe to read once mounted, to avoid a hydration mismatch).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(getStoredTheme());
    try {
      const stored = localStorage.getItem(DISPLAY_NAME_KEY);
      if (stored) {
        setName(stored);
        setSavedName(stored);
      }
    } catch {
      // localStorage can throw in a locked-down context — the default name still works.
    }
  }, []);

  function chooseTheme(choice: ThemeChoice) {
    setTheme(choice);
    setStoredTheme(choice);
    applyTheme(choice);
  }

  function saveName() {
    const trimmed = name.trim() || DEFAULT_NAME;
    setName(trimmed);
    setSavedName(trimmed);
    try {
      localStorage.setItem(DISPLAY_NAME_KEY, trimmed);
    } catch {
      // best-effort — the field still reflects the change for this session
    }
    show("Profile updated", "success");
  }

  return (
    <div className="mt-6 space-y-6">
      <section
        className="rounded-[var(--radius-card)] border p-5"
        style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
      >
        <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Profile
        </h2>
        <label className="mt-3 block text-xs font-medium" style={{ color: "var(--text-faint)" }}>
          Display name
        </label>
        <div className="mt-1.5 flex gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && saveName()}
            className="w-full rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none focus:border-[var(--primary)]"
            style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
          />
          <button
            type="button"
            onClick={saveName}
            disabled={name.trim() === savedName}
            className="flex-none rounded-[var(--radius-control)] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            style={{ background: "var(--gradient-accent)" }}
          >
            Save
          </button>
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-faint)" }}>
          Stored locally in your browser — this build has a single demo account, not real auth.
        </p>
      </section>

      <section
        className="rounded-[var(--radius-card)] border p-5"
        style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
      >
        <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
          Appearance
        </h2>
        <div className="mt-3 inline-flex rounded-[var(--radius-control)] border p-1" style={{ borderColor: "var(--border)" }}>
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => chooseTheme(opt.value)}
              className="rounded-[calc(var(--radius-control)-2px)] px-3.5 py-1.5 text-sm font-medium transition-colors"
              style={{
                background: theme === opt.value ? "var(--gradient-accent)" : "transparent",
                color: theme === opt.value ? "white" : "var(--text-muted)",
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--text-faint)" }}>
          Same setting as the toggle in the top bar and ⌘K.
        </p>
      </section>
    </div>
  );
}

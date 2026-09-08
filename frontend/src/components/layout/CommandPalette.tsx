"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api/client";
import type { SearchHit } from "@/lib/api/types";
import { getStoredTheme, setStoredTheme, type ThemeChoice } from "@/lib/theme";

type StaticAction = { kind: "action"; id: string; label: string; run: () => void };
type SearchResult = { kind: "search"; hit: SearchHit };
type Entry = StaticAction | SearchResult;

const THEME_CYCLE: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const DEBOUNCE_MS = 200;

/**
 * ⌘K / Ctrl+K global command palette. Mounted once in the root layout so it
 * works from any page, not re-implemented per route. Two entry types: a
 * fixed set of navigation/theme actions, and live transcript search results
 * from the same `/api/search` endpoint the (placeholder) search page will
 * eventually use — searching *is* the highest-value ⌘K action in an app
 * whose whole point is meetings full of things people said.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
    setHits([]);
    setSelected(0);
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      } else if (e.key === "Escape" && open) {
        close();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, close]);

  // Lets the rail's Search icon (IconRail.tsx) open the same palette instead
  // of duplicating a search UI — this component owns the one real search
  // experience in the app.
  useEffect(() => {
    function onOpenRequest() {
      setOpen(true);
    }
    window.addEventListener("open-command-palette", onOpenRequest);
    return () => window.removeEventListener("open-command-palette", onOpenRequest);
  }, []);

  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const q = query.trim();
    // A too-short query clears results as a plain derived value below
    // (`entries`), not a setState call here — this effect only needs to
    // subscribe to the debounced fetch for a query long enough to search.
    if (q.length < 2) return;
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await apiGet<{ items: SearchHit[] }>(`/api/search?q=${encodeURIComponent(q)}`);
        setHits(res.items.slice(0, 8));
      } catch {
        setHits([]);
      }
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const actions: StaticAction[] = [
    { kind: "action", id: "new-meeting", label: "New meeting…", run: () => router.push("/meetings/new") },
    { kind: "action", id: "library", label: "Go to meeting library", run: () => router.push("/") },
    {
      kind: "action",
      id: "theme",
      label: `Switch theme (currently ${getStoredTheme()})`,
      run: () => setStoredTheme(THEME_CYCLE[getStoredTheme()]),
    },
  ];

  const query2 = query.trim().toLowerCase();
  const filteredActions = query2
    ? actions.filter((a) => a.label.toLowerCase().includes(query2))
    : actions;
  const visibleHits = query2.length < 2 ? [] : hits;
  const entries: Entry[] = [
    ...filteredActions,
    ...visibleHits.map((hit): Entry => ({ kind: "search", hit })),
  ];

  function runEntry(entry: Entry) {
    if (entry.kind === "action") entry.run();
    else router.push(`/meetings/${entry.hit.meeting_id}`);
    close();
  }

  function onKeyDownInInput(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, entries.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && entries[selected]) {
      e.preventDefault();
      runEntry(entries[selected]);
    }
  }

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      style={{ background: "rgba(0,0,0,0.4)" }}
      onClick={close}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-[var(--radius-card)] border shadow-2xl"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(0);
          }}
          onKeyDown={onKeyDownInInput}
          placeholder="Search meetings, or jump to a page…"
          aria-label="Command palette input"
          className="w-full border-b bg-transparent px-4 py-3 text-sm outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
        />
        <ul className="max-h-80 overflow-y-auto py-1.5">
          {entries.length === 0 && (
            <li className="px-4 py-3 text-sm" style={{ color: "var(--text-faint)" }}>
              No matches.
            </li>
          )}
          {entries.map((entry, i) => (
            <li key={entry.kind === "action" ? entry.id : `hit-${entry.hit.segment_id}`}>
              <button
                onClick={() => runEntry(entry)}
                onMouseEnter={() => setSelected(i)}
                className="flex w-full flex-col gap-0.5 px-4 py-2 text-left text-sm"
                style={{ background: i === selected ? "var(--surface-2)" : "transparent", color: "var(--text)" }}
              >
                {entry.kind === "action" ? (
                  <span>{entry.label}</span>
                ) : (
                  <>
                    <span>
                      {entry.hit.meeting_title}
                      {entry.hit.speaker_name && (
                        <span style={{ color: "var(--text-faint)" }}> · {entry.hit.speaker_name}</span>
                      )}
                    </span>
                    <span
                      className="truncate text-xs"
                      style={{ color: "var(--text-faint)" }}
                      dangerouslySetInnerHTML={{ __html: entry.hit.snippet }}
                    />
                  </>
                )}
              </button>
            </li>
          ))}
        </ul>
        <div
          className="flex items-center justify-between border-t px-4 py-2 text-[11px]"
          style={{ borderColor: "var(--border)", color: "var(--text-faint)" }}
        >
          <span>↑↓ to navigate · Enter to select</span>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  );
}

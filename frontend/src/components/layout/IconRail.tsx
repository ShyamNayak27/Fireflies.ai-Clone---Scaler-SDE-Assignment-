"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useToast } from "@/components/layout/ToastProvider";

type NavItem =
  | { id: string; label: string; glyph: string; kind: "link"; href: string }
  | { id: string; label: string; glyph: string; kind: "search" }
  | { id: string; label: string; glyph: string; kind: "soon" };

const NAV_ITEMS: NavItem[] = [
  { id: "search", label: "Search", glyph: "⌕", kind: "search" },
  { id: "meetings", label: "Meetings", glyph: "▢", kind: "link", href: "/" },
  { id: "import", label: "Import transcript", glyph: "⇧", kind: "link", href: "/meetings/new" },
  { id: "record", label: "Record", glyph: "●", kind: "soon" },
  { id: "comments", label: "Comments", glyph: "◔", kind: "soon" },
  { id: "bookmarks", label: "Bookmarks", glyph: "▤", kind: "soon" },
];

const EXPANDED_WIDTH = 216;

/**
 * Primary nav rail. Collapsed to an icon strip at rest (matches the real
 * Fireflies app's default), expands into a labeled flyout on hover/focus —
 * it's absolutely positioned inside a fixed-width wrapper so the expansion
 * overlays the page instead of reflowing every layout that reserves
 * `--rail-width` for it.
 *
 * "Search" opens the global ⌘K command palette (the only real search this
 * app has — see CommandPalette.tsx) instead of linking to a page that
 * doesn't exist. Items with no shipped feature behind them ("soon") are
 * inert by design and say so on click, rather than silently linking home.
 */
export function IconRail() {
  const [expanded, setExpanded] = useState(false);
  const { show } = useToast();

  const announceSoon = useCallback(
    (label: string) => show(`${label} — coming soon`),
    [show],
  );

  const openSearch = useCallback(() => {
    window.dispatchEvent(new CustomEvent("open-command-palette"));
  }, []);

  return (
    <div
      className="relative h-full w-[var(--rail-width)] flex-none"
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
      onFocus={() => setExpanded(true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setExpanded(false);
      }}
    >
      <nav
        className="absolute left-0 top-0 flex h-full flex-col gap-1 overflow-hidden border-r py-4 transition-[width] duration-200 ease-out"
        style={{
          width: expanded ? EXPANDED_WIDTH : "var(--rail-width)",
          borderColor: "var(--border)",
          background: "var(--surface)",
          boxShadow: expanded ? "var(--shadow-md)" : "none",
          zIndex: 40,
        }}
        aria-label="Primary"
      >
        {NAV_ITEMS.map((item) => (
          <RailRow key={item.id} item={item} expanded={expanded} onSoon={announceSoon} onSearch={openSearch} />
        ))}
      </nav>
    </div>
  );
}

function RailRow({
  item,
  expanded,
  onSoon,
  onSearch,
}: {
  item: NavItem;
  expanded: boolean;
  onSoon: (label: string) => void;
  onSearch: () => void;
}) {
  const inner = (
    <>
      <span
        className="flex h-10 w-10 flex-none items-center justify-center text-lg"
        aria-hidden
      >
        {item.glyph}
      </span>
      <span
        className="flex flex-1 items-center justify-between gap-2 overflow-hidden pr-3 text-sm font-medium"
        style={{
          opacity: expanded ? 1 : 0,
          transition: `opacity 150ms ${expanded ? "100ms" : "0ms"}`,
        }}
      >
        <span className="truncate whitespace-nowrap">{item.label}</span>
        {item.kind === "soon" && (
          <span
            className="flex-none rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--surface-2)", color: "var(--text-faint)" }}
          >
            Soon
          </span>
        )}
      </span>
    </>
  );

  const baseClass =
    "mx-2 flex items-center rounded-[var(--radius-control)] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--primary)]";

  if (item.kind === "link") {
    return (
      <Link
        href={item.href}
        title={item.label}
        className={`${baseClass} hover:bg-[var(--surface-2)]`}
        style={{ color: "var(--text-muted)" }}
      >
        {inner}
      </Link>
    );
  }

  if (item.kind === "search") {
    return (
      <button
        type="button"
        title="Search (⌘K)"
        onClick={onSearch}
        className={`${baseClass} hover:bg-[var(--surface-2)]`}
        style={{ color: "var(--text-muted)" }}
      >
        {inner}
      </button>
    );
  }

  return (
    <button
      type="button"
      title={`${item.label} — coming soon`}
      onClick={() => onSoon(item.label)}
      className={`${baseClass} cursor-default hover:bg-[var(--surface-2)]`}
      style={{ color: "var(--text-faint)" }}
    >
      {inner}
    </button>
  );
}

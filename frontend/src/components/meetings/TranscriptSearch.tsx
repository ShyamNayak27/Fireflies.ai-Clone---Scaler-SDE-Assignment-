"use client";

import type { Segment } from "@/lib/api/types";

interface TranscriptSearchProps {
  query: string;
  onQueryChange: (query: string) => void;
  matches: Segment[];
  matchCursor: number;
  onJumpTo: (index: number) => void;
}

/**
 * Client-side search over the segments already loaded into this page — a
 * different thing from the global /api/search endpoint (which hits Postgres
 * tsvector / SQLite FTS5 across every meeting, see docs/ARCHITECTURE.md §7).
 * This one is instant and scoped to "find that line I remember, in the
 * meeting I'm already looking at" — no round trip needed for that.
 *
 * Controlled by the parent (MeetingDetailView) because the match set has to
 * flow back up anyway, to tell the transcript panel which rows to highlight.
 */
export function TranscriptSearch({ query, onQueryChange, matches, matchCursor, onJumpTo }: TranscriptSearchProps) {
  return (
    <div className="flex flex-col gap-1.5 border-b px-3 py-2.5" style={{ borderColor: "var(--border)" }}>
      <div className="flex items-center gap-2">
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || matches.length === 0) return;
            onJumpTo(e.shiftKey ? matchCursor - 1 : matchCursor + 1);
          }}
          placeholder="Find in transcript"
          aria-label="Find in transcript"
          className="min-w-0 flex-1 rounded-[var(--radius-control)] border bg-transparent px-2.5 py-1.5 text-sm outline-none"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
        />
        {query && (
          <span className="flex-none text-xs tabular-nums" style={{ color: "var(--text-faint)" }}>
            {matches.length === 0 ? "0/0" : `${matchCursor + 1}/${matches.length}`}
          </span>
        )}
      </div>
      {query && matches.length > 0 && (
        <div className="flex gap-1.5">
          <button
            onClick={() => onJumpTo(matchCursor - 1)}
            className="rounded px-1.5 py-0.5 text-xs hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-muted)" }}
          >
            ↑ prev
          </button>
          <button
            onClick={() => onJumpTo(matchCursor + 1)}
            className="rounded px-1.5 py-0.5 text-xs hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-muted)" }}
          >
            ↓ next
          </button>
        </div>
      )}
    </div>
  );
}

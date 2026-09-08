"use client";

import { useMemo, useState } from "react";
import { apiDelete, apiPatch, apiPost } from "@/lib/api/client";
import type { ActionItem, Segment } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/format";

/**
 * Full CRUD, not just a read-only list — this is the one place in the app
 * (so far) with a client-authored mutation, so it's also the pattern any
 * later write feature (real transcript ingest §10, editable metadata) will
 * follow: optimistic update, roll back to the prior state on a failed
 * request, and never trust the local id counter — the server assigns real
 * ids for anything actually created.
 */
export function ActionItemPanel({
  meetingId,
  initialItems,
  segments,
  onSeek,
}: {
  meetingId: number;
  initialItems: ActionItem[];
  segments: Segment[];
  onSeek: (ms: number) => void;
}) {
  const [items, setItems] = useState(initialItems);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only the segment's start_ms is needed here, and only for items with a
  // source_segment_id — a lookup by id, not a re-render trigger, so this is
  // cheap even with a large loaded transcript. Segments loaded lazily beyond
  // what's fetched so far (§8, pagination) won't resolve yet; the jump link
  // simply doesn't render until that page has loaded, rather than guessing.
  const segmentStartMsById = useMemo(() => {
    const map = new Map<number, number>();
    for (const s of segments) map.set(s.id, s.start_ms);
    return map;
  }, [segments]);

  async function toggleCompleted(item: ActionItem) {
    const nextCompleted = !item.completed;
    setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, completed: nextCompleted } : i)));
    try {
      const updated = await apiPatch<ActionItem>(`/api/action-items/${item.id}`, {
        completed: nextCompleted,
      });
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch {
      setItems((prev) => prev.map((i) => (i.id === item.id ? item : i))); // roll back
      setError("Couldn't update that item — try again.");
    }
  }

  async function deleteItem(item: ActionItem) {
    const prevItems = items;
    setItems((prev) => prev.filter((i) => i.id !== item.id));
    try {
      await apiDelete(`/api/action-items/${item.id}`);
    } catch {
      setItems(prevItems); // roll back
      setError("Couldn't delete that item — try again.");
    }
  }

  async function addItem(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await apiPost<ActionItem>(`/api/meetings/${meetingId}/action-items`, { text });
      setItems((prev) => [...prev, created]);
      setDraft("");
    } catch {
      setError("Couldn't add that item — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const sorted = [...items].sort((a, b) => Number(a.completed) - Number(b.completed));

  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
        Action items
      </h2>

      <ul className="mt-2 flex flex-col gap-1">
        {sorted.map((item) => (
          <li
            key={item.id}
            className="group flex items-start gap-2.5 rounded-[var(--radius-control)] px-1.5 py-1.5 hover:bg-[var(--surface-2)]"
          >
            <button
              onClick={() => toggleCompleted(item)}
              aria-label={item.completed ? "Mark incomplete" : "Mark complete"}
              className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded border text-[10px]"
              style={{
                borderColor: item.completed ? "var(--primary)" : "var(--border-strong, var(--border))",
                background: item.completed ? "var(--primary)" : "transparent",
                color: "white",
              }}
            >
              {item.completed && "✓"}
            </button>
            <div className="min-w-0 flex-1">
              <p
                className="text-sm leading-snug"
                style={{
                  color: item.completed ? "var(--text-faint)" : "var(--text)",
                  textDecoration: item.completed ? "line-through" : "none",
                }}
              >
                {item.text}
              </p>
              <div className="mt-0.5 flex items-center gap-2 text-[11px]" style={{ color: "var(--text-faint)" }}>
                {item.assignee && <span>{item.assignee.name}</span>}
                {item.due_date && <span>Due {item.due_date}</span>}
                {item.source_segment_id !== null &&
                  segmentStartMsById.has(item.source_segment_id) && (
                    <button
                      onClick={() => onSeek(segmentStartMsById.get(item.source_segment_id as number) as number)}
                      className="hover:underline"
                      title="Jump to where this was said"
                    >
                      {formatTimestamp(segmentStartMsById.get(item.source_segment_id as number) as number)}
                    </button>
                  )}
              </div>
            </div>
            <button
              onClick={() => deleteItem(item)}
              aria-label="Delete action item"
              className="flex-none text-xs opacity-0 transition-opacity group-hover:opacity-100"
              style={{ color: "var(--text-faint)" }}
            >
              ✕
            </button>
          </li>
        ))}
        {sorted.length === 0 && (
          <li className="px-1.5 py-1 text-sm" style={{ color: "var(--text-faint)" }}>
            No action items yet.
          </li>
        )}
      </ul>

      <form onSubmit={addItem} className="mt-2 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add an action item"
          aria-label="Add an action item"
          disabled={submitting}
          className="min-w-0 flex-1 rounded-[var(--radius-control)] border bg-transparent px-2.5 py-1.5 text-sm outline-none disabled:opacity-60"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
        />
        <button
          type="submit"
          disabled={submitting || !draft.trim()}
          className="flex-none rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          style={{ background: "var(--primary)" }}
        >
          Add
        </button>
      </form>
      {error && (
        <p className="mt-1.5 text-xs" style={{ color: "var(--accent-warn)" }}>
          {error}
        </p>
      )}
    </div>
  );
}

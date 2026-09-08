"use client";

import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { lowerBoundIndex } from "./binarySearch";

/**
 * Minimal variable-height list virtualizer, purpose-built for the transcript
 * panel rather than pulled in as a dependency — transcript rows genuinely
 * vary in height (a one-line "Sounds good." next to a five-line answer), so
 * a fixed-row-height scheme would either waste huge amounts of empty space
 * or clip long lines.
 *
 * Approach (the same shape react-window/react-virtual use under the hood):
 *  - keep a measured-height array, seeded with an estimate for rows we
 *    haven't measured yet, as React state (so a measurement is a normal
 *    state update, not an out-of-band mutation the render phase has to
 *    peek at — the offsets below are derived from it with useMemo)
 *  - on scroll, binary-search the derived offsets for the first visible row
 *    instead of walking every row from the top
 *  - render only [start - overscan, end + overscan], padded above/below with
 *    spacers sized from the offsets so the scrollbar stays the right length
 *
 * Rows report their real height once via a ResizeObserver-backed ref
 * callback; only that one row's entry changes, and the offsets memo only
 * recomputes off the (cheap) height array, not a full remeasure.
 */
export function useVirtualList<T>({
  items,
  estimateHeight,
  overscan = 8,
}: {
  items: readonly T[];
  estimateHeight: number;
  overscan?: number;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [heights, setHeights] = useState<number[]>(() => new Array(items.length).fill(estimateHeight));
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);

  // Grow/shrink the height cache to match item count (e.g. a lazily-loaded
  // transcript page arriving) without disturbing entries already measured.
  // Done during render ("adjusting state when a prop changes", not in an
  // effect) — React discards this render's output and immediately re-renders
  // with the corrected state, so there's no flash of the stale-length array.
  const [syncedLength, setSyncedLength] = useState(items.length);
  if (syncedLength !== items.length) {
    setSyncedLength(items.length);
    const next = new Array(items.length).fill(estimateHeight);
    for (let i = 0; i < heights.length && i < next.length; i++) next[i] = heights[i];
    setHeights(next);
  }

  const offsets = useMemo(() => {
    const off = new Array(heights.length + 1);
    off[0] = 0;
    for (let i = 0; i < heights.length; i++) off[i + 1] = off[i] + heights[i];
    return off;
  }, [heights]);

  const setRowHeight = useCallback((index: number, height: number) => {
    setHeights((prev) => {
      if (index >= prev.length || Math.abs(prev[index] - height) < 1) return prev;
      const next = prev.slice();
      next[index] = height;
      return next;
    });
  }, []);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    setViewportHeight(el.clientHeight);
    const onScroll = () => setScrollTop(el.scrollTop);
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(() => setViewportHeight(el.clientHeight));
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, []);

  const rowCount = heights.length;
  const totalHeight = offsets[rowCount] ?? 0;

  const { startIndex, endIndex } = useMemo(() => {
    const rawStart = lowerBoundIndex(offsets, scrollTop, (v) => v);
    const start = Math.max(0, (rawStart === -1 ? 0 : rawStart) - overscan);
    const rawEnd = lowerBoundIndex(offsets, scrollTop + viewportHeight, (v) => v);
    const end = Math.min(rowCount - 1, (rawEnd === -1 ? rowCount - 1 : rawEnd) + overscan);
    return { startIndex: start, endIndex: Math.max(start, end) };
  }, [offsets, scrollTop, viewportHeight, rowCount, overscan]);

  const scrollToIndex = useCallback(
    (index: number, behavior: ScrollBehavior = "smooth") => {
      const el = scrollRef.current;
      if (!el) return;
      const top = offsets[index] ?? 0;
      el.scrollTo({ top: Math.max(0, top - 24), behavior });
    },
    [offsets],
  );

  const isIndexVisible = useCallback(
    (index: number) => {
      const top = offsets[index] ?? 0;
      const bottom = offsets[index + 1] ?? top;
      return top >= scrollTop - 8 && bottom <= scrollTop + viewportHeight + 8;
    },
    [offsets, scrollTop, viewportHeight],
  );

  return {
    scrollRef,
    totalHeight,
    startIndex: Math.min(startIndex, Math.max(0, items.length - 1)),
    endIndex: Math.min(endIndex, Math.max(0, items.length - 1)),
    offsetTop: offsets[startIndex] ?? 0,
    setRowHeight,
    scrollToIndex,
    isIndexVisible,
  };
}

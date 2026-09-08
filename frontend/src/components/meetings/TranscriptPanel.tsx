"use client";

import { useEffect, useRef } from "react";
import type { Segment } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/format";
import { useVirtualList } from "@/lib/player/useVirtualList";

function initials(name: string): string {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

interface TranscriptPanelProps {
  segments: Segment[];
  activeIndex: number;
  highlightedIds?: ReadonlySet<number>;
  onSeek: (ms: number) => void;
  onEndReached?: () => void;
}

/**
 * Virtualized transcript list. Auto-scrolls to keep the active (currently
 * playing) segment in view — but only while the user hasn't just scrolled
 * the panel themselves. Manual scrolling suppresses auto-scroll for a few
 * seconds so reading back through history during playback doesn't fight the
 * player; scrolling to the active row (or letting the suppression window
 * lapse) hands control back to auto-scroll.
 */
export function TranscriptPanel({
  segments,
  activeIndex,
  highlightedIds,
  onSeek,
  onEndReached,
}: TranscriptPanelProps) {
  const { scrollRef, totalHeight, startIndex, endIndex, offsetTop, setRowHeight, scrollToIndex, isIndexVisible } =
    useVirtualList({ items: segments, estimateHeight: 76, overscan: 6 });

  const suppressedUntilRef = useRef(0);
  const lastAutoScrolledIndexRef = useRef(-1);
  const endReachedFiredRef = useRef(false);

  // A programmatic (auto-)scroll fires the same 'scroll' event as a manual
  // one, so distinguish them with a short "this scroll was us" window rather
  // than trying to diff event sources.
  const ignoringOwnScrollRef = useRef(false);

  function handleUserScroll() {
    if (ignoringOwnScrollRef.current) return;
    suppressedUntilRef.current = Date.now() + 4000;
  }

  useEffect(() => {
    if (activeIndex < 0) return;
    if (Date.now() < suppressedUntilRef.current) return;
    if (isIndexVisible(activeIndex)) return;
    if (lastAutoScrolledIndexRef.current === activeIndex) return;
    lastAutoScrolledIndexRef.current = activeIndex;
    ignoringOwnScrollRef.current = true;
    scrollToIndex(activeIndex);
    const t = setTimeout(() => {
      ignoringOwnScrollRef.current = false;
    }, 500);
    return () => clearTimeout(t);
  }, [activeIndex, isIndexVisible, scrollToIndex]);

  useEffect(() => {
    if (!onEndReached) return;
    if (endIndex >= segments.length - 3 && !endReachedFiredRef.current) {
      endReachedFiredRef.current = true;
      onEndReached();
    }
  }, [endIndex, segments.length, onEndReached]);

  // Reset the "already fired" guard once more items actually arrive.
  useEffect(() => {
    endReachedFiredRef.current = false;
  }, [segments.length]);

  const visible = segments.slice(startIndex, endIndex + 1);

  return (
    <div
      ref={scrollRef}
      onScroll={handleUserScroll}
      className="h-full w-full overflow-y-auto px-4 py-3"
      aria-label="Transcript"
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        <div style={{ transform: `translateY(${offsetTop}px)` }}>
          {visible.map((segment, i) => {
            const index = startIndex + i;
            const isActive = index === activeIndex;
            const isHighlighted = highlightedIds?.has(segment.id) ?? false;
            return (
              <TranscriptRow
                key={segment.id}
                segment={segment}
                isActive={isActive}
                isHighlighted={isHighlighted}
                onMeasure={(h) => setRowHeight(index, h)}
                onSeek={onSeek}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TranscriptRow({
  segment,
  isActive,
  isHighlighted,
  onMeasure,
  onSeek,
}: {
  segment: Segment;
  isActive: boolean;
  isHighlighted: boolean;
  onMeasure: (height: number) => void;
  onSeek: (ms: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    onMeasure(el.getBoundingClientRect().height);
    const ro = new ResizeObserver(([entry]) => onMeasure(entry.contentRect.height));
    ro.observe(el);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segment.text]);

  return (
    <div
      ref={ref}
      id={`segment-${segment.id}`}
      className="flex gap-2.5 rounded-[var(--radius-control)] px-2 py-2.5 transition-colors"
      style={{ background: isActive ? "var(--surface-2)" : isHighlighted ? "var(--surface-2)" : "transparent" }}
    >
      <div
        className="flex h-6 w-6 flex-none items-center justify-center rounded-full text-[9px] font-semibold text-white"
        style={{ background: segment.speaker?.avatar_color ?? "var(--text-faint)" }}
        title={segment.speaker?.name ?? "Unknown speaker"}
      >
        {segment.speaker ? initials(segment.speaker.name) : "?"}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-semibold" style={{ color: "var(--text)" }}>
            {segment.speaker?.name ?? "Unknown speaker"}
          </span>
          <button
            onClick={() => onSeek(segment.start_ms)}
            className="text-[11px] tabular-nums hover:underline"
            style={{ color: "var(--text-faint)" }}
          >
            {formatTimestamp(segment.start_ms)}
          </button>
        </div>
        <p
          className="mt-0.5 cursor-pointer text-sm leading-snug"
          style={{ color: isActive ? "var(--text)" : "var(--text-muted)" }}
          onClick={() => onSeek(segment.start_ms)}
        >
          {segment.text}
        </p>
      </div>
    </div>
  );
}

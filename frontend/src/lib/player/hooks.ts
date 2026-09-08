"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { lowerBoundIndex } from "./binarySearch";
import {
  createMediaPlaybackSource,
  createVirtualPlaybackSource,
  type PlaybackSource,
} from "./playbackSource";

interface UsePlaybackSourceArgs {
  mediaUrl: string | null;
  mediaType: "audio" | "video" | null;
  durationMs: number;
}

/**
 * Picks the right PlaybackSource implementation and, when there's real media,
 * hands back the ref to attach to the <audio>/<video> element. This is the
 * one place that branches on "does this meeting have media" — everything
 * downstream (player bar, transcript sync) just holds a `PlaybackSource`.
 */
export function usePlaybackSource({ mediaUrl, mediaType, durationMs }: UsePlaybackSourceArgs) {
  const mediaRef = useRef<(HTMLAudioElement & HTMLVideoElement) | null>(null);

  // The virtual clock needs nothing from the DOM, so it's a pure computation
  // of its inputs — a plain useMemo, no effect needed.
  const virtualSource = useMemo(
    () => (mediaUrl ? null : createVirtualPlaybackSource(durationMs)),
    [mediaUrl, durationMs],
  );

  // A real media source has to wrap an actual <audio>/<video> DOM node, which
  // only exists after this component has committed — that's a genuine
  // synchronization with an external system, so it's the one legitimate use
  // of an effect here.
  const [mediaSource, setMediaSource] = useState<PlaybackSource | null>(null);
  useEffect(() => {
    // Nothing to attach to without both a URL and a mounted media element —
    // `source` below falls back to the virtual clock in that case, so there's
    // no state to reset here.
    if (!mediaUrl) return;
    const el = mediaRef.current;
    if (!el) return;
    setMediaSource(createMediaPlaybackSource(el, durationMs));
    // No cleanup beyond letting the element get garbage collected with the
    // component — createMediaPlaybackSource's listeners live on `el` itself.
  }, [mediaUrl, durationMs]);

  const source = mediaUrl ? mediaSource : virtualSource;
  return { source, mediaRef, hasMedia: Boolean(mediaUrl && mediaType) };
}

/** Live "current time" for display (scrubber position, mm:ss readout). */
export function usePlaybackMs(source: PlaybackSource | null): number {
  return useSyncExternalStore(
    useCallback((cb) => (source ? source.subscribe(cb) : () => {}), [source]),
    () => (source ? source.getMs() : 0),
    () => 0,
  );
}

export function useIsPlaying(source: PlaybackSource | null): boolean {
  return useSyncExternalStore(
    useCallback((cb) => (source ? source.subscribe(cb) : () => {}), [source]),
    () => (source ? source.getIsPlaying() : false),
    () => false,
  );
}

interface SegmentLike {
  start_ms: number;
}

/**
 * The transcript↔player sync. Subscribes to every playback tick internally,
 * but only triggers a React re-render when the *active segment index*
 * actually changes — a tick that lands mid-segment (the common case, since
 * segments are usually several seconds long) does a cheap binary search and
 * bails out without touching React state at all. This is what keeps the
 * (potentially virtualized-but-still-large) transcript list from
 * re-rendering 10 times a second while a meeting plays.
 */
export function useActiveSegmentIndex<T extends SegmentLike>(
  source: PlaybackSource | null,
  segments: readonly T[],
): number {
  const [activeIndex, setActiveIndex] = useState(-1);
  const lastIndexRef = useRef(-1);

  useEffect(() => {
    if (!source) return;
    const compute = () => {
      const ms = source.getMs();
      const idx = lowerBoundIndex(segments, ms, (s) => s.start_ms);
      if (idx !== lastIndexRef.current) {
        lastIndexRef.current = idx;
        setActiveIndex(idx);
      }
    };
    compute();
    return source.subscribe(compute);
  }, [source, segments]);

  return activeIndex;
}

/** Convenience: derive a stable memoized "currently playing" flag + handlers. */
export function usePlayerControls(source: PlaybackSource | null) {
  const isPlaying = useIsPlaying(source);
  const toggle = useCallback(() => {
    if (!source) return;
    if (source.getIsPlaying()) source.pause();
    else source.play();
  }, [source]);
  const seek = useCallback((ms: number) => source?.seek(ms), [source]);
  return useMemo(() => ({ isPlaying, toggle, seek }), [isPlaying, toggle, seek]);
}

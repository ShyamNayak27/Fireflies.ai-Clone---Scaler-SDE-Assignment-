/**
 * PlaybackSource abstraction (docs/ARCHITECTURE.md §9 — Meeting Detail UI).
 *
 * A meeting either has real media (media_url set — e.g. it came from a live
 * recording, see the recordings pipeline) or it doesn't (a pasted/ingested
 * transcript with only estimated timestamps). The transcript panel, the
 * player bar, and the click-to-seek/auto-scroll logic should not care which
 * case they're in — they just want "the current time", "play", "pause", and
 * "seek". This module provides one small interface with two implementations:
 *
 *  - `createMediaPlaybackSource`  — wraps a real <audio>/<video> element
 *  - `createVirtualPlaybackSource` — a plain clock driven by
 *    requestAnimationFrame, for meetings with no media to play back
 *
 * Both are plain (non-React) external stores using the subscribe/getSnapshot
 * shape `useSyncExternalStore` expects, so components only re-render when they
 * actually ask for the current value — critical for the player, because a
 * naive "setState every tick" implementation would re-render the whole
 * transcript list (and everything else on the page) 10+ times a second.
 */

export interface PlaybackSource {
  readonly durationMs: number;
  getMs(): number;
  getIsPlaying(): boolean;
  play(): void;
  pause(): void;
  seek(ms: number): void;
  subscribe(onChange: () => void): () => void;
}

type Listener = () => void;

function makeListenerSet() {
  const listeners = new Set<Listener>();
  return {
    subscribe(cb: Listener) {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    notify() {
      for (const l of listeners) l();
    },
  };
}

/** Real media element (audio or video) as the source of truth for time. */
export function createMediaPlaybackSource(
  mediaEl: HTMLMediaElement,
  durationMsFallback: number,
): PlaybackSource {
  const { subscribe, notify } = makeListenerSet();
  let playing = !mediaEl.paused;

  const onTimeUpdate = () => notify();
  const onPlay = () => {
    playing = true;
    notify();
  };
  const onPause = () => {
    playing = false;
    notify();
  };
  const onSeeked = () => notify();

  mediaEl.addEventListener("timeupdate", onTimeUpdate);
  mediaEl.addEventListener("play", onPlay);
  mediaEl.addEventListener("pause", onPause);
  mediaEl.addEventListener("seeked", onSeeked);

  return {
    get durationMs() {
      return Number.isFinite(mediaEl.duration) && mediaEl.duration > 0
        ? mediaEl.duration * 1000
        : durationMsFallback;
    },
    getMs: () => mediaEl.currentTime * 1000,
    getIsPlaying: () => playing,
    play: () => void mediaEl.play(),
    pause: () => mediaEl.pause(),
    seek: (ms: number) => {
      mediaEl.currentTime = Math.max(0, ms) / 1000;
      notify();
    },
    subscribe,
  };
}

/**
 * No media to play — this is still a "player" in every way that matters to
 * the transcript UI: it has a clock that runs while "playing", it can be
 * paused, and it can be seeked (e.g. by clicking a transcript line), so the
 * exact same sync/scroll/highlight code above works whether or not there's
 * an audio file behind it.
 */
export function createVirtualPlaybackSource(durationMs: number): PlaybackSource {
  const { subscribe, notify } = makeListenerSet();
  let elapsedMs = 0;
  let playing = false;
  let lastTickAt = 0;
  let rafHandle: number | null = null;

  // Throttled to ~10Hz (matches roughly what a real <audio> element's
  // `timeupdate` fires at) rather than every animation frame — the clock
  // only needs to be smooth enough for a mm:ss readout and segment
  // highlighting, not frame-perfect, and this is 6x fewer re-renders than a
  // naive rAF-every-frame loop.
  const TICK_MS = 100;

  function tick(now: number) {
    if (!playing) return;
    if (now - lastTickAt >= TICK_MS) {
      elapsedMs = Math.min(durationMs, elapsedMs + (now - lastTickAt));
      lastTickAt = now;
      notify();
      if (elapsedMs >= durationMs) {
        playing = false;
        notify();
        return;
      }
    }
    rafHandle = requestAnimationFrame(tick);
  }

  return {
    durationMs,
    getMs: () => elapsedMs,
    getIsPlaying: () => playing,
    play: () => {
      if (playing || elapsedMs >= durationMs) return;
      playing = true;
      lastTickAt = performance.now();
      rafHandle = requestAnimationFrame(tick);
      notify();
    },
    pause: () => {
      playing = false;
      if (rafHandle !== null) cancelAnimationFrame(rafHandle);
      notify();
    },
    seek: (ms: number) => {
      elapsedMs = Math.min(durationMs, Math.max(0, ms));
      notify();
    },
    subscribe,
  };
}

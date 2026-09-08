"use client";

import type { RefObject } from "react";
import type { PlaybackSource } from "@/lib/player/playbackSource";
import { usePlaybackMs, usePlayerControls } from "@/lib/player/hooks";
import { formatTimestamp } from "@/lib/format";

/**
 * Same UI whether it's driving a real <audio>/<video> element or the virtual
 * clock — it only ever talks to the PlaybackSource interface, never checks
 * which kind it is. `mediaRef`/`mediaType` are only used to decide whether to
 * render the actual <audio>/<video> tag (needed so the browser has something
 * to actually play), not to branch any of the control logic below it.
 */
export function PlayerBar({
  source,
  mediaUrl,
  mediaType,
  mediaRef,
}: {
  source: PlaybackSource | null;
  mediaUrl: string | null;
  mediaType: "audio" | "video" | null;
  mediaRef: RefObject<(HTMLAudioElement & HTMLVideoElement) | null>;
}) {
  const currentMs = usePlaybackMs(source);
  const { isPlaying, toggle, seek } = usePlayerControls(source);
  const durationMs = source?.durationMs ?? 0;
  const progress = durationMs > 0 ? Math.min(1, currentMs / durationMs) : 0;

  function onScrub(e: React.ChangeEvent<HTMLInputElement>) {
    const fraction = Number(e.target.value) / 1000;
    seek(fraction * durationMs);
  }

  return (
    <div
      className="flex flex-none items-center gap-3 border-t px-5 py-3"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      {mediaUrl && mediaType === "audio" && (
        <audio ref={mediaRef} src={mediaUrl} preload="metadata" className="hidden" />
      )}
      {mediaUrl && mediaType === "video" && (
        <video ref={mediaRef} src={mediaUrl} preload="metadata" className="hidden" />
      )}

      <button
        onClick={toggle}
        disabled={!source}
        aria-label={isPlaying ? "Pause" : "Play"}
        className="flex h-9 w-9 flex-none items-center justify-center rounded-full text-white disabled:opacity-40"
        style={{ background: "var(--primary)" }}
      >
        <span aria-hidden>{isPlaying ? "❚❚" : "▶"}</span>
      </button>

      <span
        className="w-11 flex-none text-right text-xs tabular-nums"
        style={{ color: "var(--text-muted)" }}
      >
        {formatTimestamp(currentMs)}
      </span>

      <input
        type="range"
        min={0}
        max={1000}
        value={Math.round(progress * 1000)}
        onChange={onScrub}
        disabled={!source}
        aria-label="Seek"
        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full disabled:cursor-default"
        style={{
          background: `linear-gradient(to right, var(--primary) ${progress * 100}%, var(--surface-2) ${progress * 100}%)`,
        }}
      />

      <span
        className="w-11 flex-none text-xs tabular-nums"
        style={{ color: "var(--text-faint)" }}
      >
        {formatTimestamp(durationMs)}
      </span>

      {!mediaUrl && (
        <span
          className="flex-none rounded-full px-2 py-0.5 text-[11px] font-medium"
          style={{ background: "var(--surface-2)", color: "var(--text-faint)" }}
          title="No recording attached to this meeting — timestamps are estimated from the transcript, and this virtual clock lets you scrub through it the same way you would real audio."
        >
          No media · virtual clock
        </span>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { apiGet, apiPost } from "@/lib/api/client";
import type { ActionItem, JobOut, Summary } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/format";

const POLL_INTERVAL_MS = 1200;

/**
 * The "Overview" tab of the real Fireflies UI — an overview paragraph, then
 * notes grouped under chapter headings, e.g. "What Went Well: 00:00 – 00:36".
 * Every note with a timestamp is clickable and seeks the player, the same as
 * a transcript line (§8.2) — a summary note IS a pointer into the transcript,
 * not independent content, so it should behave like one.
 *
 * "Regenerate" (docs/ARCHITECTURE.md §9.1) posts to `/summarize` and polls the
 * returned Job exactly the way `UploadTranscriptForm` polls an ingest job —
 * same shape, same interval — then re-fetches the summary AND action items
 * (regenerating can add new ones, §9.1) and hands both back up, since
 * `ActionItemPanel` owns its own list state and can't see this job finish.
 */
export function SummaryPanel({
  meetingId,
  summary,
  onSeek,
  onRegenerated,
}: {
  meetingId: number;
  summary: Summary | null;
  onSeek: (ms: number) => void;
  onRegenerated: (summary: Summary, actionItems: ActionItem[]) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function regenerate() {
    setBusy(true);
    setError(null);
    setStage(null);
    try {
      const job = await apiPost<JobOut>(`/api/meetings/${meetingId}/summarize`, {});
      for (;;) {
        const polled = await apiGet<JobOut>(`/api/jobs/${job.id}`);
        setStage(polled.stage);
        if (polled.status === "succeeded") break;
        if (polled.status === "failed") {
          setError(polled.error ?? "Summarization failed.");
          setBusy(false);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      const [freshSummary, freshItems] = await Promise.all([
        apiGet<Summary>(`/api/meetings/${meetingId}/summary`),
        apiGet<ActionItem[]>(`/api/meetings/${meetingId}/action-items`),
      ]);
      onRegenerated(freshSummary, freshItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Summarization failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
          Overview
        </h2>
        <button
          onClick={regenerate}
          disabled={busy}
          className="flex-none rounded-[var(--radius-control)] border px-2.5 py-1 text-[11px] font-medium transition-colors disabled:opacity-50"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          title="Re-run the summarizer over this meeting's transcript"
        >
          {busy ? `Regenerating${stage ? ` — ${stage}` : ""}…` : summary ? "Regenerate" : "Generate summary"}
        </button>
      </div>

      {error && (
        <p className="-mt-3 text-xs" style={{ color: "var(--accent-warn)" }}>
          {error}
        </p>
      )}

      {!summary ? (
        <div
          className="rounded-[var(--radius-card)] border px-4 py-3 text-sm"
          style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--text-faint)" }}
        >
          No summary yet — this meeting hasn&apos;t been processed by the summarizer.
        </div>
      ) : (
        <>
          <p className="-mt-3 text-sm leading-relaxed" style={{ color: "var(--text)" }}>
            {summary.overview}
          </p>

          {summary.chapters.map((chapter) => (
            <div key={chapter.title}>
              <div className="flex items-baseline gap-2">
                <h3 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {chapter.title}
                </h3>
                <span className="text-xs tabular-nums" style={{ color: "var(--text-faint)" }}>
                  {formatTimestamp(chapter.start_ms)}&ndash;{formatTimestamp(chapter.end_ms)}
                </span>
              </div>
              <ul className="mt-1.5 flex flex-col gap-1.5">
                {chapter.notes.map((note, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    <span className="mt-1.5 h-1 w-1 flex-none rounded-full" style={{ background: "var(--text-faint)" }} />
                    <span className="flex-1">
                      {note.text}
                      {note.start_ms !== null && (
                        <button
                          onClick={() => onSeek(note.start_ms as number)}
                          className="ml-1.5 text-xs tabular-nums hover:underline"
                          style={{ color: "var(--primary)" }}
                        >
                          {formatTimestamp(note.start_ms)}
                        </button>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { apiGet, apiPostForm } from "@/lib/api/client";
import type { JobOut } from "@/lib/api/types";

type Mode = "file" | "paste";
type Phase = "idle" | "uploading" | "polling" | "failed";

const POLL_INTERVAL_MS = 1200;

/** Client component: file/paste toggle, submits to POST /api/meetings/ingest,
 * then polls GET /api/jobs/{id} — the exact same job-polling shape the
 * (deferred) live-recording upload uses, per docs/ARCHITECTURE.md §5/§14. On
 * success it navigates straight to the new meeting. */
export function UploadTranscriptForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("file");
  const [title, setTitle] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canSubmit =
    phase === "idle" || phase === "failed"
      ? mode === "file"
        ? fileInputRef.current?.files?.length
        : pastedText.trim().length > 0
      : false;

  async function pollUntilDone(jobId: string) {
    setPhase("polling");
    for (;;) {
      const job = await apiGet<JobOut>(`/api/jobs/${jobId}`);
      setStage(job.stage);
      if (job.status === "succeeded" && job.meeting_id != null) {
        router.push(`/meetings/${job.meeting_id}`);
        return;
      }
      if (job.status === "failed") {
        setError(job.error ?? "Ingest failed.");
        setPhase("failed");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPhase("uploading");

    const form = new FormData();
    form.set("title", title.trim() || "Untitled meeting");
    if (mode === "file") {
      const file = fileInputRef.current?.files?.[0];
      if (!file) {
        setError("Choose a file first.");
        setPhase("failed");
        return;
      }
      form.set("file", file);
    } else {
      form.set("text", pastedText);
    }

    try {
      const job = await apiPostForm<JobOut>("/api/meetings/ingest", form);
      await pollUntilDone(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setPhase("failed");
    }
  }

  const busy = phase === "uploading" || phase === "polling";

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="title" className="text-sm font-medium" style={{ color: "var(--text)" }}>
          Meeting title
        </label>
        <input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Q3 Planning Sync"
          disabled={busy}
          className="rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-[var(--primary)]"
          style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--text)" }}
        />
      </div>

      <div
        role="tablist"
        aria-label="Transcript source"
        className="flex gap-1 rounded-[var(--radius-control)] p-1"
        style={{ background: "var(--surface-2)" }}
      >
        {(["file", "paste"] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            disabled={busy}
            onClick={() => setMode(m)}
            className="flex-1 rounded-[var(--radius-control)] py-1.5 text-sm font-medium transition-colors"
            style={
              mode === m
                ? { background: "var(--surface)", color: "var(--text)" }
                : { color: "var(--text-muted)" }
            }
          >
            {m === "file" ? "Upload file" : "Paste text"}
          </button>
        ))}
      </div>

      {mode === "file" ? (
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Transcript file
          </span>
          <label
            className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-[var(--radius-card)] border border-dashed px-4 py-8 text-center text-sm"
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".vtt,.srt,.txt,text/vtt,text/plain"
              disabled={busy}
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
              className="sr-only"
            />
            <span aria-hidden className="text-xl">
              ⇧
            </span>
            {fileName ? (
              <span style={{ color: "var(--text)" }}>{fileName}</span>
            ) : (
              <span>.vtt, .srt, or .txt — click to browse</span>
            )}
          </label>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="pasted" className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Pasted transcript
          </label>
          <textarea
            id="pasted"
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
            disabled={busy}
            rows={10}
            placeholder={"Alex Kim  0:00\nHey everyone, thanks for joining.\n\nPriya Shah  0:15\nGlad to be here."}
            className="resize-y rounded-[var(--radius-control)] border px-3 py-2 font-mono text-sm outline-none focus-visible:outline-2 focus-visible:outline-[var(--primary)]"
            style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--text)" }}
          />
        </div>
      )}

      {error && (
        <p className="text-sm" style={{ color: "#dc2626" }}>
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!canSubmit || busy}
        className="rounded-[var(--radius-control)] px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50"
        style={{ background: "var(--primary)" }}
      >
        {phase === "uploading"
          ? "Uploading…"
          : phase === "polling"
            ? `Processing${stage ? ` — ${stage}` : ""}…`
            : "Ingest transcript"}
      </button>

      <p className="text-xs" style={{ color: "var(--text-faint)" }}>
        Supported formats: WebVTT (.vtt, including Zoom exports), SubRip (.srt), an
        Otter.ai-style paste, or plain text. Names, emails, phone numbers and URLs
        found in the transcript are pseudonymized before the meeting is saved.
      </p>
    </form>
  );
}

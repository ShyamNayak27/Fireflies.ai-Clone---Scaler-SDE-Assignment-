"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { apiGet, apiPostForm } from "@/lib/api/client";
import type { JobOut } from "@/lib/api/types";

type Phase = "idle" | "recording" | "uploading" | "polling" | "failed";

const POLL_INTERVAL_MS = 1200;

/** Picks the best `MediaRecorder` mime type this browser actually supports,
 * rather than hardcoding `audio/webm` and failing silently on browsers (e.g.
 * Safari) that don't support it — falling all the way back to letting the
 * browser choose when neither preferred type is supported. */
function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  for (const candidate of ["audio/webm", "audio/mp4"]) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return undefined;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/**
 * Live recording (docs/ARCHITECTURE.md §14) — the frontend half of Milestone
 * #7's backend, deferred until the shared upload-and-poll pattern existed
 * (§10's `UploadTranscriptForm`). Records via `MediaRecorder`, uploads the
 * resulting blob to `POST /api/recordings`, and polls the returned Job with
 * the exact same shape `UploadTranscriptForm` polls an ingest job.
 */
export function RecordMeetingForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [micDenied, setMicDenied] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  // Release the mic if the user navigates away mid-recording rather than
  // clicking Stop — an abandoned live stream otherwise keeps the browser's
  // recording indicator on.
  useEffect(() => stopStream, [stopStream]);

  async function startRecording() {
    setError(null);
    setMicDenied(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mimeType = pickMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();

      startedAtRef.current = Date.now();
      setElapsedMs(0);
      tickRef.current = setInterval(() => setElapsedMs(Date.now() - startedAtRef.current), 250);
      setPhase("recording");
    } catch {
      setMicDenied(true);
      setError("Microphone access was denied or is unavailable — allow it in your browser and try again.");
    }
  }

  async function stopRecording() {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    const blob = await new Promise<Blob>((resolve) => {
      recorder.onstop = () => resolve(new Blob(chunksRef.current, { type: recorder.mimeType }));
      recorder.stop();
    });
    stopStream();

    setPhase("uploading");
    const form = new FormData();
    form.set("title", title.trim() || "Untitled recording");
    const ext = blob.type.includes("mp4") ? "webm.mp4" : "webm";
    form.set("audio", blob, `recording.${ext}`);

    try {
      const job = await apiPostForm<JobOut>("/api/recordings", form);
      await pollUntilDone(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setPhase("failed");
    }
  }

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
        setError(job.error ?? "Transcription failed.");
        setPhase("failed");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
  }

  const busy = phase === "uploading" || phase === "polling";
  const recording = phase === "recording";

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="record-title" className="text-sm font-medium" style={{ color: "var(--text)" }}>
          Meeting title
        </label>
        <input
          id="record-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Q3 Planning Sync"
          disabled={recording || busy}
          className="rounded-[var(--radius-control)] border px-3 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-[var(--primary)]"
          style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--text)" }}
        />
      </div>

      <div
        className="flex flex-col items-center gap-4 rounded-[var(--radius-card)] border border-dashed px-4 py-10"
        style={{ borderColor: "var(--border)" }}
      >
        {recording && (
          <div className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--text)" }}>
            <span
              aria-hidden
              className="h-2.5 w-2.5 rounded-full"
              style={{ background: "var(--accent-warn)", animation: "recording-pulse 1.4s ease-in-out infinite" }}
            />
            Recording · <span className="tabular-nums">{formatElapsed(elapsedMs)}</span>
          </div>
        )}

        {!recording && phase !== "uploading" && phase !== "polling" && (
          <button
            type="button"
            onClick={startRecording}
            className="flex h-16 w-16 items-center justify-center rounded-full text-2xl text-white transition-transform hover:scale-105"
            style={{ background: "var(--primary)" }}
            aria-label="Start recording"
          >
            ●
          </button>
        )}

        {recording && (
          <button
            type="button"
            onClick={stopRecording}
            className="flex h-16 w-16 items-center justify-center rounded-full text-white transition-transform hover:scale-105"
            style={{ background: "#dc2626" }}
            aria-label="Stop recording"
          >
            <span aria-hidden style={{ display: "block", width: 18, height: 18, background: "white", borderRadius: 3 }} />
          </button>
        )}

        {busy && (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {phase === "uploading" ? "Uploading…" : `Processing${stage ? ` — ${stage}` : ""}…`}
          </p>
        )}

        {!recording && !busy && (
          <p className="text-xs" style={{ color: "var(--text-faint)" }}>
            {micDenied ? "Microphone access is required to record." : "Click to start recording from your microphone."}
          </p>
        )}
      </div>

      {error && (
        <p className="text-sm" style={{ color: "#dc2626" }}>
          {error}
        </p>
      )}

      <p className="text-xs" style={{ color: "var(--text-faint)" }}>
        Recorded audio is transcribed via speech-to-text and becomes a regular meeting —
        searchable, summarized, and playable back — the moment it finishes processing.
        Recorded audio never leaves this deployment except to the configured
        transcription provider.
      </p>
    </div>
  );
}

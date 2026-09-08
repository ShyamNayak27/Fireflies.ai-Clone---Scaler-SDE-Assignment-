"use client";

import { useState } from "react";
import { IconRail } from "@/components/layout/IconRail";
import { TopBar } from "@/components/layout/TopBar";
import { RecordMeetingForm } from "@/components/meetings/RecordMeetingForm";
import { UploadTranscriptForm } from "@/components/meetings/UploadTranscriptForm";

type Source = "import" | "record";

const COPY: Record<Source, { heading: string; body: string }> = {
  import: {
    heading: "Import a transcript",
    body: "Upload an exported transcript or paste one directly. It becomes a regular meeting — searchable, summarized, and playable back — the moment it finishes processing.",
  },
  record: {
    heading: "Record a meeting",
    body: "Record straight from your microphone. It's transcribed and becomes a regular meeting the same way an imported one does.",
  },
};

export default function NewMeetingPage() {
  const [source, setSource] = useState<Source>("import");
  const copy = COPY[source];

  return (
    <div className="flex h-screen" style={{ background: "var(--bg)" }}>
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar crumb="New meeting" />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-xl px-5 py-8">
            <div
              role="tablist"
              aria-label="Meeting source"
              className="mb-6 flex gap-1 rounded-[var(--radius-control)] p-1"
              style={{ background: "var(--surface-2)" }}
            >
              {(["import", "record"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  role="tab"
                  aria-selected={source === s}
                  onClick={() => setSource(s)}
                  className="flex-1 rounded-[var(--radius-control)] py-1.5 text-sm font-medium transition-colors"
                  style={
                    source === s
                      ? { background: "var(--surface)", color: "var(--text)" }
                      : { color: "var(--text-muted)" }
                  }
                >
                  {s === "import" ? "Import transcript" : "Record meeting"}
                </button>
              ))}
            </div>

            <h1 className="mb-1 text-lg font-semibold" style={{ color: "var(--text)" }}>
              {copy.heading}
            </h1>
            <p className="mb-6 text-sm" style={{ color: "var(--text-muted)" }}>
              {copy.body}
            </p>
            <div
              className="rounded-[var(--radius-card)] border p-5"
              style={{ borderColor: "var(--border)", background: "var(--surface)" }}
            >
              {source === "import" ? <UploadTranscriptForm /> : <RecordMeetingForm />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

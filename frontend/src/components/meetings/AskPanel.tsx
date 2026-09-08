"use client";

import { useState } from "react";
import { apiPost } from "@/lib/api/client";
import type { AskResponse } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/format";

interface Exchange {
  question: string;
  response: AskResponse;
}

/**
 * "Ask this meeting" (docs/ARCHITECTURE.md §9.2) — a small chat over one
 * meeting's transcript. Each answer is followed by numbered citation chips;
 * clicking one seeks the player the same way a summary note or action item
 * does (`onSeek`), because a citation here is exactly that: a pointer back
 * into the transcript, not independent content.
 */
export function AskPanel({ meetingId, onSeek }: { meetingId: number; onSeek: (ms: number) => void }) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    try {
      const response = await apiPost<AskResponse>(`/api/meetings/${meetingId}/ask`, { question: q });
      setHistory((prev) => [...prev, { question: q, response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't get an answer — try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-faint)" }}>
        Ask this meeting
      </h2>

      {history.length === 0 && !busy && (
        <p className="mt-2 text-sm" style={{ color: "var(--text-faint)" }}>
          Ask a question about what was discussed — answers cite the exact moments they come from.
        </p>
      )}

      <ul className="mt-2 flex flex-col gap-3">
        {history.map((exchange, i) => (
          <li key={i} className="flex flex-col gap-1.5">
            <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
              {exchange.question}
            </p>
            <p className="whitespace-pre-line text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {exchange.response.answer}
            </p>
            {exchange.response.citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {exchange.response.citations.map((c) => (
                  <button
                    key={c.number}
                    onClick={() => onSeek(c.start_ms)}
                    className="rounded-full border px-2 py-0.5 text-[11px] tabular-nums hover:underline"
                    style={{ borderColor: "var(--border)", color: "var(--primary)" }}
                    title="Jump to where this was said"
                  >
                    [{c.number}] {formatTimestamp(c.start_ms)}
                  </button>
                ))}
              </div>
            )}
            {exchange.response.model === null && exchange.response.citations.length > 0 && (
              <p className="text-[11px]" style={{ color: "var(--text-faint)" }}>
                No LLM configured — showing the closest transcript excerpts instead of a synthesized answer.
              </p>
            )}
          </li>
        ))}
      </ul>

      {error && (
        <p className="mt-2 text-xs" style={{ color: "var(--accent-warn)" }}>
          {error}
        </p>
      )}

      <form onSubmit={submit} className="mt-3 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What did we decide about…?"
          aria-label="Ask this meeting a question"
          disabled={busy}
          className="min-w-0 flex-1 rounded-[var(--radius-control)] border bg-transparent px-2.5 py-1.5 text-sm outline-none disabled:opacity-60"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="flex-none rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          style={{ background: "var(--primary)" }}
        >
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
    </div>
  );
}

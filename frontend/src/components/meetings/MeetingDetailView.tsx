"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { IconRail } from "@/components/layout/IconRail";
import { TopBar } from "@/components/layout/TopBar";
import { useToast } from "@/components/layout/ToastProvider";
import { PlayerBar } from "@/components/player/PlayerBar";
import { ActionItemPanel } from "@/components/meetings/ActionItemPanel";
import { AskPanel } from "@/components/meetings/AskPanel";
import { ExportMenu } from "@/components/meetings/ExportMenu";
import { MeetingHeaderActions } from "@/components/meetings/MeetingHeaderActions";
import { SummaryPanel } from "@/components/meetings/SummaryPanel";
import { TagChips } from "@/components/meetings/TagChips";
import { TranscriptPanel } from "@/components/meetings/TranscriptPanel";
import { TranscriptSearch } from "@/components/meetings/TranscriptSearch";
import { apiDelete, apiGet, apiPatch } from "@/lib/api/client";
import type { ActionItem, MeetingDetail, Segment, Summary, TranscriptResponse } from "@/lib/api/types";
import { usePlaybackSource, useActiveSegmentIndex } from "@/lib/player/hooks";
import { formatDate, formatDuration } from "@/lib/format";

export function MeetingDetailView({
  meeting,
  initialSegments,
  initialCursor,
  summary,
  initialActionItems,
}: {
  meeting: MeetingDetail;
  initialSegments: Segment[];
  initialCursor: string | null;
  summary: Summary | null;
  initialActionItems: ActionItem[];
}) {
  const router = useRouter();
  const { show } = useToast();
  const [segments, setSegments] = useState(initialSegments);
  const cursorRef = useRef(initialCursor);
  const loadingMoreRef = useRef(false);
  const [exhausted, setExhausted] = useState(initialCursor === null);

  const [title, setTitle] = useState(meeting.title);
  const [description, setDescription] = useState(meeting.description ?? "");
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(meeting.title);
  const [draftDescription, setDraftDescription] = useState(meeting.description ?? "");
  const [savingEdit, setSavingEdit] = useState(false);
  const [deleting, setDeleting] = useState(false);

  function startEdit() {
    setDraftTitle(title);
    setDraftDescription(description);
    setEditing(true);
  }

  async function saveEdit() {
    const nextTitle = draftTitle.trim();
    if (!nextTitle) {
      show("Title can't be empty", "error");
      return;
    }
    setSavingEdit(true);
    try {
      const updated = await apiPatch<MeetingDetail>(`/api/meetings/${meeting.id}`, {
        title: nextTitle,
        description: draftDescription.trim() || null,
      });
      setTitle(updated.title);
      setDescription(updated.description ?? "");
      setEditing(false);
      show("Meeting updated", "success");
    } catch {
      show("Couldn't save changes — try again", "error");
    } finally {
      setSavingEdit(false);
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    try {
      await apiDelete(`/api/meetings/${meeting.id}`);
      show("Meeting deleted", "success");
      router.push("/");
    } catch {
      show("Couldn't delete this meeting — try again", "error");
      setDeleting(false);
    }
  }

  // `SummaryPanel` runs its own regenerate-summary job and hands the fresh
  // summary + action items back up here — regenerating can both replace the
  // summary and add new action items (app/services/summarize.py), and
  // `ActionItemPanel` only reads its list from props on mount, so bumping
  // `actionItemsKey` remounts it with the fresh list rather than needing a
  // second, parallel way to push updates into its internal state.
  const [currentSummary, setCurrentSummary] = useState(summary);
  const [currentActionItems, setCurrentActionItems] = useState(initialActionItems);
  const [actionItemsKey, setActionItemsKey] = useState(0);

  function handleRegenerated(nextSummary: Summary, nextActionItems: ActionItem[]) {
    setCurrentSummary(nextSummary);
    setCurrentActionItems(nextActionItems);
    setActionItemsKey((k) => k + 1);
  }

  const { source, mediaRef } = usePlaybackSource({
    mediaUrl: meeting.media_url,
    mediaType: meeting.media_type,
    durationMs: meeting.duration_ms,
  });
  const activeIndex = useActiveSegmentIndex(source, segments);

  const [query, setQuery] = useState("");
  const [matchCursor, setMatchCursor] = useState(0);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [] as Segment[];
    return segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [query, segments]);
  const highlightedIds = useMemo(() => new Set(matches.map((m) => m.id)), [matches]);

  const seek = useCallback((ms: number) => source?.seek(ms), [source]);

  function handleQueryChange(next: string) {
    setQuery(next);
    setMatchCursor(0);
  }

  function jumpToMatch(index: number) {
    if (matches.length === 0) return;
    const wrapped = ((index % matches.length) + matches.length) % matches.length;
    setMatchCursor(wrapped);
    seek(matches[wrapped].start_ms);
  }

  // Loads the next page of transcript on demand as the virtualized list
  // scrolls near the bottom — a 500-segment cap per request (see
  // backend/app/routers/meetings.py) means a long meeting needs more than
  // one fetch, and there's no reason to pull all of them up front.
  const loadMore = useCallback(async () => {
    if (loadingMoreRef.current || exhausted || cursorRef.current === null) return;
    loadingMoreRef.current = true;
    try {
      const page = await apiGet<TranscriptResponse>(
        `/api/meetings/${meeting.id}/transcript?limit=200&cursor=${encodeURIComponent(cursorRef.current)}`,
      );
      setSegments((prev) => [...prev, ...page.items]);
      cursorRef.current = page.next_cursor;
      if (page.next_cursor === null) setExhausted(true);
    } finally {
      loadingMoreRef.current = false;
    }
  }, [meeting.id, exhausted]);

  return (
    <div className="flex h-screen" style={{ background: "var(--bg)" }}>
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar crumb={title} />
        <div className="flex min-h-0 flex-1">
          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl px-6 py-5">
              <div className="flex items-start justify-between gap-3">
                <Link href="/" className="text-xs hover:underline" style={{ color: "var(--text-faint)" }}>
                  ← All meetings
                </Link>
                <div className="flex items-center gap-2">
                  <MeetingHeaderActions
                    editing={editing}
                    deleting={deleting}
                    onEdit={startEdit}
                    onDelete={confirmDelete}
                  />
                  <ExportMenu meetingId={meeting.id} />
                </div>
              </div>

              {editing ? (
                <div className="mt-2 space-y-2">
                  <input
                    value={draftTitle}
                    onChange={(e) => setDraftTitle(e.target.value)}
                    autoFocus
                    className="w-full rounded-[var(--radius-control)] border px-3 py-1.5 text-xl font-semibold outline-none focus:border-[var(--primary)]"
                    style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
                  />
                  <textarea
                    value={draftDescription}
                    onChange={(e) => setDraftDescription(e.target.value)}
                    placeholder="Add a description…"
                    rows={2}
                    className="w-full resize-none rounded-[var(--radius-control)] border px-3 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
                    style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={saveEdit}
                      disabled={savingEdit}
                      className="rounded-[var(--radius-control)] px-3.5 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                      style={{ background: "var(--gradient-accent)" }}
                    >
                      {savingEdit ? "Saving…" : "Save"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditing(false)}
                      disabled={savingEdit}
                      className="rounded-[var(--radius-control)] border px-3.5 py-1.5 text-sm font-medium"
                      style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <h1 className="mt-2 text-xl font-semibold" style={{ color: "var(--text)" }}>
                  {title}
                </h1>
              )}
              <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                {formatDate(meeting.started_at)} · {formatDuration(meeting.duration_ms)}
                {meeting.timestamps_estimated && (
                  <span
                    className="ml-2 rounded-full px-2 py-0.5 text-[11px]"
                    style={{ background: "var(--surface-2)", color: "var(--text-faint)" }}
                    title="This meeting has no source recording, so segment timestamps were estimated from word count rather than measured from audio."
                  >
                    estimated timestamps
                  </span>
                )}
              </p>
              {!editing && description && (
                <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {description}
                </p>
              )}
              <div className="mt-4 flex -space-x-2">
                {meeting.participants.map((p) => (
                  <div
                    key={p.id}
                    title={p.name}
                    className="flex h-8 w-8 items-center justify-center rounded-full border-2 text-[11px] font-semibold text-white"
                    style={{ background: p.avatar_color, borderColor: "var(--surface)" }}
                  >
                    {p.name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()}
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <TagChips meetingId={meeting.id} initialTags={meeting.tags} />
              </div>
            </div>

            <div className="mx-auto w-full max-w-3xl px-6 pb-8">
              <div
                className="rounded-[var(--radius-card)] border p-4"
                style={{ borderColor: "var(--border)", background: "var(--surface)" }}
              >
                <SummaryPanel
                  meetingId={meeting.id}
                  summary={currentSummary}
                  onSeek={seek}
                  onRegenerated={handleRegenerated}
                />
              </div>
              <div
                className="mt-4 rounded-[var(--radius-card)] border p-4"
                style={{ borderColor: "var(--border)", background: "var(--surface)" }}
              >
                <ActionItemPanel
                  key={actionItemsKey}
                  meetingId={meeting.id}
                  initialItems={currentActionItems}
                  segments={segments}
                  onSeek={seek}
                />
              </div>
              <div
                className="mt-4 rounded-[var(--radius-card)] border p-4"
                style={{ borderColor: "var(--border)", background: "var(--surface)" }}
              >
                <AskPanel meetingId={meeting.id} onSeek={seek} />
              </div>
            </div>
          </main>

          <aside
            className="flex min-h-0 flex-none flex-col border-l"
            style={{ borderColor: "var(--border)", width: "var(--transcript-width)" }}
          >
            <TranscriptSearch
              query={query}
              onQueryChange={handleQueryChange}
              matches={matches}
              matchCursor={matchCursor}
              onJumpTo={jumpToMatch}
            />
            <div className="min-h-0 flex-1">
              <TranscriptPanel
                segments={segments}
                activeIndex={activeIndex}
                highlightedIds={highlightedIds}
                highlightQuery={query}
                onSeek={seek}
                onEndReached={loadMore}
              />
            </div>
          </aside>
        </div>

        <PlayerBar source={source} mediaUrl={meeting.media_url} mediaType={meeting.media_type} mediaRef={mediaRef} />
      </div>
    </div>
  );
}

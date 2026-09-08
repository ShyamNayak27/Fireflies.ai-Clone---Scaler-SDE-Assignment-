import { notFound } from "next/navigation";
import { MeetingDetailView } from "@/components/meetings/MeetingDetailView";
import { apiGet, apiGetOptional, ApiError } from "@/lib/api/client";
import type { ActionItem, MeetingDetail, Summary, TranscriptResponse } from "@/lib/api/types";

// Server component for the first paint (meeting metadata + first transcript
// page), same reasoning as the library page (docs/ARCHITECTURE.md §8.1) —
// the player, transcript sync, and lazy pagination beyond page one all need
// client-side state, so MeetingDetailView takes over from there.
export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let meeting: MeetingDetail;
  let transcript: TranscriptResponse;
  let summary: Summary | null;
  let actionItems: ActionItem[];
  try {
    [meeting, transcript, summary, actionItems] = await Promise.all([
      apiGet<MeetingDetail>(`/api/meetings/${id}`),
      apiGet<TranscriptResponse>(`/api/meetings/${id}/transcript?limit=200`),
      // A meeting can legitimately have no summary yet (job hasn't run) — a
      // 404 here means "not generated", not "something's wrong", so this one
      // tolerates it instead of throwing (see apiGetOptional in lib/api/client.ts).
      apiGetOptional<Summary>(`/api/meetings/${id}/summary`),
      apiGet<ActionItem[]>(`/api/meetings/${id}/action-items`),
    ]);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <MeetingDetailView
      meeting={meeting}
      initialSegments={transcript.items}
      initialCursor={transcript.next_cursor}
      summary={summary}
      initialActionItems={actionItems}
    />
  );
}

import Link from "next/link";

import { IconRail } from "@/components/layout/IconRail";
import { TopBar } from "@/components/layout/TopBar";
import { LibraryFilterBar } from "@/components/meetings/LibraryFilterBar";
import { MeetingRow } from "@/components/meetings/MeetingRow";
import { apiGet } from "@/lib/api/client";
import type { MeetingListResponse, Tag } from "@/lib/api/types";

type SearchParams = Record<string, string | string[] | undefined>;

function first(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

// Server component: filters live in the URL's search params, so the initial
// paint already reflects them (no client refetch flash, and a filtered view
// is a shareable/bookmarkable link) — see docs/ARCHITECTURE.md §8.1 for the
// same reasoning applied to the unfiltered case this extends.
export default async function LibraryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const q = first(sp.q)?.trim() || undefined;
  const participant = first(sp.participant)?.trim() || undefined;
  const tag = first(sp.tag)?.trim() || undefined;
  const dateFrom = first(sp.from)?.trim() || undefined;
  const dateTo = first(sp.to)?.trim() || undefined;
  const sort = first(sp.sort) === "oldest" ? "oldest" : "recent";

  const query = new URLSearchParams({ limit: "20", sort });
  if (q) query.set("q", q);
  if (participant) query.set("participant", participant);
  if (tag) query.set("tag", tag);
  if (dateFrom) query.set("date_from", dateFrom);
  if (dateTo) query.set("date_to", dateTo);

  const [data, allTags] = await Promise.all([
    apiGet<MeetingListResponse>(`/api/meetings?${query.toString()}`),
    apiGet<Tag[]>("/api/tags"),
  ]);

  const activeFilterCount = [q, participant, tag, dateFrom, dateTo].filter(Boolean).length;

  return (
    <div className="flex h-screen" style={{ background: "var(--bg)" }}>
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar crumb="Meetings" />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-5 py-6">
            <div className="mb-5 flex items-end justify-between">
              <div>
                <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
                  All meetings
                </h1>
                <p className="mt-0.5 text-sm" style={{ color: "var(--text-faint)" }}>
                  {data.items.length} meeting{data.items.length === 1 ? "" : "s"}
                  {activeFilterCount > 0 ? ` matching ${activeFilterCount} filter${activeFilterCount === 1 ? "" : "s"}` : " · transcribed & searchable"}
                </p>
              </div>
              <Link
                href="/meetings/new"
                className="rounded-[var(--radius-control)] px-3.5 py-2 text-sm font-medium text-white transition-transform active:scale-[0.97]"
                style={{ background: "var(--gradient-accent)", boxShadow: "var(--shadow-sm)" }}
              >
                + Import transcript
              </Link>
            </div>

            <LibraryFilterBar
              tags={allTags}
              initial={{ q, participant, tag, from: dateFrom, to: dateTo, sort }}
            />

            <div
              className="mt-4 overflow-hidden rounded-[var(--radius-card)] border"
              style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
            >
              {data.items.length === 0 ? (
                <div className="px-5 py-10 text-center text-sm" style={{ color: "var(--text-faint)" }}>
                  No meetings match these filters.
                </div>
              ) : (
                data.items.map((meeting) => <MeetingRow key={meeting.id} meeting={meeting} />)
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

import Link from "next/link";

import { IconRail } from "@/components/layout/IconRail";
import { TopBar } from "@/components/layout/TopBar";
import { MeetingRow } from "@/components/meetings/MeetingRow";
import { apiGet } from "@/lib/api/client";
import type { MeetingListResponse } from "@/lib/api/types";

// Server component: first paint has real data, no client-side loading flash for
// the initial page. See docs/ARCHITECTURE.md §8.1 — RSC for the library's first
// load, client-side takes over for infinite scroll beyond page one.
export default async function LibraryPage() {
  const data = await apiGet<MeetingListResponse>("/api/meetings?limit=20");

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
                  {data.items.length} meeting{data.items.length === 1 ? "" : "s"} · transcribed &amp; searchable
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
            <div
              className="overflow-hidden rounded-[var(--radius-card)] border"
              style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
            >
              {data.items.map((meeting) => (
                <MeetingRow key={meeting.id} meeting={meeting} />
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

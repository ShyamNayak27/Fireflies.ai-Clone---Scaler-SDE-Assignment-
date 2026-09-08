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
          <div className="mx-auto max-w-4xl">
            <div className="flex items-center justify-between px-5 py-4">
              <h1 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
                All meetings
              </h1>
              <div className="flex items-center gap-3">
                <span className="text-sm" style={{ color: "var(--text-faint)" }}>
                  {data.items.length} meeting{data.items.length === 1 ? "" : "s"}
                </span>
                <Link
                  href="/meetings/new"
                  className="rounded-[var(--radius-control)] border px-3 py-1.5 text-sm font-medium"
                  style={{ borderColor: "var(--border)", color: "var(--text)" }}
                >
                  Import transcript
                </Link>
              </div>
            </div>
            <div
              className="rounded-[var(--radius-card)] border"
              style={{ borderColor: "var(--border)", background: "var(--surface)" }}
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

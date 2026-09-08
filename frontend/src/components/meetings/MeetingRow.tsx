import Link from "next/link";
import type { MeetingListItem } from "@/lib/api/types";
import { formatDate, formatDuration } from "@/lib/format";

function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function MeetingRow({ meeting }: { meeting: MeetingListItem }) {
  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="group grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b px-5 py-3.5 transition-colors last:border-b-0 hover:bg-[var(--surface-2)]"
      style={{ borderColor: "var(--border)" }}
    >
      <div className="min-w-0">
        <p
          className="truncate text-sm font-medium transition-colors group-hover:text-[var(--primary)]"
          style={{ color: "var(--text)" }}
        >
          {meeting.title}
        </p>
        <p className="mt-0.5 text-xs" style={{ color: "var(--text-faint)" }}>
          {formatDate(meeting.started_at)} · {formatDuration(meeting.duration_ms)}
          {meeting.tags.length > 0 && (
            <span className="ml-2 inline-flex gap-1 align-middle">
              {meeting.tags.map((t) => (
                <span
                  key={t.id}
                  className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                  style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
                >
                  {t.name}
                </span>
              ))}
            </span>
          )}
        </p>
      </div>
      <div className="flex -space-x-2">
        {meeting.participants.slice(0, 4).map((p) => (
          <div
            key={p.id}
            title={p.name}
            className="flex h-7 w-7 items-center justify-center rounded-full border-2 text-[10px] font-semibold text-white"
            style={{ background: p.avatar_color, borderColor: "var(--surface)" }}
          >
            {initials(p.name)}
          </div>
        ))}
      </div>
      <span
        className="rounded-full px-2.5 py-1 text-xs font-medium"
        style={{
          background: meeting.status === "ready" ? "var(--surface-2)" : "var(--accent-warn)",
          color: meeting.status === "ready" ? "var(--text-muted)" : "white",
        }}
      >
        {meeting.status}
      </span>
    </Link>
  );
}

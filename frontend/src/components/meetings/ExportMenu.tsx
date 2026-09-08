"use client";

import { useState } from "react";
import { apiUrl } from "@/lib/api/client";

/** Plain `<a href>` navigation rather than a JS fetch+blob — the backend
 * already sends the right Content-Disposition header (app/routers/extras.py),
 * so a direct browser navigation downloads the file with zero extra code and
 * works even if the export is large. */
export function ExportMenu({ meetingId }: { meetingId: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-[var(--radius-control)] border px-2.5 py-1.5 text-xs font-medium"
        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
      >
        Export ▾
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 z-20 mt-1 w-40 overflow-hidden rounded-[var(--radius-control)] border shadow-lg"
            style={{ borderColor: "var(--border)", background: "var(--surface)" }}
          >
            <a
              href={apiUrl(`/api/meetings/${meetingId}/export?format=md`)}
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text)" }}
            >
              Markdown (.md)
            </a>
            <a
              href={apiUrl(`/api/meetings/${meetingId}/export?format=txt`)}
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text)" }}
            >
              Plain text (.txt)
            </a>
          </div>
        </>
      )}
    </div>
  );
}

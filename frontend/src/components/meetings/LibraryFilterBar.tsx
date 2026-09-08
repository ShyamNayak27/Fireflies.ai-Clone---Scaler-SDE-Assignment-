"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Tag } from "@/lib/api/types";

type Filters = {
  q?: string;
  participant?: string;
  tag?: string;
  from?: string;
  to?: string;
  sort: "recent" | "oldest";
};

const DEBOUNCE_MS = 350;

/**
 * Filter/sort controls for the library, backed by URL search params (see
 * page.tsx) rather than local-only state — the library page's server
 * component reads the same params, so a filtered view survives a refresh
 * and can be shared as a link. Text fields debounce before pushing a new
 * URL; select/date fields push immediately since there's no typing to wait
 * out.
 */
export function LibraryFilterBar({ tags, initial }: { tags: Tag[]; initial: Filters }) {
  const router = useRouter();
  const pathname = usePathname();
  const [q, setQ] = useState(initial.q ?? "");
  const [participant, setParticipant] = useState(initial.participant ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function pushFilters(next: Partial<Filters>) {
    const merged: Filters = {
      q,
      participant,
      tag: initial.tag,
      from: initial.from,
      to: initial.to,
      sort: initial.sort,
      ...next,
    };
    const params = new URLSearchParams();
    if (merged.q) params.set("q", merged.q);
    if (merged.participant) params.set("participant", merged.participant);
    if (merged.tag) params.set("tag", merged.tag);
    if (merged.from) params.set("from", merged.from);
    if (merged.to) params.set("to", merged.to);
    if (merged.sort !== "recent") params.set("sort", merged.sort);
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (q === (initial.q ?? "") && participant === (initial.participant ?? "")) return;
    debounceRef.current = setTimeout(() => pushFilters({ q, participant }), DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, participant]);

  const hasFilters = Boolean(initial.q || initial.participant || initial.tag || initial.from || initial.to);

  return (
    <div
      className="flex flex-wrap items-center gap-2 rounded-[var(--radius-card)] border p-2.5"
      style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
    >
      <div className="relative min-w-[180px] flex-1">
        <span
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-sm"
          style={{ color: "var(--text-faint)" }}
          aria-hidden
        >
          ⌕
        </span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter by title…"
          aria-label="Filter by title"
          className="w-full rounded-[var(--radius-control)] border py-1.5 pl-7 pr-2 text-sm outline-none focus:border-[var(--primary)]"
          style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
        />
      </div>

      <input
        value={participant}
        onChange={(e) => setParticipant(e.target.value)}
        placeholder="Participant…"
        aria-label="Filter by participant"
        className="w-36 rounded-[var(--radius-control)] border px-2.5 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
        style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
      />

      <select
        value={initial.tag ?? ""}
        onChange={(e) => pushFilters({ tag: e.target.value || undefined })}
        aria-label="Filter by tag"
        className="rounded-[var(--radius-control)] border px-2.5 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
        style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
      >
        <option value="">All tags</option>
        {tags.map((t) => (
          <option key={t.id} value={t.name}>
            {t.name}
          </option>
        ))}
      </select>

      <input
        type="date"
        value={initial.from ?? ""}
        onChange={(e) => pushFilters({ from: e.target.value || undefined })}
        aria-label="From date"
        className="rounded-[var(--radius-control)] border px-2.5 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
        style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
      />
      <span className="text-sm" style={{ color: "var(--text-faint)" }}>
        –
      </span>
      <input
        type="date"
        value={initial.to ?? ""}
        onChange={(e) => pushFilters({ to: e.target.value || undefined })}
        aria-label="To date"
        className="rounded-[var(--radius-control)] border px-2.5 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
        style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
      />

      <select
        value={initial.sort}
        onChange={(e) => pushFilters({ sort: e.target.value as Filters["sort"] })}
        aria-label="Sort order"
        className="ml-auto rounded-[var(--radius-control)] border px-2.5 py-1.5 text-sm outline-none focus:border-[var(--primary)]"
        style={{ borderColor: "var(--border)", background: "var(--bg)", color: "var(--text)" }}
      >
        <option value="recent">Newest first</option>
        <option value="oldest">Oldest first</option>
      </select>

      {hasFilters && (
        <button
          type="button"
          onClick={() => {
            setQ("");
            setParticipant("");
            router.push(pathname);
          }}
          className="rounded-[var(--radius-control)] px-2.5 py-1.5 text-sm font-medium"
          style={{ color: "var(--text-muted)" }}
        >
          Clear
        </button>
      )}
    </div>
  );
}

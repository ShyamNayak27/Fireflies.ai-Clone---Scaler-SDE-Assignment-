"use client";

import { useState } from "react";
import { apiDelete, apiPost } from "@/lib/api/client";
import type { Tag } from "@/lib/api/types";

/** Add/remove tag chips on a meeting. Optimistic like `ActionItemPanel` — add
 * shows immediately with a temporary id, replaced by the server's real tag
 * (or rolled back on failure); a tag name that already exists elsewhere is
 * reused server-side (`get_or_create_tag`), not duplicated. */
export function TagChips({ meetingId, initialTags }: { meetingId: number; initialTags: Tag[] }) {
  const [tags, setTags] = useState(initialTags);
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function addTag(e: React.FormEvent) {
    e.preventDefault();
    const name = draft.trim();
    if (!name || adding) return;
    if (tags.some((t) => t.name.toLowerCase() === name.toLowerCase())) {
      setDraft("");
      return;
    }
    setAdding(true);
    setError(null);
    try {
      const created = await apiPost<Tag>(`/api/meetings/${meetingId}/tags`, { name });
      setTags((prev) => [...prev, created]);
      setDraft("");
    } catch {
      setError("Couldn't add that tag.");
    } finally {
      setAdding(false);
    }
  }

  async function removeTag(tag: Tag) {
    const prev = tags;
    setTags((cur) => cur.filter((t) => t.id !== tag.id));
    try {
      await apiDelete(`/api/meetings/${meetingId}/tags/${tag.id}`);
    } catch {
      setTags(prev);
      setError("Couldn't remove that tag.");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {tags.map((tag) => (
        <span
          key={tag.id}
          className="group flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium"
          style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
        >
          {tag.name}
          <button
            onClick={() => removeTag(tag)}
            aria-label={`Remove tag ${tag.name}`}
            className="opacity-0 transition-opacity group-hover:opacity-100"
            style={{ color: "var(--text-faint)" }}
          >
            ✕
          </button>
        </span>
      ))}
      <form onSubmit={addTag} className="flex items-center">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="+ tag"
          aria-label="Add a tag"
          disabled={adding}
          className="w-16 rounded-full bg-transparent px-2 py-1 text-xs outline-none focus:w-24 transition-all"
          style={{ color: "var(--text-muted)" }}
        />
      </form>
      {error && (
        <span className="text-xs" style={{ color: "#dc2626" }}>
          {error}
        </span>
      )}
    </div>
  );
}

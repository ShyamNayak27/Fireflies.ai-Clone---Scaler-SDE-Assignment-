"use client";

import { useState } from "react";

/**
 * Edit + Delete for the meeting header. Delete asks for confirmation inline
 * (swaps the button for a "Delete this meeting? / Cancel" pair) instead of a
 * native `window.confirm` — same visual language as the rest of the app, and
 * it doesn't leave a raw browser dialog behind mid-flow.
 */
export function MeetingHeaderActions({
  editing,
  deleting,
  onEdit,
  onDelete,
}: {
  editing: boolean;
  deleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span style={{ color: "var(--text-muted)" }}>Delete this meeting?</span>
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="rounded-[var(--radius-control)] px-2.5 py-1 text-xs font-medium text-white disabled:opacity-60"
          style={{ background: "#e0503f" }}
        >
          {deleting ? "Deleting…" : "Delete"}
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={deleting}
          className="rounded-[var(--radius-control)] border px-2.5 py-1 text-xs font-medium"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={onEdit}
        disabled={editing}
        title="Edit title & description"
        className="rounded-[var(--radius-control)] border px-2.5 py-1 text-xs font-medium disabled:opacity-40"
        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
      >
        Edit
      </button>
      <button
        type="button"
        onClick={() => setConfirming(true)}
        title="Delete meeting"
        className="rounded-[var(--radius-control)] border px-2.5 py-1 text-xs font-medium"
        style={{ borderColor: "var(--border)", color: "#e0503f" }}
      >
        Delete
      </button>
    </div>
  );
}

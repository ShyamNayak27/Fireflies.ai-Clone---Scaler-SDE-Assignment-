"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useToast } from "@/components/layout/ToastProvider";

export function TopBar({ crumb }: { crumb: string }) {
  const { show } = useToast();

  async function handleShare() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      show("Link copied to clipboard", "success");
    } catch {
      show("Couldn't copy the link — copy it from the address bar", "error");
    }
  }

  return (
    <header
      className="flex h-[var(--topbar-height)] flex-none items-center justify-between border-b px-5 backdrop-blur-sm"
      style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
    >
      <span className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        {crumb}
      </span>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <button
          type="button"
          onClick={handleShare}
          className="rounded-[var(--radius-control)] px-3.5 py-1.5 text-sm font-medium text-white transition-transform active:scale-[0.97]"
          style={{ background: "var(--gradient-accent)", boxShadow: "var(--shadow-sm)" }}
        >
          Share
        </button>
        <Link
          href="/settings"
          title="Settings"
          className="flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold text-white transition-transform active:scale-[0.94]"
          style={{ background: "var(--gradient-accent)", borderColor: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
        >
          SN
        </Link>
      </div>
    </header>
  );
}

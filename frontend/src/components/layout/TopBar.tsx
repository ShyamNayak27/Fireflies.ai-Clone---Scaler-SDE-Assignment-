import { ThemeToggle } from "@/components/layout/ThemeToggle";

export function TopBar({ crumb }: { crumb: string }) {
  return (
    <header
      className="flex h-[var(--topbar-height)] flex-none items-center justify-between border-b px-5"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      <span className="text-sm" style={{ color: "var(--text-muted)" }}>
        {crumb}
      </span>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <button
          className="rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-medium text-white transition-colors"
          style={{ background: "var(--primary)" }}
        >
          Share
        </button>
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold text-white"
          style={{ background: "var(--primary)" }}
        >
          SN
        </div>
      </div>
    </header>
  );
}

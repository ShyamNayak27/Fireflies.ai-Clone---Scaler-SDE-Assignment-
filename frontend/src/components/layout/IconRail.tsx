import Link from "next/link";

const ICONS = [
  { href: "/search", label: "Search", glyph: "⌕" },
  { href: "/", label: "Meetings", glyph: "▢" },
  { href: "/meetings/new", label: "Import transcript", glyph: "⇧" },
  { href: "/", label: "Record", glyph: "●" },
  { href: "/", label: "Comments", glyph: "◔" },
  { href: "/", label: "Bookmarks", glyph: "▤" },
];

export function IconRail() {
  return (
    <nav
      className="flex h-full w-[var(--rail-width)] flex-none flex-col items-center gap-1 border-r py-4"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      aria-label="Primary"
    >
      {ICONS.map((icon) => (
        <Link
          key={icon.label}
          href={icon.href}
          title={icon.label}
          className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-control)] text-lg hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--primary)]"
          style={{ color: "var(--text-muted)" }}
        >
          <span aria-hidden>{icon.glyph}</span>
        </Link>
      ))}
    </nav>
  );
}

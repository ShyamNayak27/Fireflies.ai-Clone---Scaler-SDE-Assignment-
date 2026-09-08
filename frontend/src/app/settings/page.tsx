import { IconRail } from "@/components/layout/IconRail";
import { TopBar } from "@/components/layout/TopBar";
import { SettingsForm } from "@/components/settings/SettingsForm";

const SOON_SECTIONS = [
  {
    title: "Notifications",
    body: "Email and desktop alerts for new transcripts, mentions, and action items assigned to you.",
  },
  {
    title: "Integrations",
    body: "Connect a calendar so meetings are created automatically, plus Slack and CRM export.",
  },
  {
    title: "Billing",
    body: "Plan, seats, and usage — this is a single-demo-owner build (see the README), so there's no billing model yet.",
  },
];

export default function SettingsPage() {
  return (
    <div className="flex h-screen" style={{ background: "var(--bg)" }}>
      <IconRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar crumb="Settings" />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-2xl px-5 py-8">
            <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--text)" }}>
              Settings
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--text-faint)" }}>
              Your profile and appearance are live. Everything else here is on the roadmap.
            </p>

            <SettingsForm />

            <div className="mt-8">
              <h2
                className="mb-3 text-xs font-semibold uppercase tracking-wide"
                style={{ color: "var(--text-faint)" }}
              >
                Coming soon
              </h2>
              <div
                className="overflow-hidden rounded-[var(--radius-card)] border"
                style={{ borderColor: "var(--border)", background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
              >
                {SOON_SECTIONS.map((s, i) => (
                  <div
                    key={s.title}
                    className="flex items-start justify-between gap-4 px-5 py-4"
                    style={i > 0 ? { borderTop: "1px solid var(--border)" } : undefined}
                  >
                    <div>
                      <p className="text-sm font-medium" style={{ color: "var(--text)" }}>
                        {s.title}
                      </p>
                      <p className="mt-0.5 text-sm" style={{ color: "var(--text-faint)" }}>
                        {s.body}
                      </p>
                    </div>
                    <span
                      className="mt-0.5 flex-none rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                      style={{ background: "var(--surface-2)", color: "var(--text-faint)" }}
                    >
                      Soon
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

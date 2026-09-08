import { defineConfig, devices } from "@playwright/test";

/**
 * Real Chromium against a real dev server and a real FastAPI backend, per
 * docs/ARCHITECTURE.md §10 — no mocked API responses. `webServer` starts the
 * Next.js dev server for a local run; CI (see .github/workflows/ci.yml)
 * starts the backend as its own step first, since Playwright's `webServer`
 * only manages one process cleanly and the backend needs the seed data to
 * exist before the frontend even boots.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false, // several specs mutate the same seeded meeting (tags, comments)
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Some environments (e.g. a locked-down CI sandbox with no network
        // access to download browsers) ship a pinned Chromium build under a
        // fixed path rather than the headless-shell build Playwright expects
        // by default — point at it explicitly when set, otherwise let
        // Playwright resolve its own managed browser as usual.
        ...(process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } }
          : {}),
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev -- -p 3000",
        url: "http://localhost:3000",
        reuseExistingServer: true,
        timeout: 30_000,
      },
});

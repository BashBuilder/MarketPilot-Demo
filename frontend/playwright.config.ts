import { defineConfig, devices } from "@playwright/test";

const mockPort = 3000;
const realPort = 3001;
const mockBaseURL = `http://localhost:${mockPort}`;
const realBaseURL = `http://localhost:${realPort}`;
const realApiUrl = process.env.E2E_API_URL?.trim();

// Next dev servers cannot safely share one working directory, so start only
// the server for the project being run. `e2e:mock` and `e2e:real` select one.
const cliProjects = process.argv
  .filter((arg) => arg.startsWith("--project="))
  .map((arg) => arg.slice("--project=".length));
const runsReal = cliProjects.includes("real");
const startsMock = !runsReal || cliProjects.includes("mock");

const mockServer = {
  command: `pnpm exec cross-env NEXT_PUBLIC_API_MOCKING=enabled NEXT_TELEMETRY_DISABLED=1 next dev --port ${mockPort}`,
  url: mockBaseURL,
  reuseExistingServer: !process.env.CI,
  timeout: 180_000,
};

const realServer = {
  command: `pnpm exec cross-env NEXT_PUBLIC_API_URL=${realApiUrl} NEXT_TELEMETRY_DISABLED=1 next dev --port ${realPort}`,
  url: realBaseURL,
  reuseExistingServer: !process.env.CI,
  timeout: 180_000,
};

const servers = [
  ...(startsMock ? [mockServer] : []),
  ...(runsReal && realApiUrl ? [realServer] : []),
];

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  // The mock app runs under `next dev`, so cold page compilation can take a
  // while; keep a small worker pool and a generous per-test budget.
  timeout: 90_000,
  workers: process.env.CI ? 1 : 2,
  reporter: "list",
  use: {
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "mock",
      use: { ...devices["Desktop Chrome"], baseURL: mockBaseURL },
    },
    {
      name: "real",
      testMatch: /happy-path\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"], baseURL: realBaseURL },
    },
  ],
  webServer: servers.length > 0 ? servers : undefined,
});

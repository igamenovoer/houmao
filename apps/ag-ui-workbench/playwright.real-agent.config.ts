import { defineConfig, devices } from "@playwright/test";

const testTimeoutMs = Number.parseInt(process.env.HMWB_REAL_AGENT_TIMEOUT_MS ?? "180000", 10);

export default defineConfig({
  testDir: "./tests",
  testMatch: "realAgentGuiSmoke.spec.ts",
  timeout: Number.isFinite(testTimeoutMs) && testTimeoutMs > 0 ? testTimeoutMs + 60_000 : 240_000,
  expect: {
    timeout: 15_000,
  },
  outputDir: "test-results/real-agent-gui-smoke",
  use: {
    baseURL: "http://127.0.0.1:5179",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: "HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE=1 bun run dev --host 127.0.0.1 --port 5179",
    url: "http://127.0.0.1:5179",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});

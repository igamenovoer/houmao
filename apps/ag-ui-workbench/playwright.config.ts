import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testIgnore: ["**/realAgentGuiSmoke.spec.ts"],
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },
  use: {
    baseURL: "http://127.0.0.1:5178",
    trace: "on-first-retry",
  },
  webServer: {
    command: "HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE=1 bun run dev --host 127.0.0.1 --port 5178",
    url: "http://127.0.0.1:5178",
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

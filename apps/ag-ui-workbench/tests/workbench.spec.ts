import { expect, test, type Page } from "@playwright/test";

import { FakeAgUiServer } from "./fakeAgUiServer";

let fakeServer: FakeAgUiServer;

test.beforeAll(async () => {
  fakeServer = new FakeAgUiServer();
  await fakeServer.start();
});

test.afterAll(async () => {
  await fakeServer.stop();
});

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
});

test("validates operator, docked multi-pane isolation, graphics, detach, and persistence", async ({ page, context }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("proxy-status")).toContainText("loopback proxy ready");

  await configurePane(page, "operator", "Operator", fakeServer.targetBase("operator"), "operator-thread");
  await page.getByTestId("prompt-operator").fill("operator prompt");
  await page.getByTestId("run-operator").click();
  await expect(page.getByTestId("transcript-operator")).toContainText("operator-only-run-evidence");
  expect(fakeServer.runs.filter((run) => run.target === "operator")).toHaveLength(1);
  expect(fakeServer.runs.filter((run) => run.target === "alpha")).toHaveLength(0);
  expect(fakeServer.runs.filter((run) => run.target === "beta")).toHaveLength(0);

  await page.getByTestId("add-agent-pane").click();
  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-1", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");
  await configurePane(page, "agent-2", "Beta", fakeServer.targetBase("beta"), "beta-thread");
  await page.getByTestId("split-right-agent-2").click();

  await page.getByTestId("connect-agent-1").click();
  await page.getByTestId("connect-agent-2").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");
  await expect(page.getByTestId("raw-agent-2")).toContainText("beta-connect-evidence");
  await expect(page.getByTestId("raw-agent-1")).not.toContainText("beta-connect-evidence");
  await expect(page.getByTestId("raw-agent-2")).not.toContainText("alpha-connect-evidence");

  await page.getByTestId("prompt-agent-1").fill("render alpha graphic");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("alpha-run-evidence");
  await expect(page.getByTestId("graphic-agent-1")).toContainText("Alpha SVG Graphic");
  await expect(page.getByTestId("graphic-agent-1")).toContainText("Alpha graphic alt text");
  await expect(page.getByTestId("graphic-agent-1").locator("svg")).toContainText("alpha svg content");

  await page.getByTestId("prompt-agent-2").fill("render unsupported graphic");
  await page.getByTestId("run-agent-2").click();
  await expect(page.getByTestId("unsupported-graphic-agent-2")).toContainText("Unsupported graphic format: iframe");

  await page.getByTestId("disconnect-agent-1").click();
  await page.getByTestId("disconnect-agent-2").click();
  await expect
    .poll(() => fakeServer.detaches.map((detach) => detach.connectionId).sort())
    .toEqual(["alpha-connection-1", "beta-connection-1"]);
  expect(fakeServer.interruptRequests).toBe(0);

  await expect.poll(() => context.pages().length).toBe(1);
  const savedBeforeReload = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(JSON.stringify(savedBeforeReload.layout)).not.toContain("floatingGroups");
  expect(JSON.stringify(savedBeforeReload.layout)).not.toContain("popoutGroups");

  await page.reload();
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect(page.getByTestId("thread-id-agent-1")).toHaveValue("alpha-thread");
  await expect(page.getByTestId("transcript-agent-1")).not.toContainText("alpha-run-evidence");
  const savedAfterReload = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(JSON.stringify(savedAfterReload.layout)).not.toContain("floatingGroups");
  expect(JSON.stringify(savedAfterReload.layout)).not.toContain("popoutGroups");
});

test("surfaces target policy errors before contacting a disallowed target", async ({ page }) => {
  await configurePane(page, "operator", "Operator", "http://example.com/v1/ag-ui", "operator-thread");
  await page.getByTestId("capabilities-operator").click();
  await expect(page.getByTestId("errors-operator")).toContainText("target_policy_rejected");
});

async function configurePane(
  page: Page,
  paneId: string,
  label: string,
  url: string,
  threadId: string,
): Promise<void> {
  await page.getByTestId(`target-label-${paneId}`).fill(label);
  await page.getByTestId(`target-url-${paneId}`).fill(url);
  await page.getByTestId(`thread-id-${paneId}`).fill(threadId);
}

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
  fakeServer.resetRecords();
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
});

test("submits minimal run and connect request bodies", async ({ page }) => {
  const proxyRequests = collectProxyPostBodies(page);

  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect.poll(() => panelIds(page)).toEqual([]);

  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-1", "Manual Operator", fakeServer.targetBase("operator"), "operator-thread");
  await page.getByTestId("connect-agent-1").click();
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "operator").length).toBe(1);
  expectMinimalConnectBody(fakeServer.connects.find((connect) => connect.target === "operator")!.body);

  await page.getByTestId("prompt-agent-1").fill("operator canvas prompt");
  const operatorSurface = await measuredSurfaceSize(page, "agent-1");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("operator-only-run-evidence");
  const operatorRun = fakeServer.runs.find((run) => run.target === "operator");
  expect(operatorRun).toBeTruthy();
  expectMinimalRunBody(operatorRun!.body, {
    threadId: "operator-thread",
    message: "operator canvas prompt",
    canvasSize: operatorSurface,
  });

  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-2", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");
  await page.getByTestId("connect-agent-2").click();
  await expect(page.getByTestId("raw-agent-2")).toContainText("alpha-connect-evidence");
  const agentConnect = fakeServer.connects.find((connect) => connect.target === "alpha");
  expect(agentConnect).toBeTruthy();
  expectMinimalConnectBody(agentConnect!.body);

  await page.getByTestId("prompt-agent-2").fill("agent canvas prompt");
  const agentSurface = await measuredSurfaceSize(page, "agent-2");
  await page.getByTestId("run-agent-2").click();
  await expect(page.getByTestId("transcript-agent-2")).toContainText("alpha-run-evidence");
  const agentRun = fakeServer.runs.find((run) => run.target === "alpha");
  expect(agentRun).toBeTruthy();
  expectMinimalRunBody(agentRun!.body, {
    threadId: "alpha-thread",
    message: "agent canvas prompt",
    canvasSize: agentSurface,
  });

  await page.getByTestId("add-debug-agent-pane").click();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");
  const debugConnect = proxyRequests.find(
    (request) => request.target?.includes("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/connect"),
  );
  expect(debugConnect).toBeTruthy();
  expectMinimalConnectBody(expectRecord(debugConnect!.body), { allowReplayFlag: true });
});

test("validates docked multi-pane isolation, graphics, detach, and persistence", async ({ page, context }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("proxy-status")).toContainText("loopback proxy ready");

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
  await expect(page.getByTestId("transcript-agent-1")).toContainText("Alpha Dashboard");
  await expect(page.getByTestId("component-dashboard-agent-1")).toBeVisible();
  await expect(page.getByTestId("component-metric-grid-agent-1")).toContainText("Pass rate");
  await expect(page.getByTestId("component-chart-agent-1").first()).toBeVisible();
  await expect(page.getByTestId("component-table-agent-1")).toContainText("Alpha count");

  await page.getByTestId("prompt-agent-1").fill("prompt survives clear");
  const detachesBeforeClear = fakeServer.detaches.length;
  await page.getByTestId("clear-canvas-agent-1").click();
  await expect(page.getByTestId("graphic-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("component-dashboard-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("transcript-agent-1")).not.toContainText("alpha-run-evidence");
  await expect(page.getByTestId("raw-agent-1")).not.toContainText("alpha-connect-evidence");
  await expect(page.getByTestId("prompt-agent-1")).toHaveValue("prompt survives clear");
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect(page.getByTestId("status-agent-1")).toContainText("connected");
  expect(fakeServer.detaches).toHaveLength(detachesBeforeClear);
  expect(fakeServer.interruptRequests).toBe(0);

  await page.getByTestId("prompt-agent-1").fill("render alpha graphic after clear");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("alpha-run-evidence");
  await expect(page.getByTestId("graphic-agent-1")).toContainText("Alpha SVG Graphic");

  await page.getByTestId("prompt-agent-2").fill("render unsupported graphic");
  await page.getByTestId("run-agent-2").click();
  await expect(page.getByTestId("unsupported-graphic-agent-2")).toContainText("Unsupported graphic format: iframe");
  await expect(page.getByTestId("invalid-component-agent-2")).toContainText("data must be a non-empty array");
  await expect(page.getByTestId("unknown-component-agent-2")).toContainText("houmao.chart.scatter");
  await expect(page.getByTestId("unknown-component-agent-2")).toContainText("beta unknown raw marker");

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

test("supports agent-pane operator marking without restoring the legacy operator pane", async ({ page }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect.poll(() => panelIds(page)).toEqual([]);

  await page.evaluate(() => {
    window.localStorage.setItem(
      "houmao.agUiWorkbench.v1",
      JSON.stringify({
        discovery: { passiveServerUrl: "http://127.0.0.1:9891" },
        panes: {
          operator: {
            paneId: "operator",
            kind: "operator",
            target: {
              label: "Legacy Operator",
              url: "http://127.0.0.1:9/v1/ag-ui",
              threadId: "legacy-thread",
              source: { kind: "manual" },
            },
          },
        },
        watchedTargets: {},
        nextAgentIndex: 1,
        nextDebugAgentIndex: 1,
        nextTmuxIndex: 1,
      }),
    );
  });
  await page.reload();
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect.poll(() => panelIds(page)).toEqual([]);
  expect(await page.evaluate(() => window.__HMWB_TEST__!.storage().panes.operator)).toBeUndefined();

  await page.getByTestId("add-agent-pane").click();
  await expect(page.getByTestId("mark-operator-agent-1")).toBeDisabled();

  await page.getByTestId("choose-agent-agent-1").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("select-agent-alpha").click();
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect(page.getByTestId("mark-operator-agent-1")).toBeEnabled();

  await page.getByTestId("mark-operator-agent-1").click();
  await expect(page.getByTestId("operator-marker-agent-1")).toContainText("Operator");
  expect(await page.evaluate(() => window.__HMWB_TEST__!.storage().operatorPaneId)).toBe("agent-1");

  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");
  const connect = fakeServer.connects.find((entry) => entry.target === "alpha");
  expect(connect).toBeTruthy();
  expectMinimalConnectBody(connect!.body);

  await page.getByTestId("prompt-agent-1").fill("operator marked request stays minimal");
  const surface = await measuredSurfaceSize(page, "agent-1");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("alpha-run-evidence");
  const run = fakeServer.runs.find((entry) => entry.target === "alpha");
  expect(run).toBeTruthy();
  expectMinimalRunBody(run!.body, {
    threadId: "alpha-thread",
    message: "operator marked request stays minimal",
    canvasSize: surface,
  });

  await page.getByTestId("target-url-agent-1").fill(fakeServer.targetBase("manual"));
  await expect(page.getByTestId("operator-marker-agent-1")).toHaveCount(0);
  expect(await page.evaluate(() => window.__HMWB_TEST__!.storage().operatorPaneId)).toBeUndefined();

  await page.getByTestId("close-agent-1").click();
  await expect.poll(() => panelIds(page)).toEqual([]);
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await page.reload();
  await expect.poll(() => panelIds(page)).toEqual([]);
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
});

test("surfaces target policy errors before contacting a disallowed target", async ({ page }) => {
  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-1", "Manual", "http://example.com/v1/ag-ui", "agent-thread");
  await page.getByTestId("capabilities-agent-1").click();
  await expect(page.getByTestId("errors-agent-1")).toContainText("target_policy_rejected");
});

test("lists discovered agents, retargets panes, opens new panes, and keeps manual fallback", async ({ page }) => {
  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-1", "Manual", fakeServer.targetBase("manual"), "manual-thread");
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("manual-connect-evidence");

  await page.getByTestId("choose-agent-agent-1").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("agent-row-alpha")).toBeVisible();
  await expect(page.getByTestId("agent-row-beta")).toBeVisible();
  await page.getByTestId("agent-filter").fill("alpha");
  await expect(page.getByTestId("agent-row-alpha")).toBeVisible();
  await expect(page.getByTestId("agent-row-beta")).toBeHidden();
  await page.getByTestId("agent-filter").fill("");
  await page.getByTestId("agent-row-alpha").dblclick();

  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect(page.getByTestId("raw-agent-1")).not.toContainText("manual-connect-evidence");
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");

  const savedDiscovered = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(savedDiscovered.discovery.passiveServerUrl).toBe(fakeServer.passiveBase());
  expect(savedDiscovered.panes["agent-1"].target.source).toMatchObject({
    kind: "discovered",
    agentId: "alpha",
    agentName: "HOUMAO-alpha",
  });
  expect(JSON.stringify(savedDiscovered)).not.toContain("alpha-connect-evidence");

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-beta").dblclick();
  await expect(page.getByTestId("target-url-agent-2")).toHaveValue(fakeServer.targetBase("beta"));
  await page.getByTestId("connect-agent-2").click();
  await expect(page.getByTestId("raw-agent-2")).toContainText("beta-connect-evidence");
  await expect(page.getByTestId("raw-agent-1")).not.toContainText("beta-connect-evidence");

  await page.getByTestId("target-url-agent-1").fill(fakeServer.targetBase("manual"));
  const savedManual = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(savedManual.panes["agent-1"].target.source).toMatchObject({ kind: "manual" });

  await page.getByTestId("choose-agent-agent-1").click();
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("select-agent-no-gateway").click();
  await expect(page.getByTestId("agent-picker")).toHaveCount(0);
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue("");
  const savedWaiting = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(savedWaiting.panes["agent-1"].target.source).toMatchObject({
    kind: "discovered",
    agentId: "no-gateway",
    addressStatus: "live_without_gateway",
  });
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("status-agent-1")).toContainText("waiting");
});

test("binds last-bound thread only for foreground discovered agent panes", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("select-agent-alpha").click();

  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect
    .poll(() => fakeServer.bindingUpdates.filter((update) => update.target === "alpha"))
    .toContainEqual({ target: "alpha", threadId: "alpha-thread", source: "gui_view_change" });

  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");
  await expect
    .poll(() => fakeServer.bindingUpdates.filter((update) => update.target === "alpha"))
    .toContainEqual({ target: "alpha", threadId: "alpha-thread", source: "gui_connect" });

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("watch-agent-beta").click();
  await expect.poll(() => fakeServer.connects.some((connect) => connect.target === "beta")).toBeTruthy();
  expect(fakeServer.bindingUpdates.some((update) => update.target === "beta")).toBeFalsy();
  await page.getByTestId("close-agent-picker").click();
  await expect(page.getByTestId("agent-picker")).toHaveCount(0);

  await page.getByTestId("close-agent-1").click();
  await expect(page.getByTestId("panel-agent-1")).toHaveCount(0);
  await expect.poll(() => fakeServer.bindingClears).toContain("alpha");
  expect(fakeServer.bindingClears).not.toContain("beta");
});

test("opens tmux tab, filters sessions, attaches, rejects read-only input, and avoids persistence", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("close-agent-picker").click();

  await page.getByTestId("add-tmux-pane").click();
  await expect(page.getByTestId("panel-tmux-1")).toBeVisible();
  await expect(page.getByTestId("tmux-status-tmux-1")).toContainText("ready");
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toBeVisible();
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toContainText("HOUMAO-alpha");
  await expect(page.getByTestId("tmux-session-utility-shell")).toBeHidden();

  await page.getByTestId("tmux-search-tmux-1").fill("gen-alpha");
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toBeVisible();
  await page.getByTestId("tmux-search-tmux-1").fill("utility");
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toBeHidden();
  await expect(page.getByTestId("tmux-empty-tmux-1")).toContainText("No tmux sessions match");

  await page.getByTestId("tmux-houmao-only-tmux-1").uncheck();
  await expect(page.getByTestId("tmux-session-utility-shell")).toBeVisible();
  await page.getByTestId("tmux-search-tmux-1").fill("");

  await page.getByTestId("tmux-session-houmao-alpha").click();
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture attached houmao-alpha");
  await page.getByTestId("tmux-terminal-tmux-1").click();
  await page.keyboard.type("rw-fixture-input");
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture input");

  await page.getByTestId("tmux-detach-tmux-1").click();
  await page.getByTestId("tmux-read-only-tmux-1").check();
  await page.getByTestId("tmux-session-houmao-alpha").click();
  await expect(page.getByTestId("tmux-read-only-state-tmux-1")).toContainText("read only");
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture attached houmao-alpha");
  await page.getByTestId("tmux-terminal-tmux-1").click();
  await page.keyboard.type("blocked-fixture-input");
  await expect(page.getByTestId("tmux-terminal-tmux-1")).not.toContainText("blocked-fixture-input");
  expect(await readOnlyTmuxSocketRejectsInput(page)).toBeTruthy();

  const persistenceBeforeClose = await browserPersistenceText(page);
  expect(persistenceBeforeClose).not.toContain("fixture attached");
  expect(persistenceBeforeClose).not.toContain("rw-fixture-input");
  expect(persistenceBeforeClose).not.toContain("blocked-fixture-input");

  await page.getByTestId("close-tmux-1").click();
  await expect(page.getByTestId("panel-tmux-1")).toHaveCount(0);
  const sessions = (await (await page.request.get("/__houmao_tmux/sessions")).json()) as {
    sessions: Array<{ sessionName: string }>;
  };
  expect(sessions.sessions.some((session) => session.sessionName === "houmao-alpha")).toBeTruthy();
  expect(fakeServer.detaches).toHaveLength(0);
  expect(fakeServer.interruptRequests).toBe(0);

  const persistenceAfterClose = await browserPersistenceText(page);
  expect(persistenceAfterClose).not.toContain("fixture attached");
  expect(persistenceAfterClose).not.toContain("fixture input");
  expect(persistenceAfterClose).not.toContain("Authorization");
  expect(persistenceAfterClose).not.toContain("Bearer");
  expect(JSON.stringify(await page.evaluate(() => window.__HMWB_TEST__!.storage().layout ?? {}))).not.toContain(
    "floatingGroups",
  );
});

test("surfaces target policy errors for disallowed passive-server discovery", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill("http://example.com");
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("picker-error")).toContainText("target_policy_rejected");
});

test("reconnects discovered pane through passive resolution after gateway restart", async ({ page }) => {
  await page.getByTestId("add-agent-pane").click();
  await page.getByTestId("choose-agent-agent-1").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-alpha").dblclick();

  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");
  const firstGatewayUrl = await page.getByTestId("target-url-agent-1").inputValue();

  await fakeServer.restartGateway("alpha");

  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-reconnect-evidence", {
    timeout: 15000,
  });
  await expect
    .poll(() => page.getByTestId("target-url-agent-1").inputValue())
    .not.toBe(firstGatewayUrl);
  expect(
    fakeServer.connects.some(
      (connect) => connect.target === "alpha" && connect.body.lastSeenEventId === undefined,
    ),
  ).toBeTruthy();
});

test("watched target keeps external chart in client cache after pane close and reopen", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-alpha").dblclick();

  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("watch-strip-agent-1")).toContainText("Watched");
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");

  const publishResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: barToolCallEvents("watched-cache-chart", "Watched Cache Chart"),
    },
  });
  expect(publishResponse.ok()).toBeTruthy();
  const publishBody = (await publishResponse.json()) as {
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(publishBody.deliveredCount).toBe(3);
  expect(publishBody.storedCount).toBe(0);
  expect(publishBody.replay).toBe("none");

  await expect(page.getByTestId("component-agent-1")).toContainText("Watched Cache Chart");
  await expect(page.getByTestId("component-chart-agent-1").first().locator("svg")).toBeVisible();

  await page.getByTestId("close-agent-1").click();
  await expect(page.getByTestId("panel-agent-1")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.__HMWB_TEST__!.watchedTargetKeys().length)).toBe(1);

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("watch-state-alpha")).toContainText("connected");
  await page.getByTestId("open-watched-agent-alpha").click();

  await expect(page.getByTestId("panel-agent-2")).toBeVisible();
  await expect(page.getByTestId("component-agent-2")).toContainText("Watched Cache Chart");
  await expect(page.getByTestId("component-chart-agent-2").first().locator("svg")).toBeVisible();
});

test("clear canvas clears watched cache without detaching and accepts future live events", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-alpha").dblclick();
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("watch-strip-agent-1")).toContainText("Watched");
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-connect-evidence");

  const staleResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: barToolCallEvents("watched-clear-stale-chart", "Watched Clear Stale Chart"),
    },
  });
  expect(staleResponse.ok()).toBeTruthy();
  expect((await staleResponse.json()) as { deliveredCount: number }).toMatchObject({
    deliveredCount: 3,
  });
  await expect(page.getByTestId("component-agent-1")).toContainText("Watched Clear Stale Chart");
  await expect(page.getByTestId("component-chart-agent-1").first().locator("svg")).toBeVisible();

  const detachesBeforeClear = fakeServer.detaches.length;
  await page.getByTestId("clear-canvas-agent-1").click();
  await expect(page.getByTestId("component-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("raw-agent-1")).not.toContainText("alpha-connect-evidence");
  await expect(page.getByTestId("status-agent-1")).toContainText("connected");
  expect(fakeServer.detaches).toHaveLength(detachesBeforeClear);
  expect(fakeServer.interruptRequests).toBe(0);

  await page.getByTestId("close-agent-1").click();
  await expect(page.getByTestId("panel-agent-1")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.__HMWB_TEST__!.watchedTargetKeys().length)).toBe(1);

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("watch-state-alpha")).toContainText("connected");
  await page.getByTestId("open-watched-agent-alpha").click();
  await expect(page.getByTestId("panel-agent-2")).toBeVisible();
  await expect(page.getByTestId("transcript-agent-2")).not.toContainText("Watched Clear Stale Chart");

  const freshResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: barToolCallEvents("watched-clear-fresh-chart", "Watched Clear Fresh Chart"),
    },
  });
  expect(freshResponse.ok()).toBeTruthy();
  expect((await freshResponse.json()) as { deliveredCount: number }).toMatchObject({
    deliveredCount: 3,
  });
  await expect(page.getByTestId("component-agent-2")).toContainText("Watched Clear Fresh Chart");
  await expect(page.getByTestId("component-chart-agent-2").first().locator("svg")).toBeVisible();
});

test("events published while unwatched are live-only and not recovered later", async ({ page }) => {
  const publishResponse = await page.request.post(`${fakeServer.targetBase("beta")}/events`, {
    data: {
      threadId: "beta-thread",
      events: barToolCallEvents("missed-live-chart", "Missed Live-Only Chart"),
    },
  });
  expect(publishResponse.ok()).toBeTruthy();
  const publishBody = (await publishResponse.json()) as {
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(publishBody.deliveredCount).toBe(0);
  expect(publishBody.storedCount).toBe(0);
  expect(publishBody.replay).toBe("none");

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-beta").dblclick();
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("raw-agent-1")).toContainText("beta-connect-evidence");
  await expect(page.getByTestId("transcript-agent-1")).not.toContainText("Missed Live-Only Chart");
});

test("debug agent receives external AG-UI events and renders chart proof", async ({ page }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await page.getByTestId("add-debug-agent-pane").click();
  await expect(page.getByTestId("panel-debug-agent-1")).toBeVisible();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");
  await expect(page.getByTestId("debug-events-endpoint-debug-agent-1")).toHaveValue(
    "http://127.0.0.1:5178/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events",
  );

  const response = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: barToolCallEvents("debug-live-bar", "External Live Chart"),
    },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as {
    acceptedCount: number;
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(body.acceptedCount).toBe(3);
  expect(body.deliveredCount).toBeGreaterThan(0);
  expect(body.storedCount).toBe(3);
  expect(body.replay).toBe("debug_thread_buffer");

  await expect(page.getByTestId("component-debug-agent-1")).toContainText("External Live Chart");
  const chart = page.getByTestId("component-chart-debug-agent-1").first();
  await expect(chart).toBeVisible();
  await expect(chart.locator("svg")).toBeVisible();
  const bars = chart.locator("svg .recharts-bar-rectangle, svg .recharts-rectangle");
  await expect(bars.first()).toBeVisible();
  expect(await bars.count()).toBeGreaterThan(0);

  await page.getByTestId("panel-debug-agent-1").screenshot({
    path: "test-results/debug-agent-chart.png",
  });

  const stored = await page.evaluate(() =>
    Object.entries(window.localStorage)
      .map(([key, value]) => `${key}:${value}`)
      .join("\n"),
  );
  expect(stored).not.toContain("External Live Chart");
  expect(stored).not.toContain("TOOL_CALL_ARGS");
  expect(stored).not.toContain("Authorization");
  expect(stored).not.toContain("Bearer");
});

test("debug relay validates, replays, supports live-only mode, and detaches", async ({ page }) => {
  const statusResponse = await page.request.get("/__houmao_debug_agents/status");
  expect(statusResponse.ok()).toBeTruthy();
  const statusBody = (await statusResponse.json()) as { status: string; routes: string[] };
  expect(statusBody.status).toBe("ready");
  expect(statusBody.routes).toContain("POST /__houmao_debug_agents/{agent_id}/v1/ag-ui/events");

  const capabilitiesResponse = await page.request.get(
    "/__houmao_debug_agents/debug-agent-1/v1/ag-ui/capabilities",
  );
  expect(capabilitiesResponse.ok()).toBeTruthy();
  const capabilities = (await capabilitiesResponse.json()) as {
    capabilities?: { identity?: { type?: string } };
    houmao?: { lifecycleBoundary?: string };
  };
  expect(capabilities.capabilities?.identity?.type).toBe("debug-agent");
  expect(capabilities.houmao?.lifecycleBoundary).toBe("debug-relay-only");

  const invalidResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: [],
    },
  });
  expect(invalidResponse.status()).toBe(400);
  const invalidBody = (await invalidResponse.json()) as { code: string; detail: string };
  expect(invalidBody.code).toBe("ag_ui_event_validation_failed");
  expect(invalidBody.detail).toContain("non-empty array");

  const replayResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: barToolCallEvents("debug-replay-bar", "Replay Before Connect Chart"),
    },
  });
  const replayBody = (await replayResponse.json()) as {
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(replayBody.deliveredCount).toBe(0);
  expect(replayBody.storedCount).toBe(3);
  expect(replayBody.replay).toBe("debug_thread_buffer");

  await page.getByTestId("add-debug-agent-pane").click();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");
  await expect(
    page.getByTestId("component-debug-agent-1").filter({ hasText: "Replay Before Connect Chart" }),
  ).toBeVisible();

  const wrongThreadResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-wrong-thread",
      replay: false,
      events: barToolCallEvents("debug-wrong-thread-bar", "Wrong Thread Chart"),
    },
  });
  const wrongThreadBody = (await wrongThreadResponse.json()) as {
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(wrongThreadBody.deliveredCount).toBe(0);
  expect(wrongThreadBody.storedCount).toBe(0);
  expect(wrongThreadBody.replay).toBe("none");
  await expect(page.getByTestId("transcript-debug-agent-1")).not.toContainText("Wrong Thread Chart");

  await page.getByTestId("disconnect-debug-agent-1").click();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("disconnected");
  await expect.poll(() => debugAgentConnectionCount(page, "debug-agent-1")).toBe(0);
  const afterDetachResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      replay: false,
      events: barToolCallEvents("debug-after-detach-bar", "After Detach Chart"),
    },
  });
  const afterDetachBody = (await afterDetachResponse.json()) as { deliveredCount: number };
  expect(afterDetachBody.deliveredCount).toBe(0);
  const afterDetachStatus = (await (await page.request.get("/__houmao_debug_agents/status")).json()) as {
    agents: Array<{ agentId: string; connectionCount: number }>;
  };
  expect(afterDetachStatus.agents.find((agent) => agent.agentId === "debug-agent-1")?.connectionCount ?? 0).toBe(0);

  const replayAgentId = `debug-agent-replay-${Date.now()}`;
  const replayThreadId = `${replayAgentId}-thread`;
  await page.request.post(`/__houmao_debug_agents/${replayAgentId}/v1/ag-ui/events`, {
    data: {
      threadId: replayThreadId,
      events: barToolCallEvents("debug-direct-replay-bar", "Direct Replay Chart"),
    },
  });
  await expect
    .poll(() => readDebugStreamPreview(page, replayAgentId, replayThreadId))
    .toContain("Direct Replay Chart");

  const liveOnlyAgentId = `debug-agent-live-${Date.now()}`;
  const liveOnlyThreadId = `${liveOnlyAgentId}-thread`;
  const liveOnlyResponse = await page.request.post(
    `/__houmao_debug_agents/${liveOnlyAgentId}/v1/ag-ui/events`,
    {
      data: {
        threadId: liveOnlyThreadId,
        replay: false,
        events: barToolCallEvents("debug-live-only-bar", "Live Only Unseen Chart"),
      },
    },
  );
  const liveOnlyBody = (await liveOnlyResponse.json()) as {
    deliveredCount: number;
    storedCount: number;
    replay: string;
  };
  expect(liveOnlyBody.deliveredCount).toBe(0);
  expect(liveOnlyBody.storedCount).toBe(0);
  expect(liveOnlyBody.replay).toBe("none");
  expect(await readDebugStreamPreview(page, liveOnlyAgentId, liveOnlyThreadId)).not.toContain(
    "Live Only Unseen Chart",
  );
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

interface ExpectedRunBody {
  threadId: string;
  message: string;
  canvasSize: { w: number; h: number };
}

interface RecordedProxyRequest {
  target: string | null;
  body: unknown;
}

function collectProxyPostBodies(page: Page): RecordedProxyRequest[] {
  const requests: RecordedProxyRequest[] = [];
  page.on("request", (request) => {
    if (request.method() !== "POST" || !request.url().includes("/__houmao_ag_ui_proxy?")) {
      return;
    }
    const target = new URL(request.url()).searchParams.get("target");
    let body: unknown;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    requests.push({ target, body });
  });
  return requests;
}

async function measuredSurfaceSize(page: Page, paneId: string): Promise<{ w: number; h: number }> {
  const box = await page.getByTestId(`transcript-${paneId}`).boundingBox();
  expect(box).toBeTruthy();
  const w = Math.round(box!.width);
  const h = Math.round(box!.height);
  expect(w).toBeGreaterThan(0);
  expect(h).toBeGreaterThan(0);
  return { w, h };
}

function expectMinimalRunBody(body: unknown, expected: ExpectedRunBody): void {
  const record = expectRecord(body);
  expect(record.threadId).toBe(expected.threadId);
  expect(typeof record.runId).toBe("string");
  expect(record.state).toEqual({});
  expect(record.forwardedProps).toEqual({});
  expect(record.tools).toEqual([]);
  expect(record.context).toEqual([
    {
      description: "houmao.canvas_size_px.v1",
      value: JSON.stringify({
        widthPx: expected.canvasSize.w,
        heightPx: expected.canvasSize.h,
      }),
    },
  ]);
  const messages = Array.isArray(record.messages) ? record.messages : [];
  expect(messages).toHaveLength(1);
  const message = expectRecord(messages[0]);
  expect(message.role).toBe("user");
  expect(message.content).toBe(expected.message);
  expect(JSON.stringify(record.state)).not.toContain("pane");
  expect(JSON.stringify(record.forwardedProps)).not.toContain("pane");
  expect(JSON.stringify(record.context)).not.toContain("agentId");
}

function expectMinimalConnectBody(
  body: Record<string, unknown>,
  options: { allowReplayFlag?: boolean } = {},
): void {
  expect(typeof body.threadId).toBe("string");
  expect(typeof body.runId).toBe("string");
  expect(body.state).toEqual({});
  expect(body.context).toEqual([]);
  expect(body.tools).toEqual([]);
  expect(body.forwardedProps).toEqual({});
  expect(body.messages).toEqual([]);
  const allowedKeys = new Set([
    "threadId",
    "runId",
    "state",
    "messages",
    "tools",
    "context",
    "forwardedProps",
  ]);
  if (options.allowReplayFlag) {
    allowedKeys.add("replay");
  }
  for (const key of Object.keys(body)) {
    expect(allowedKeys.has(key), `unexpected connect body key ${key}`).toBeTruthy();
  }
  expect(JSON.stringify(body.state)).not.toContain("pane");
  expect(JSON.stringify(body.forwardedProps)).not.toContain("source");
}

function expectRecord(value: unknown): Record<string, unknown> {
  expect(typeof value).toBe("object");
  expect(value).not.toBeNull();
  expect(Array.isArray(value)).toBeFalsy();
  return value as Record<string, unknown>;
}

function barToolCallEvents(toolCallId: string, title: string): Array<Record<string, unknown>> {
  return [
    {
      type: "TOOL_CALL_START",
      toolCallId,
      toolCallName: "houmao.chart.bar",
      parentMessageId: `${toolCallId}-message`,
    },
    {
      type: "TOOL_CALL_ARGS",
      toolCallId,
      delta: JSON.stringify({
        schemaVersion: 1,
        title,
        subtitle: "Playwright debug relay proof",
        xLabel: "Segment",
        yLabel: "Value",
        data: [
          { label: "A", value: 12, color: "#79a35d" },
          { label: "B", value: 21, color: "#d3a749" },
          { label: "C", value: 16, color: "#6aa6b8" },
        ],
      }),
    },
    {
      type: "TOOL_CALL_END",
      toolCallId,
    },
  ];
}

async function readDebugStreamPreview(page: Page, agentId: string, threadId: string): Promise<string> {
  return page.evaluate(
    async ({ agentId: browserAgentId, threadId: browserThreadId }) => {
      const controller = new AbortController();
      const response = await fetch(
        `/__houmao_debug_agents/${encodeURIComponent(browserAgentId)}/v1/ag-ui/connect`,
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify({
            threadId: browserThreadId,
            runId: `preview-${browserAgentId}`,
          }),
          signal: controller.signal,
        },
      );
      if (!response.body) {
        throw new Error("Debug stream response had no body.");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      const deadline = Date.now() + 350;
      while (Date.now() < deadline) {
        const remaining = Math.max(1, deadline - Date.now());
        const result = await Promise.race([
          reader.read(),
          new Promise<null>((resolve) => {
            window.setTimeout(() => resolve(null), remaining);
          }),
        ]);
        if (!result) {
          break;
        }
        if (result.done) {
          break;
        }
        text += decoder.decode(result.value, { stream: true });
      }
      controller.abort();
      await reader.cancel().catch(() => undefined);
      return text;
    },
    { agentId, threadId },
  );
}

async function debugAgentConnectionCount(page: Page, agentId: string): Promise<number> {
  const response = await page.request.get("/__houmao_debug_agents/status");
  const body = (await response.json()) as {
    agents: Array<{ agentId: string; connectionCount: number }>;
  };
  return body.agents.find((agent) => agent.agentId === agentId)?.connectionCount ?? 0;
}

async function readOnlyTmuxSocketRejectsInput(page: Page): Promise<boolean> {
  return page.evaluate(
    () =>
      new Promise<boolean>((resolve) => {
        const url = new URL("/__houmao_tmux/attach", window.location.href);
        url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
        const socket = new WebSocket(url.toString());
        const timer = window.setTimeout(() => {
          socket.close();
          resolve(false);
        }, 1500);
        const finish = (result: boolean) => {
          window.clearTimeout(timer);
          socket.close();
          resolve(result);
        };
        socket.addEventListener("open", () => {
          socket.send(
            JSON.stringify({
              type: "attach",
              sessionName: "houmao-alpha",
              mode: "read-only",
              cols: 80,
              rows: 24,
            }),
          );
        });
        socket.addEventListener("message", (event) => {
          const data = String(event.data);
          if (data.includes('"type":"attached"')) {
            socket.send(JSON.stringify({ type: "input", data: "crafted-read-only-input" }));
            return;
          }
          if (data.includes("tmux_read_only")) {
            finish(true);
          }
        });
        socket.addEventListener("error", () => finish(false));
      }),
  );
}

async function browserPersistenceText(page: Page): Promise<string> {
  return page.evaluate(async () => {
    const localStorageText = Object.entries(window.localStorage)
      .map(([key, value]) => `${key}:${value}`)
      .join("\n");
    const indexedDbWithDatabases = window.indexedDB as IDBFactory & {
      databases?: () => Promise<Array<{ name?: string }>>;
    };
    const databaseNames = indexedDbWithDatabases.databases
      ? (await indexedDbWithDatabases.databases()).map((database) => database.name ?? "")
      : [];
    return [localStorageText, databaseNames.join("\n")].join("\n");
  });
}

async function panelIds(page: Page): Promise<string[]> {
  return page.evaluate(() => window.__HMWB_TEST__!.panelIds().sort());
}

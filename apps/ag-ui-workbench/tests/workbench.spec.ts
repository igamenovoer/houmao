import { expect, test, type Locator, type Page } from "@playwright/test";

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
  await page.request.post("/__houmao_workbench/ag-ui/streams/close-all").catch(() => undefined);
  fakeServer.resetRecords();
  await page.goto("/");
  await page.request.post("/__houmao_tmux/fixture/reset");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
});

test("submits minimal run and connect request bodies", async ({ page }) => {
  const bridgeRequests = collectAgUiBridgePostBodies(page);

  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect.poll(() => panelIds(page)).toEqual([]);

  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Manual Operator", fakeServer.targetBase("operator"), "operator-thread");
  await page.getByTestId("connect-agent-1").click();
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "operator").length).toBe(1);
  expectMinimalConnectBody(fakeServer.connects.find((connect) => connect.target === "operator")!.body);

  await page.getByTestId("prompt-agent-1").fill("operator canvas prompt");
  await expectSurfaceHasPositiveSize(page, "agent-1");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("operator-only-run-evidence");
  const operatorRun = fakeServer.runs.find((run) => run.target === "operator");
  expect(operatorRun).toBeTruthy();
  expectMinimalRunBody(operatorRun!.body, {
    threadId: "operator-thread",
    message: "operator canvas prompt",
  });

  await addBlankAgentPane(page);
  await configurePane(page, "agent-2", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");
  await page.getByTestId("connect-agent-2").click();
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBe(1);
  const agentConnect = fakeServer.connects.find((connect) => connect.target === "alpha");
  expect(agentConnect).toBeTruthy();
  expectMinimalConnectBody(agentConnect!.body);

  await page.getByTestId("prompt-agent-2").fill("agent canvas prompt");
  await expectSurfaceHasPositiveSize(page, "agent-2");
  await page.getByTestId("run-agent-2").click();
  await expect(page.getByTestId("transcript-agent-2")).toContainText("alpha-run-evidence");
  const agentRun = fakeServer.runs.find((run) => run.target === "alpha");
  expect(agentRun).toBeTruthy();
  expectMinimalRunBody(agentRun!.body, {
    threadId: "alpha-thread",
    message: "agent canvas prompt",
  });

  await page.getByTestId("add-debug-agent-pane").click();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");
  const debugConnect = bridgeRequests.find(
    (request) =>
      request.operation === "connect" &&
      request.target?.includes("/__houmao_debug_agents/debug-agent-1/v1/ag-ui"),
  );
  expect(debugConnect).toBeTruthy();
  expectMinimalConnectBody(expectRecord(debugConnect!.body), { allowReplayFlag: true });
});

test("prompt editors submit with Shift+Enter and keep plain Enter multiline", async ({ page }) => {
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Manual", fakeServer.targetBase("manual"), "manual-thread");

  const prompt = page.getByTestId("prompt-agent-1");
  await prompt.fill("line one");
  await prompt.press("Enter");
  await expect(prompt).toHaveValue("line one\n");
  expect(fakeServer.runs).toHaveLength(0);

  await prompt.fill("shortcut agent prompt");
  await expectSurfaceHasPositiveSize(page, "agent-1");
  await prompt.press("Shift+Enter");
  await expect(page.getByTestId("transcript-agent-1")).toContainText("manual-run-evidence");
  await expect(prompt).toHaveValue("");
  const manualRun = fakeServer.runs.find((run) => run.target === "manual");
  expect(manualRun).toBeTruthy();
  expectMinimalRunBody(manualRun!.body, {
    threadId: "manual-thread",
    message: "shortcut agent prompt",
  });

  const runCount = fakeServer.runs.length;
  await prompt.fill("   ");
  await prompt.press("Shift+Enter");
  await page.waitForTimeout(100);
  expect(fakeServer.runs).toHaveLength(runCount);
  await expect(prompt).toHaveValue("   ");

  await page.getByTestId("add-debug-agent-pane").click();
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");
  const debugEditor = page.getByTestId("debug-editor-debug-agent-1");
  const debugResponse = page.getByTestId("debug-response-debug-agent-1");
  await debugEditor.fill("   ");
  await debugEditor.press("Shift+Enter");
  await page.waitForTimeout(100);
  await expect(debugResponse).toContainText("No message has been sent.");

  await debugEditor.fill(
    JSON.stringify(
      {
        schemaVersion: 2,
        chartType: "bar",
        renderer: { preferred: "plotly" },
        title: "Shift Enter Debug Chart",
        traces: [{ type: "bar", x: ["A"], y: [7] }],
      },
      null,
      2,
    ),
  );
  await debugEditor.press("Shift+Enter");
  await expect(debugResponse).toContainText('"status": "accepted"');
  await expect(page.getByTestId("component-debug-agent-1")).toContainText("Shift Enter Debug Chart");
});

test("validates docked multi-pane isolation, graphics, detach, and persistence", async ({ page, context }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("proxy-status")).toContainText("loopback proxy ready");

  await addBlankAgentPane(page);
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");
  await configurePane(page, "agent-2", "Beta", fakeServer.targetBase("beta"), "beta-thread");
  await page.getByTestId("split-right-agent-2").click();

  await page.getByTestId("connect-agent-1").click();
  await page.getByTestId("connect-agent-2").click();
  await expect
    .poll(() => fakeServer.connects.map((connect) => connect.target).sort())
    .toEqual(["alpha", "beta"]);
  await expect(page.getByTestId("status-agent-1")).toContainText("connected");
  await expect(page.getByTestId("status-agent-2")).toContainText("connected");

  await page.getByTestId("prompt-agent-1").fill("render alpha graphic");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("alpha-run-evidence");
  await page.getByTestId("message-info-agent-1-alpha-assistant").click();
  await expect(page.getByTestId("message-diagnostics-agent-1")).toBeVisible();
  await expect(page.getByTestId("raw-agent-1")).toContainText("TEXT_MESSAGE_CONTENT");
  await expect(page.getByTestId("raw-agent-1")).toContainText("alpha-run-evidence");
  await page.getByTestId("message-diagnostics-close-agent-1").click();
  await expect(page.getByTestId("graphic-agent-1")).toContainText("Alpha SVG Graphic");
  await expect(page.getByTestId("graphic-agent-1")).toContainText("Alpha graphic alt text");
  await expect(page.getByTestId("graphic-agent-1").locator("svg")).toContainText("alpha svg content");
  await expect(page.getByTestId("transcript-agent-1")).toContainText("Alpha Dashboard");
  await expect(page.getByTestId("component-dashboard-agent-1")).toBeVisible();
  await expect(page.getByTestId("component-metric-grid-agent-1")).toContainText("Pass rate");
  await expect(page.getByTestId("template-chart-plotly-agent-1").first()).toBeVisible();
  await expect(page.getByTestId("component-table-agent-1")).toContainText("Alpha count");
  const alphaTemplateFrame = page.getByTestId("component-agent-1").filter({ hasText: "Alpha Template Graphic" });
  const alphaTemplateChart = alphaTemplateFrame.getByTestId("template-chart-plotly-agent-1");
  await expect(alphaTemplateFrame).toBeVisible();
  await expect(alphaTemplateChart).toBeVisible();
  await expect(alphaTemplateChart.locator("svg").first()).toBeVisible();
  const alphaVegaFrame = page.getByTestId("component-agent-1").filter({ hasText: "Alpha Vega-Lite Graphic" });
  await expect(alphaVegaFrame).toBeVisible();
  await expectVegaChartVisible(alphaVegaFrame.getByTestId("vega-lite-chart-agent-1"));

  await page.getByTestId("prompt-agent-1").fill("prompt survives clear");
  const detachesBeforeClear = fakeServer.detaches.length;
  await page.getByTestId("clear-canvas-agent-1").click();
  await expect(page.getByTestId("graphic-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("component-dashboard-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("template-chart-plotly-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("vega-lite-chart-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("transcript-agent-1")).not.toContainText("alpha-run-evidence");
  await expect(page.getByTestId("message-diagnostics-agent-1")).toHaveCount(0);
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
  await expect(
    page.getByTestId("invalid-component-agent-2").filter({ hasText: "traces must be a non-empty array" }),
  ).toBeVisible();
  await expect(page.getByTestId("invalid-component-agent-2").filter({ hasText: "spec.data.url" })).toBeVisible();
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

test("agent pane renders Plotly templates and diagnostic-only unsupported payloads", async ({ page }) => {
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");

  const rendererLabel = page.getByTestId("template-renderer-agent-1");
  await expect(rendererLabel).toContainText("Plotly");
  await expect(rendererLabel.locator("select")).toHaveCount(0);
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("watch-strip-agent-1")).toContainText("Watched");

  await page.getByTestId("prompt-agent-1").fill("plotly template graphic");
  await page.getByTestId("run-agent-1").click();
  const autoFrame = page.getByTestId("component-agent-1").filter({ hasText: "Alpha Template Graphic" });
  await expect(autoFrame.getByTestId("template-chart-plotly-agent-1").locator("svg").first()).toBeVisible();
  await expectPlotlyChartToFillContainer(autoFrame.getByTestId("template-chart-plotly-agent-1"));

  await page.getByTestId("clear-canvas-agent-1").click();
  for (const chartType of ["line", "scatter", "pie", "histogram"] as const) {
    const title = `Plotly ${chartType} Template Graphic`;
    const response = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
      data: {
        threadId: "alpha-thread",
        events: templateToolCallEvents(`plotly-${chartType}-template`, title, { chartType }),
      },
    });
    expect(response.ok()).toBeTruthy();
    const frame = page.getByTestId("component-agent-1").filter({ hasText: title });
    await expect(frame.getByTestId("template-chart-plotly-agent-1").locator("svg").first()).toBeVisible();
  }

  const datasourceResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: templateToolCallEvents("datasource-template", "Datasource Template Graphic", { datasource: true }),
    },
  });
  expect(datasourceResponse.ok()).toBeTruthy();
  await expect(page.getByTestId("invalid-component-agent-1")).toContainText(
    "Datasource materialization is not supported yet",
  );
  await expect(page.getByTestId("invalid-component-agent-1")).toContainText("Datasource Template Graphic");

  const retiredResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: retiredBarToolCallEvents("retired-bar", "Retired Bar Chart"),
    },
  });
  expect(retiredResponse.ok()).toBeTruthy();
  await expect(page.getByTestId("unknown-component-agent-1")).toContainText("houmao.chart.bar");
});

test("agent pane renders Vega-Lite, shows fallback, and clears the Vega view", async ({ page }) => {
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");
  await page.getByTestId("connect-agent-1").click();
  await expect(page.getByTestId("status-agent-1")).toContainText("connected");

  const validResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: vegaliteToolCallEvents("vega-normal-valid", "Normal Vega-Lite Graphic"),
    },
  });
  expect(validResponse.ok()).toBeTruthy();
  const validFrame = page.getByTestId("component-agent-1").filter({ hasText: "Normal Vega-Lite Graphic" });
  await expect(validFrame).toBeVisible();
  await expectVegaChartVisible(validFrame.getByTestId("vega-lite-chart-agent-1"));

  const detachesBeforeClear = fakeServer.detaches.length;
  await page.getByTestId("clear-canvas-agent-1").click();
  await expect(page.getByTestId("vega-lite-chart-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("status-agent-1")).toContainText("connected");
  expect(fakeServer.detaches).toHaveLength(detachesBeforeClear);

  const remoteResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: vegaliteToolCallEvents("vega-normal-remote", "Remote Vega-Lite Graphic", {
        remoteData: true,
      }),
    },
  });
  expect(remoteResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-agent-1").filter({ hasText: "Remote Vega-Lite Graphic" }),
  ).toContainText("spec.data.url");

  const laterResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: vegaliteToolCallEvents("vega-normal-later", "Later Vega-Lite Graphic"),
    },
  });
  expect(laterResponse.ok()).toBeTruthy();
  const laterFrame = page.getByTestId("component-agent-1").filter({ hasText: "Later Vega-Lite Graphic" });
  await expect(laterFrame).toBeVisible();
  await expectVegaChartVisible(laterFrame.getByTestId("vega-lite-chart-agent-1"));
});

test("sanitizes legacy stored template renderer values to Plotly", async ({ page }) => {
  await addBlankAgentPane(page);
  await expect(page.getByTestId("template-renderer-agent-1")).toContainText("Plotly");
  expect(
    await page.evaluate(
      () => window.__HMWB_TEST__!.storage().panes["agent-1"].presentation?.templateGraphicBackend,
    ),
  ).toBe("plotly");

  await page.evaluate(() => {
    const current = window.__HMWB_TEST__!.storage() as any;
    current.panes["agent-1"].presentation = { templateGraphicBackend: "legacy-multi-renderer" };
    window.localStorage.setItem("houmao.agUiWorkbench.v1", JSON.stringify(current));
  });
  await page.reload();

  await expect(page.getByTestId("template-renderer-agent-1")).toContainText("Plotly");
  expect(
    await page.evaluate(
      () => window.__HMWB_TEST__!.storage().panes["agent-1"].presentation?.templateGraphicBackend,
    ),
  ).toBe("plotly");
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

  await addBlankAgentPane(page);
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

  await expect.poll(() => fakeServer.connects.filter((entry) => entry.target === "alpha").length).toBe(1);
  const connect = fakeServer.connects.find((entry) => entry.target === "alpha");
  expect(connect).toBeTruthy();
  expectMinimalConnectBody(connect!.body);

  await page.getByTestId("prompt-agent-1").fill("operator marked request stays minimal");
  await expectSurfaceHasPositiveSize(page, "agent-1");
  await page.getByTestId("run-agent-1").click();
  await expect(page.getByTestId("transcript-agent-1")).toContainText("alpha-run-evidence");
  const run = fakeServer.runs.find((entry) => entry.target === "alpha");
  expect(run).toBeTruthy();
  expectMinimalRunBody(run!.body, {
    threadId: "alpha-thread",
    message: "operator marked request stays minimal",
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
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Manual", "http://example.com/v1/ag-ui", "agent-thread");
  await page.getByTestId("capabilities-agent-1").click();
  await expect(page.getByTestId("errors-agent-1")).toContainText("target_policy_rejected");
});

test("lists discovered agents, retargets panes, opens new panes, and keeps manual fallback", async ({ page }) => {
  await addBlankAgentPane(page);
  await configurePane(page, "agent-1", "Manual", fakeServer.targetBase("manual"), "manual-thread");
  await page.getByTestId("connect-agent-1").click();
  await expect.poll(() => fakeServer.connects.filter((entry) => entry.target === "manual").length).toBe(1);

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
  await expect.poll(() => fakeServer.connects.filter((entry) => entry.target === "alpha").length).toBe(1);
  await expect
    .poll(() => fakeServer.activeThreadUpdates.filter((entry) => entry.target === "alpha"))
    .toContainEqual({ target: "alpha", threadId: "alpha-thread", source: "gui_connect" });

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
  await expect.poll(() => fakeServer.connects.filter((entry) => entry.target === "beta").length).toBe(1);
  await expect
    .poll(() => fakeServer.activeThreadUpdates.filter((entry) => entry.target === "beta"))
    .toContainEqual({ target: "beta", threadId: "beta-thread", source: "gui_connect" });

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

test("agents picker auto-refreshes and creates blank panes from New", async ({ page }) => {
  await expect(page.getByTestId("add-agent-pane")).toHaveCount(0);

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await expect(page.getByTestId("agent-row-alpha")).toBeVisible();
  await expect(page.getByTestId("agent-row-beta")).toBeVisible();
  const connectsBeforeBlankPane = fakeServer.connects.length;
  const activeUpdatesBeforeBlankPane = fakeServer.activeThreadUpdates.length;
  await page.getByTestId("new-agent-pane").click();

  await expect(page.getByTestId("panel-agent-1")).toBeVisible();
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue("");
  expect(fakeServer.connects).toHaveLength(connectsBeforeBlankPane);
  expect(fakeServer.activeThreadUpdates).toHaveLength(activeUpdatesBeforeBlankPane);
  await expect.poll(() => page.evaluate(() => window.__HMWB_TEST__!.watchedTargetKeys())).toEqual([]);

  await page.getByTestId("choose-agent-agent-1").click();
  await expect(page.getByTestId("agent-row-alpha")).toBeVisible();
  const connectsBeforeSecondBlankPane = fakeServer.connects.length;
  const activeUpdatesBeforeSecondBlankPane = fakeServer.activeThreadUpdates.length;
  await page.getByTestId("new-agent-pane").click();

  await expect(page.getByTestId("panel-agent-2")).toBeVisible();
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue("");
  expect(fakeServer.connects).toHaveLength(connectsBeforeSecondBlankPane);
  expect(fakeServer.activeThreadUpdates).toHaveLength(activeUpdatesBeforeSecondBlankPane);
});

test("marks active thread only by user action or connect for discovered agent panes", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("select-agent-alpha").click();

  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBe(1);
  await expect
    .poll(() => fakeServer.activeThreadUpdates.filter((update) => update.target === "alpha"))
    .toContainEqual({ target: "alpha", threadId: "alpha-thread", source: "gui_connect" });
  await expect(page.getByTestId("active-thread-marker-agent-1")).toContainText("Active thread");

  const externalActive = await page.request.put(`${fakeServer.targetBase("alpha")}/active-thread`, {
    data: { threadId: "external-thread", source: "manual" },
  });
  expect(externalActive.ok()).toBeTruthy();
  await expect(page.getByTestId("active-thread-marker-agent-1")).toContainText("Inactive thread");

  await page.getByTestId("mark-active-thread-agent-1").click();
  await expect
    .poll(() => fakeServer.activeThreadUpdates.filter((update) => update.target === "alpha"))
    .toContainEqual({ target: "alpha", threadId: "alpha-thread", source: "gui_button" });
  await expect(page.getByTestId("active-thread-marker-agent-1")).toContainText("Active thread");

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("watch-agent-beta").click();
  await expect.poll(() => fakeServer.connects.some((connect) => connect.target === "beta")).toBeTruthy();
  expect(fakeServer.activeThreadUpdates.some((update) => update.target === "beta")).toBeFalsy();
  await page.getByTestId("close-agent-picker").click();
  await expect(page.getByTestId("agent-picker")).toHaveCount(0);

  await page.getByTestId("close-agent-1").click();
  await expect(page.getByTestId("panel-agent-1")).toHaveCount(0);
  await expect
    .poll(() => fakeServer.activeThreadClears)
    .toContainEqual({ target: "alpha", expectedThreadId: "alpha-thread" });
  expect(fakeServer.activeThreadClears.some((clear) => clear.target === "beta")).toBeFalsy();
});

test("shows unsupported active-thread state for discovered gateways without active-thread route", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("select-agent-legacy").click();

  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("legacy"));
  await expect(page.getByTestId("active-thread-marker-agent-1")).toContainText("Active-thread unsupported");
  await expect(page.getByTestId("active-thread-marker-agent-1")).toContainText("unsupported");
  await expect(page.getByTestId("active-thread-marker-agent-1")).not.toContainText("Inactive thread");
  await expect(page.getByTestId("mark-active-thread-agent-1")).toBeDisabled();
  await expect.poll(() => fakeServer.connects.some((connect) => connect.target === "legacy")).toBeTruthy();
  expect(fakeServer.activeThreadUpdates.some((update) => update.target === "legacy")).toBeFalsy();
});

test("opens tmux tab, filters sessions, attaches, rejects read-only input, and avoids persistence", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("close-agent-picker").click();

  await page.getByTestId("add-tmux-pane").click();
  await expect(page.getByTestId("panel-tmux-1")).toBeVisible();
  await expect(page.getByTestId("tmux-session-list-tmux-1")).toHaveCount(0);
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
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
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
  await expect(page.getByTestId("tmux-session-utility-shell")).toBeVisible();
  await page.getByTestId("tmux-search-tmux-1").fill("");

  await page.getByTestId("tmux-session-houmao-alpha").click();
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture attached houmao-alpha");
  await page.getByTestId("tmux-terminal-tmux-1").click();
  await page.keyboard.type("rw-fixture-input");
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture input");

  await page.getByTestId("tmux-detach-tmux-1").click();
  await page.getByTestId("tmux-read-only-tmux-1").check();
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
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

test("tmux tab refits on resize and removes dead fixture sessions", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("close-agent-picker").click();

  await page.getByTestId("add-tmux-pane").click();
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toBeVisible();
  const initialHeight = await elementHeight(page, "tmux-terminal-tmux-1");

  await page.getByTestId("tmux-session-houmao-alpha").click();
  await expect(page.getByTestId("tmux-terminal-tmux-1")).toContainText("fixture attached houmao-alpha");
  const panelBox = await page.getByTestId("panel-tmux-1").boundingBox();
  const terminalBox = await page.getByTestId("tmux-terminal-tmux-1").boundingBox();
  expect(panelBox).toBeTruthy();
  expect(terminalBox).toBeTruthy();
  expect(terminalBox!.width).toBeGreaterThan(panelBox!.width - 40);
  await page.setViewportSize({ width: 1280, height: 900 });
  await expect.poll(() => elementHeight(page, "tmux-terminal-tmux-1")).toBeGreaterThan(initialHeight + 50);

  await page.request.delete("/__houmao_tmux/fixture/sessions/houmao-alpha");
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
  await expect(page.getByTestId("tmux-session-houmao-alpha")).toHaveCount(0);
});

test("tmux tab repaints visible scrollback after mouse-wheel scrolling", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("close-agent-picker").click();

  await page.getByTestId("add-tmux-pane").click();
  await page.getByTestId("tmux-picker-toggle-tmux-1").click();
  await page.getByTestId("tmux-session-houmao-alpha").click();
  const terminal = page.getByTestId("tmux-terminal-tmux-1");
  await expect(terminal).toContainText("fixture attached houmao-alpha");
  await terminal.click();
  for (let index = 0; index < 70; index += 1) {
    await page.keyboard.insertText(`scrollback-${String(index).padStart(2, "0")}\n`);
  }
  await expect(terminal).toContainText("scrollback-69");

  const beforeScrollBox = await terminal.boundingBox();
  expect(beforeScrollBox).toBeTruthy();
  await terminal.hover();
  await page.mouse.wheel(0, -2500);
  await expect.poll(() => visibleScrollbackMinIndex(terminal)).toBeLessThan(50);
  const afterScrollBox = await terminal.boundingBox();
  expect(afterScrollBox).toBeTruthy();
  expect(Math.round(afterScrollBox!.width)).toBe(Math.round(beforeScrollBox!.width));
  expect(Math.round(afterScrollBox!.height)).toBe(Math.round(beforeScrollBox!.height));

  await page.mouse.wheel(0, 2500);
  await expect.poll(() => visibleScrollbackMaxIndex(terminal)).toBeGreaterThan(65);
});

test("surfaces target policy errors for disallowed passive-server discovery", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill("http://example.com");
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("picker-error")).toContainText("target_policy_rejected");
});

test("reconnects discovered pane through passive resolution after gateway restart", async ({ page }) => {
  await addBlankAgentPane(page);
  await page.getByTestId("choose-agent-agent-1").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-alpha").dblclick();

  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBe(1);
  const firstGatewayUrl = await page.getByTestId("target-url-agent-1").inputValue();

  await fakeServer.restartGateway("alpha");

  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBeGreaterThan(1);
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

  await expect(page.getByTestId("watch-strip-agent-1")).toContainText("Watched");
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBe(1);

  const publishResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: templateToolCallEvents("watched-cache-chart", "Watched Cache Chart"),
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
  await expect(page.getByTestId("template-chart-plotly-agent-1").first().locator("svg").first()).toBeVisible();

  await page.getByTestId("close-agent-1").click();
  await expect(page.getByTestId("panel-agent-1")).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.__HMWB_TEST__!.watchedTargetKeys().length)).toBe(1);

  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("watch-state-alpha")).toContainText("connected");
  await page.getByTestId("open-watched-agent-alpha").click();

  await expect(page.getByTestId("panel-agent-2")).toBeVisible();
  await expect(page.getByTestId("component-agent-2")).toContainText("Watched Cache Chart");
  await expect(page.getByTestId("template-chart-plotly-agent-2").first().locator("svg").first()).toBeVisible();
});

test("clear canvas clears watched cache without detaching and accepts future live events", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill(fakeServer.passiveBase());
  await page.getByTestId("refresh-agents").click();
  await page.getByTestId("agent-row-alpha").dblclick();
  await expect(page.getByTestId("watch-strip-agent-1")).toContainText("Watched");
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "alpha").length).toBe(1);

  const staleResponse = await page.request.post(`${fakeServer.targetBase("alpha")}/events`, {
    data: {
      threadId: "alpha-thread",
      events: templateToolCallEvents("watched-clear-stale-chart", "Watched Clear Stale Chart"),
    },
  });
  expect(staleResponse.ok()).toBeTruthy();
  expect((await staleResponse.json()) as { deliveredCount: number }).toMatchObject({
    deliveredCount: 3,
  });
  await expect(page.getByTestId("component-agent-1")).toContainText("Watched Clear Stale Chart");
  await expect(page.getByTestId("template-chart-plotly-agent-1").first().locator("svg").first()).toBeVisible();

  const detachesBeforeClear = fakeServer.detaches.length;
  await page.getByTestId("clear-canvas-agent-1").click();
  await expect(page.getByTestId("component-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("message-diagnostics-agent-1")).toHaveCount(0);
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
      events: templateToolCallEvents("watched-clear-fresh-chart", "Watched Clear Fresh Chart"),
    },
  });
  expect(freshResponse.ok()).toBeTruthy();
  expect((await freshResponse.json()) as { deliveredCount: number }).toMatchObject({
    deliveredCount: 3,
  });
  await expect(page.getByTestId("component-agent-2")).toContainText("Watched Clear Fresh Chart");
  await expect(page.getByTestId("template-chart-plotly-agent-2").first().locator("svg").first()).toBeVisible();
});

test("events published while unwatched are live-only and not recovered later", async ({ page }) => {
  const publishResponse = await page.request.post(`${fakeServer.targetBase("beta")}/events`, {
    data: {
      threadId: "beta-thread",
      events: templateToolCallEvents("missed-live-chart", "Missed Live-Only Chart"),
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
  await expect.poll(() => fakeServer.connects.filter((connect) => connect.target === "beta").length).toBe(1);
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
      events: templateToolCallEvents("debug-live-bar", "External Live Chart"),
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

  const liveFrame = page.getByTestId("component-debug-agent-1").filter({ hasText: "External Live Chart" });
  await expect(liveFrame).toBeVisible();
  const chart = liveFrame.getByTestId("template-chart-plotly-debug-agent-1");
  await expect(chart).toBeVisible();
  await expect(chart.locator("svg").first()).toBeVisible();
  await expectPlotlyChartToFillContainer(chart);

  const templateResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: templateToolCallEvents("debug-live-template", "External Template Graphic"),
    },
  });
  expect(templateResponse.ok()).toBeTruthy();
  const templateFrame = page.getByTestId("component-debug-agent-1").filter({ hasText: "External Template Graphic" });
  await expect(templateFrame).toBeVisible();
  await expect(templateFrame.getByTestId("template-chart-plotly-debug-agent-1").locator("svg").first()).toBeVisible();

  await page.getByTestId("debug-component-debug-agent-1").selectOption("houmao.graphic.vegalite");
  await expect(page.getByTestId("debug-editor-debug-agent-1")).toContainText("Debug Agent Vega-Lite Graphic");
  await page.getByTestId("debug-validate-debug-agent-1").click();
  await expect(page.getByTestId("debug-response-debug-agent-1")).toContainText('"status": "validated"');
  await page.getByTestId("debug-load-remote-vega-debug-agent-1").click();
  await page.getByTestId("debug-validate-debug-agent-1").click();
  await expect(page.getByTestId("debug-response-debug-agent-1")).toContainText(
    '"code": "component_validation_failed"',
  );
  await expect(page.getByTestId("debug-response-debug-agent-1")).toContainText("spec.data.url");

  const vegaResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: vegaliteToolCallEvents("debug-live-vega", "External Vega-Lite Graphic"),
    },
  });
  expect(vegaResponse.ok()).toBeTruthy();
  const vegaBody = (await vegaResponse.json()) as { deliveredCount: number; acceptedCount: number };
  expect(vegaBody.acceptedCount).toBe(3);
  expect(vegaBody.deliveredCount).toBeGreaterThan(0);
  const vegaFrame = page.getByTestId("component-debug-agent-1").filter({ hasText: "External Vega-Lite Graphic" });
  await expect(vegaFrame).toBeVisible();
  await expectVegaChartVisible(vegaFrame.getByTestId("vega-lite-chart-debug-agent-1"));

  const remoteVegaResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: vegaliteToolCallEvents("debug-remote-vega", "Remote Debug Vega-Lite Graphic", {
        remoteData: true,
      }),
    },
  });
  expect(remoteVegaResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-debug-agent-1").filter({ hasText: "Remote Debug Vega-Lite Graphic" }),
  ).toContainText("spec.data.url");

  const laterVegaResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: vegaliteToolCallEvents("debug-later-vega", "Later Debug Vega-Lite Graphic"),
    },
  });
  expect(laterVegaResponse.ok()).toBeTruthy();
  const laterVegaFrame = page
    .getByTestId("component-debug-agent-1")
    .filter({ hasText: "Later Debug Vega-Lite Graphic" });
  await expect(laterVegaFrame).toBeVisible();
  await expectVegaChartVisible(laterVegaFrame.getByTestId("vega-lite-chart-debug-agent-1"));

  await page.getByTestId("debug-clear-debug-agent-1").click();
  await expect(page.getByTestId("vega-lite-chart-debug-agent-1")).toHaveCount(0);
  await expect(page.getByTestId("status-debug-agent-1")).toContainText("connected");

  const fallbackResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: templateToolCallEvents("debug-template-fallback", "Fallback Template Graphic", {
        rendererPreferred: "not-installed",
      }),
    },
  });
  expect(fallbackResponse.ok()).toBeTruthy();
  const fallbackFrame = page.getByTestId("invalid-component-debug-agent-1").filter({
    hasText: "Fallback Template Graphic",
  });
  await expect(fallbackFrame).toBeVisible();
  await expect(fallbackFrame).toContainText("renderer.preferred must be plotly");

  const invalidTemplateResponse = await page.request.post("/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events", {
    data: {
      threadId: "debug-agent-1-thread",
      events: templateToolCallEvents("debug-invalid-template", "Invalid Template Graphic", {
        omitY: true,
      }),
    },
  });
  expect(invalidTemplateResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-debug-agent-1").filter({ hasText: "traces.0 requires y" }),
  ).toBeVisible();

  const unsupportedAreaResponse = await page.request.post(
    "/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events",
    {
      data: {
        threadId: "debug-agent-1-thread",
        events: templateToolCallEvents("debug-unsupported-area", "Unsupported Area Template", {
          chartTypeOverride: "area",
        }),
      },
    },
  );
  expect(unsupportedAreaResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-debug-agent-1").filter({ hasText: "chartType must be one of" }),
  ).toBeVisible();

  const unsupported3dResponse = await page.request.post(
    "/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events",
    {
      data: {
        threadId: "debug-agent-1-thread",
        events: templateToolCallEvents("debug-unsupported-3d", "Unsupported 3D Template", {
          chartTypeOverride: "scatter3d",
        }),
      },
    },
  );
  expect(unsupported3dResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-debug-agent-1").filter({ hasText: "Unsupported 3D Template" }),
  ).toContainText("chartType must be one of");

  const unsupportedTraceResponse = await page.request.post(
    "/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events",
    {
      data: {
        threadId: "debug-agent-1-thread",
        events: templateToolCallEvents("debug-unsupported-trace", "Unsupported Trace Template", {
          traceTypeOverride: "scatter",
        }),
      },
    },
  );
  expect(unsupportedTraceResponse.ok()).toBeTruthy();
  await expect(
    page.getByTestId("invalid-component-debug-agent-1").filter({ hasText: "Unsupported Trace Template" }),
  ).toContainText("traces.0.type must be one of bar");

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
      events: templateToolCallEvents("debug-replay-bar", "Replay Before Connect Chart"),
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
      events: templateToolCallEvents("debug-wrong-thread-bar", "Wrong Thread Chart"),
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
      events: templateToolCallEvents("debug-after-detach-bar", "After Detach Chart"),
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
      events: templateToolCallEvents("debug-direct-replay-bar", "Direct Replay Chart"),
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
        events: templateToolCallEvents("debug-live-only-bar", "Live Only Unseen Chart"),
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

async function addBlankAgentPane(page: Page): Promise<void> {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("new-agent-pane").click();
}

interface ExpectedRunBody {
  threadId: string;
  message: string;
}

interface RecordedBridgeRequest {
  target: string | null;
  operation: string;
  body: unknown;
}

function collectAgUiBridgePostBodies(page: Page): RecordedBridgeRequest[] {
  const requests: RecordedBridgeRequest[] = [];
  page.on("request", (request) => {
    if (request.method() !== "POST" || !request.url().includes("/__houmao_workbench/ag-ui/")) {
      return;
    }
    let payload: unknown;
    try {
      payload = request.postDataJSON();
    } catch {
      payload = request.postData();
    }
    const operation = new URL(request.url()).pathname.split("/").pop() ?? "";
    const record = expectRecord(payload);
    const target = typeof record.targetUrl === "string" ? record.targetUrl : null;
    const body = record.input ?? payload;
    requests.push({ target, operation, body });
  });
  return requests;
}

async function expectSurfaceHasPositiveSize(page: Page, paneId: string): Promise<void> {
  const box = await page.getByTestId(`transcript-${paneId}`).boundingBox();
  expect(box).toBeTruthy();
  const w = Math.round(box!.width);
  const h = Math.round(box!.height);
  expect(w).toBeGreaterThan(0);
  expect(h).toBeGreaterThan(0);
}

async function elementHeight(page: Page, testId: string): Promise<number> {
  const box = await page.getByTestId(testId).boundingBox();
  expect(box).toBeTruthy();
  return Math.round(box!.height);
}

async function visibleScrollbackMinIndex(locator: Locator): Promise<number> {
  const indices = await visibleScrollbackIndices(locator);
  return indices.length ? Math.min(...indices) : Number.POSITIVE_INFINITY;
}

async function visibleScrollbackMaxIndex(locator: Locator): Promise<number> {
  const indices = await visibleScrollbackIndices(locator);
  return indices.length ? Math.max(...indices) : Number.NEGATIVE_INFINITY;
}

async function visibleScrollbackIndices(locator: Locator): Promise<number[]> {
  const text = await locator.innerText();
  return [...text.matchAll(/scrollback-(\d{2})/g)].map((match) => Number(match[1]));
}

async function expectPlotlyChartToFillContainer(locator: Locator): Promise<void> {
  await expect
    .poll(async () => {
      const chartBox = await locator.boundingBox();
      const svgBox = await locator.locator("svg").first().boundingBox();
      if (!chartBox || !svgBox || chartBox.height <= 0) {
        return 0;
      }
      return svgBox.height / chartBox.height;
    })
    .toBeGreaterThan(0.75);
}

async function expectVegaChartVisible(locator: Locator): Promise<void> {
  await expect(locator).toBeVisible();
  await expect(locator.locator("svg").first()).toBeVisible();
  await expect
    .poll(async () => {
      const chartBox = await locator.boundingBox();
      const svgBox = await locator.locator("svg").first().boundingBox();
      if (!chartBox || !svgBox) {
        return 0;
      }
      return Math.min(svgBox.width, svgBox.height, chartBox.width, chartBox.height);
    })
    .toBeGreaterThan(20);
}

function expectMinimalRunBody(body: unknown, expected: ExpectedRunBody): void {
  const record = expectRecord(body);
  expect(record.threadId).toBe(expected.threadId);
  expect(typeof record.runId).toBe("string");
  expect(record.state).toEqual({});
  expect(record.forwardedProps).toEqual({});
  expect(record.tools).toEqual([]);
  expect(record.context).toEqual([]);
  const messages = Array.isArray(record.messages) ? record.messages : [];
  expect(messages).toHaveLength(1);
  const message = expectRecord(messages[0]);
  expect(message.role).toBe("user");
  expect(message.content).toBe(expected.message);
  expect(JSON.stringify(record.state)).not.toContain("pane");
  expect(JSON.stringify(record.forwardedProps)).not.toContain("pane");
  const contextJson = JSON.stringify(record.context);
  expect(contextJson).not.toContain("houmao.canvas_size_px.v1");
  expect(contextJson).not.toContain("houmao.canvas.v1");
  expect(contextJson).not.toContain("width");
  expect(contextJson).not.toContain("height");
  expect(contextJson).not.toContain("pane");
  expect(contextJson).not.toContain("display");
  expect(contextJson).not.toContain("transcript");
  expect(contextJson).not.toContain("renderer");
  expect(contextJson).not.toContain("scroll");
  expect(contextJson).not.toContain("agentId");
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

function retiredBarToolCallEvents(toolCallId: string, title: string): Array<Record<string, unknown>> {
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

function templateToolCallEvents(
  toolCallId: string,
  title: string,
  options: {
    rendererPreferred?: string;
    omitY?: boolean;
    datasource?: boolean;
    chartType?: "bar" | "line" | "scatter" | "pie" | "histogram";
    chartTypeOverride?: string;
    traceTypeOverride?: string;
  } = {},
): Array<Record<string, unknown>> {
  const chartType = options.chartType ?? "bar";
  const payload = templatePayload(title, { ...options, chartType });
  return [
    {
      type: "TOOL_CALL_START",
      toolCallId,
      toolCallName: "houmao.graphic.template",
      parentMessageId: `${toolCallId}-message`,
    },
    {
      type: "TOOL_CALL_ARGS",
      toolCallId,
      delta: JSON.stringify(payload),
    },
    {
      type: "TOOL_CALL_END",
      toolCallId,
    },
  ];
}

function vegaliteToolCallEvents(
  toolCallId: string,
  title: string,
  options: { remoteData?: boolean; malformed?: boolean } = {},
): Array<Record<string, unknown>> {
  return [
    {
      type: "TOOL_CALL_START",
      toolCallId,
      toolCallName: "houmao.graphic.vegalite",
      parentMessageId: `${toolCallId}-message`,
    },
    {
      type: "TOOL_CALL_ARGS",
      toolCallId,
      delta: JSON.stringify(vegalitePayload(title, options)),
    },
    {
      type: "TOOL_CALL_END",
      toolCallId,
    },
  ];
}

function vegalitePayload(
  title: string,
  options: { remoteData?: boolean; malformed?: boolean } = {},
): Record<string, unknown> {
  const data = options.remoteData
    ? { url: "https://example.invalid/private.json" }
    : {
        values: [
          { status: "Ready", count: 12 },
          { status: "Review", count: 21 },
          { status: "Blocked", count: 3 },
        ],
      };
  return {
    schemaVersion: 1,
    library: "vega-lite",
    specVersion: "6",
    title,
    description: "Playwright Vega-Lite proof",
    spec: {
      $schema: "https://vega.github.io/schema/vega-lite/v6.4.1.json",
      data,
      mark: options.malformed ? undefined : "bar",
      encoding: {
        x: { field: "status", type: "nominal" },
        y: { field: "count", type: "quantitative" },
        color: { field: "status", type: "nominal", legend: null },
      },
    },
    display: { height: 320, caption: "Inline Vega-Lite rows." },
  };
}

function templatePayload(
  title: string,
  options: {
    rendererPreferred?: string;
    omitY?: boolean;
    datasource?: boolean;
    chartType: "bar" | "line" | "scatter" | "pie" | "histogram";
    chartTypeOverride?: string;
    traceTypeOverride?: string;
  },
): Record<string, unknown> {
  if (options.datasource) {
    return {
      schemaVersion: 2,
      chartType: options.chartType,
      renderer: { preferred: "plotly" },
      title,
      subtitle: "Playwright template graphic proof",
      dataRefs: [{ id: "debugRows", columns: [{ name: "status" }, { name: "count" }] }],
      traces: [
        {
          type: options.chartType === "line" ? "scatter" : options.chartType,
          source: {
            dataRef: "debugRows",
            x: { column: "status" },
            y: { column: "count" },
          },
        },
      ],
    };
  }
  const trace = templateTrace(options.chartType, options.omitY);
  if (typeof options.traceTypeOverride === "string") {
    trace.type = options.traceTypeOverride;
  }
  return {
    schemaVersion: 2,
    chartType: options.chartTypeOverride ?? options.chartType,
    renderer: { preferred: options.rendererPreferred ?? "plotly" },
    title,
    subtitle: "Playwright template graphic proof",
    traces: [trace],
    layout: { xaxis: { title: "Status" }, yaxis: { title: "Count" }, bargap: 0.25 },
    extra: { plotly: { layout: { margin: { l: 48, r: 16, t: 20, b: 44 } } } },
  };
}

function templateTrace(
  chartType: "bar" | "line" | "scatter" | "pie" | "histogram",
  omitY = false,
): Record<string, unknown> {
  if (chartType === "pie") {
    return { type: "pie", labels: ["Ready", "Review", "Blocked"], values: [12, 21, 3] };
  }
  if (chartType === "histogram") {
    return { type: "histogram", x: [91, 102, 107, 120, 121, 135] };
  }
  const trace: Record<string, unknown> = {
    type: chartType === "line" ? "scatter" : chartType,
    x: ["Ready", "Review", "Blocked"],
    mode: chartType === "scatter" ? "markers" : chartType === "line" ? "lines+markers" : undefined,
    marker: { color: ["#2563eb", "#16a34a", "#dc2626"] },
  };
  if (!omitY) {
    trace.y = [12, 21, 3];
  }
  return trace;
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

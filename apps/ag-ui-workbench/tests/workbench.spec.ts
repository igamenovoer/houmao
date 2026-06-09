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
  await expect(page.getByTestId("transcript-agent-1")).toContainText("Alpha Dashboard");
  await expect(page.getByTestId("component-dashboard-agent-1")).toBeVisible();
  await expect(page.getByTestId("component-metric-grid-agent-1")).toContainText("Pass rate");
  await expect(page.getByTestId("component-chart-agent-1").first()).toBeVisible();
  await expect(page.getByTestId("component-table-agent-1")).toContainText("Alpha count");

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

test("respects closing operator pane while preserving other panes and operator metadata", async ({ page }) => {
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await configurePane(
    page,
    "operator",
    "Custom Operator",
    fakeServer.targetBase("operator"),
    "operator-thread-custom",
  );
  await page.getByTestId("add-agent-pane").click();
  await configurePane(page, "agent-1", "Alpha", fakeServer.targetBase("alpha"), "alpha-thread");

  const closed = await page.evaluate(() => window.__HMWB_TEST__!.closePane("operator"));
  expect(closed).toBeTruthy();
  await expect.poll(() => panelIds(page)).toEqual(["agent-1"]);
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect(page.getByTestId("panel-agent-1")).toBeVisible();

  await expect
    .poll(() => page.evaluate(() => JSON.stringify(window.__HMWB_TEST__!.storage().layout ?? {})))
    .not.toContain("operator");
  const savedBeforeReload = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(savedBeforeReload.panes.operator.target).toMatchObject({
    label: "Custom Operator",
    url: fakeServer.targetBase("operator"),
    threadId: "operator-thread-custom",
  });

  await page.reload();
  await expect.poll(() => panelIds(page)).toEqual(["agent-1"]);
  await expect(page.getByTestId("panel-operator")).toHaveCount(0);
  await expect(page.getByTestId("panel-agent-1")).toBeVisible();
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("alpha"));
  await expect(page.getByTestId("thread-id-agent-1")).toHaveValue("alpha-thread");
  const savedAfterReload = await page.evaluate(() => window.__HMWB_TEST__!.storage());
  expect(savedAfterReload.panes.operator.target).toMatchObject({
    label: "Custom Operator",
    url: fakeServer.targetBase("operator"),
    threadId: "operator-thread-custom",
  });
});

test("surfaces target policy errors before contacting a disallowed target", async ({ page }) => {
  await configurePane(page, "operator", "Operator", "http://example.com/v1/ag-ui", "operator-thread");
  await page.getByTestId("capabilities-operator").click();
  await expect(page.getByTestId("errors-operator")).toContainText("target_policy_rejected");
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
  await expect(page.getByTestId("picker-error")).toContainText("no gateway");
  await expect(page.getByTestId("target-url-agent-1")).toHaveValue(fakeServer.targetBase("manual"));
});

test("surfaces target policy errors for disallowed passive-server discovery", async ({ page }) => {
  await page.getByTestId("open-agent-picker").click();
  await page.getByTestId("passive-server-url").fill("http://example.com");
  await page.getByTestId("refresh-agents").click();
  await expect(page.getByTestId("picker-error")).toContainText("target_policy_rejected");
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

async function panelIds(page: Page): Promise<string[]> {
  return page.evaluate(() => window.__HMWB_TEST__!.panelIds().sort());
}

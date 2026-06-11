import { execFile } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

import { expect, test, type Page, type TestInfo } from "@playwright/test";

const execFileAsync = promisify(execFile);
const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(appRoot, "../..");
const TEMPLATE_TOOL_NAME = "houmao.graphic.template";
const DONE_PREFIX = "AG_UI_TEMPLATE_GRAPHIC_SMOKE_DONE";
const TITLE_PREFIX = "Real Agent Template Graphic Smoke";

interface SmokeConfig {
  enabled: boolean;
  passiveServerUrl: string;
  agentName: string;
  agentId: string;
  agentRef: string;
  timeoutMs: number;
  commandTimeoutMs: number;
  stopAfterSmoke: boolean;
  evidenceDir: string | null;
}

interface PassiveResolveResponse {
  status?: string;
  detail?: string;
  agentRef?: string;
  agentId?: string | null;
  agentName?: string | null;
  gateway?: {
    host?: string;
    port?: number;
    protocolVersion?: string;
  } | null;
}

interface Diagnostics {
  nonce: string;
  passiveServerUrl: string;
  agentRef: string;
  agentName?: string;
  agentId?: string;
  resolvedTarget?: string;
  threadId?: string;
  prompt?: string;
  capabilities?: unknown;
  capabilityNotes?: string[];
  textMarkerSeen?: boolean;
  console: string[];
  errors: string[];
  relaunch?: CommandResult;
  templateSchema?: CommandResult;
  stop?: CommandResult;
}

interface CommandResult {
  command: string[];
  stdout: string;
  stderr: string;
}

const config = readConfig();

test.describe("real-agent AG-UI GUI smoke", () => {
  test.skip(!config.enabled, "Set HMWB_REAL_AGENT_SMOKE=1 to run the live real-agent GUI smoke.");

  test("prompts a real Houmao agent and renders a template graphic", async ({ page }, testInfo) => {
    const missing = missingPrerequisites(config);
    if (missing.length > 0) {
      throw new Error(`Missing real-agent GUI smoke prerequisites: ${missing.join(", ")}`);
    }

    test.setTimeout(config.timeoutMs + config.commandTimeoutMs + 60_000);

    const nonce = `${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 8)}`;
    const diagnostics: Diagnostics = {
      nonce,
      passiveServerUrl: config.passiveServerUrl,
      agentRef: config.agentRef,
      agentName: config.agentName || undefined,
      agentId: config.agentId || undefined,
      console: [],
      errors: [],
    };
    let connected = false;

    page.on("console", (message) => {
      diagnostics.console.push(`[${message.type()}] ${message.text()}`);
    });
    page.on("pageerror", (error) => {
      diagnostics.errors.push(error.stack || error.message);
    });

    try {
      diagnostics.relaunch = await runHoumaoMgr(
        ["agents", "single", ...agentSelectorArgs(config), "relaunch"],
        config.commandTimeoutMs,
      );

      const resolved = await waitForLiveGateway(config, diagnostics);
      diagnostics.resolvedTarget = gatewayTargetUrl(resolved, config.passiveServerUrl);

      const capabilities = await fetchCapabilities(diagnostics.resolvedTarget);
      diagnostics.capabilities = capabilities;
      diagnostics.capabilityNotes = assertLivePresentationCapabilities(capabilities);
      diagnostics.templateSchema = await runHoumaoMgr(
        ["internals", "ag-ui", "components", "schema", TEMPLATE_TOOL_NAME],
        config.commandTimeoutMs,
      );
      assertTemplateSchemaCommand(diagnostics.templateSchema);

      await page.goto("/");
      await page.evaluate(() => {
        window.localStorage.clear();
      });
      await page.reload();

      await page.getByTestId("open-agent-picker").click();
      await page.getByTestId("passive-server-url").fill(config.passiveServerUrl);
      await page.getByTestId("refresh-agents").click();

      const agentRow = page
        .getByTestId("agent-list")
        .locator(".agent-row")
        .filter({ hasText: resolved.agentId || config.agentRef })
        .first();
      await expect(agentRow).toBeVisible();
      await agentRow.dblclick();

      await expect(page.getByTestId("panel-agent-1")).toBeVisible();
      await expect(page.getByTestId("target-url-agent-1")).toHaveValue(diagnostics.resolvedTarget);

      await page.getByTestId("connect-agent-1").click();
      await expect(page.getByTestId("status-agent-1")).toContainText("connected");
      await expect(page.getByTestId("watch-strip-agent-1")).toContainText("connected");
      connected = true;

      const threadId = (await page.getByTestId("thread-id-agent-1").inputValue()).trim();
      diagnostics.threadId = threadId;

      const prompt = validationPrompt(nonce, threadId);
      diagnostics.prompt = prompt;
      await page.getByTestId("prompt-agent-1").fill(prompt);
      await page.getByTestId("run-agent-1").click();

      await expect(page.getByTestId("component-agent-1").filter({ hasText: `${TITLE_PREFIX} ${nonce}` })).toBeVisible({
        timeout: config.timeoutMs,
      });

      const templateChart = page.getByTestId("template-chart-vega-lite-agent-1").filter({
        has: page.locator("svg"),
        hasText: `${TITLE_PREFIX} ${nonce}`,
      });
      await expect(templateChart).toBeVisible({ timeout: config.timeoutMs });
      await expect(templateChart.locator("svg")).toBeVisible();
      diagnostics.textMarkerSeen = await containsTextWithin(
        page,
        "transcript-agent-1",
        `${DONE_PREFIX} ${nonce}`,
        5_000,
      );
    } catch (error) {
      await writeFailureEvidence(page, testInfo, config, diagnostics, error);
      throw error;
    } finally {
      if (connected && !page.isClosed()) {
        await page.getByTestId("disconnect-agent-1").click({ timeout: 2_000 }).catch((error: unknown) => {
          diagnostics.errors.push(`disconnect failed: ${errorMessage(error)}`);
        });
      }
      if (config.stopAfterSmoke) {
        try {
          diagnostics.stop = await runHoumaoMgr(
            ["agents", "single", ...agentSelectorArgs(config), "stop"],
            config.commandTimeoutMs,
          );
        } catch (error) {
          diagnostics.errors.push(`stop-after-smoke failed: ${errorMessage(error)}`);
        }
      }
    }
  });
});

function readConfig(): SmokeConfig {
  const agentName = process.env.HMWB_TEST_AGENT_NAME?.trim() ?? "";
  const agentId = process.env.HMWB_TEST_AGENT_ID?.trim() ?? "";
  return {
    enabled: process.env.HMWB_REAL_AGENT_SMOKE === "1",
    passiveServerUrl: process.env.HMWB_PASSIVE_SERVER_URL?.trim() ?? "",
    agentName,
    agentId,
    agentRef: agentId || agentName,
    timeoutMs: positiveIntegerEnv("HMWB_REAL_AGENT_TIMEOUT_MS", 180_000),
    commandTimeoutMs: positiveIntegerEnv("HMWB_AGENT_COMMAND_TIMEOUT_MS", 180_000),
    stopAfterSmoke: process.env.HMWB_REAL_AGENT_STOP_AFTER === "1",
    evidenceDir: process.env.HMWB_REAL_AGENT_EVIDENCE_DIR?.trim() || null,
  };
}

function missingPrerequisites(smokeConfig: SmokeConfig): string[] {
  const missing: string[] = [];
  if (!smokeConfig.passiveServerUrl) {
    missing.push("HMWB_PASSIVE_SERVER_URL");
  }
  if (!smokeConfig.agentName && !smokeConfig.agentId) {
    missing.push("HMWB_TEST_AGENT_NAME or HMWB_TEST_AGENT_ID");
  }
  return missing;
}

function positiveIntegerEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function agentSelectorArgs(smokeConfig: SmokeConfig): string[] {
  if (smokeConfig.agentId) {
    return ["--agent-id", smokeConfig.agentId];
  }
  return ["--agent-name", smokeConfig.agentName];
}

async function runHoumaoMgr(args: string[], timeoutMs: number): Promise<CommandResult> {
  const command = ["pixi", "run", "houmao-mgr", "--print-json", ...args];
  const { stdout, stderr } = await execFileAsync(command[0], command.slice(1), {
    cwd: repoRoot,
    timeout: timeoutMs,
    maxBuffer: 2 * 1024 * 1024,
  });
  return { command, stdout, stderr };
}

async function waitForLiveGateway(
  smokeConfig: SmokeConfig,
  diagnostics: Diagnostics,
): Promise<PassiveResolveResponse> {
  const deadline = Date.now() + smokeConfig.commandTimeoutMs;
  let lastError = "";
  while (Date.now() < deadline) {
    try {
      const resolved = await resolveAgent(smokeConfig.passiveServerUrl, smokeConfig.agentRef);
      if (resolved.status === "live_with_gateway" && resolved.gateway?.port) {
        diagnostics.agentId = resolved.agentId ?? diagnostics.agentId;
        diagnostics.agentName = resolved.agentName ?? diagnostics.agentName;
        return resolved;
      }
      lastError = `${resolved.status ?? "unknown"}: ${resolved.detail ?? "no detail"}`;
    } catch (error) {
      lastError = errorMessage(error);
    }
    await delay(2_000);
  }
  throw new Error(`Timed out waiting for live gateway for ${smokeConfig.agentRef}: ${lastError}`);
}

async function resolveAgent(passiveServerUrl: string, agentRef: string): Promise<PassiveResolveResponse> {
  const base = passiveServerUrl.replace(/\/+$/, "");
  const response = await fetch(`${base}/houmao/agents/${encodeURIComponent(agentRef)}/resolve`, {
    headers: { accept: "application/json" },
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(`Passive resolve HTTP ${response.status}: ${body.slice(0, 300)}`);
  }
  return JSON.parse(body) as PassiveResolveResponse;
}

function gatewayTargetUrl(resolved: PassiveResolveResponse, passiveServerUrl: string): string {
  const gateway = resolved.gateway;
  if (!gateway?.host || !gateway.port) {
    throw new Error(`Agent ${resolved.agentRef ?? "target"} has no gateway coordinates.`);
  }
  const host = browserReachableHost(gateway.host, passiveServerUrl);
  return `http://${host}:${gateway.port}/v1/ag-ui`;
}

function browserReachableHost(gatewayHost: string, passiveServerUrl: string): string {
  const normalized = gatewayHost.toLowerCase().replace(/^\[/, "").replace(/\]$/, "");
  if (normalized && normalized !== "0.0.0.0" && normalized !== "::") {
    return gatewayHost;
  }
  const passiveHost = new URL(passiveServerUrl).hostname;
  return passiveHost === "0.0.0.0" || passiveHost === "::" ? "127.0.0.1" : passiveHost;
}

async function fetchCapabilities(targetUrl: string): Promise<unknown> {
  const response = await fetch(`${targetUrl.replace(/\/+$/, "")}/capabilities`, {
    headers: { accept: "application/json" },
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(`AG-UI capabilities HTTP ${response.status}: ${body.slice(0, 300)}`);
  }
  return JSON.parse(body) as unknown;
}

function assertLivePresentationCapabilities(capabilities: unknown): string[] {
  const record = asRecord(capabilities);
  const houmao = asRecord(record.houmao);
  const features = asRecord(houmao.features);
  if (features.taskRunSubmission !== true) {
    throw new Error("AG-UI capabilities do not advertise task-run submission.");
  }
  if (features.guiConnect !== true) {
    throw new Error("AG-UI capabilities do not advertise GUI connect streams.");
  }

  const capabilityRoot = asRecord(record.capabilities);
  const transport = asRecord(capabilityRoot.transport);
  if (transport.streaming !== true) {
    throw new Error("AG-UI capabilities do not advertise streaming transport.");
  }

  const custom = asRecord(capabilityRoot.custom);
  const customHoumao = asRecord(custom.houmao);
  const publishedEvents = asRecord(customHoumao.publishedEvents);
  if (publishedEvents.delivery !== "live_only_fanout") {
    throw new Error("AG-UI capabilities do not advertise live published-event fanout.");
  }

  const notes: string[] = [];
  const tools = asRecord(capabilityRoot.tools);
  const toolItems = Array.isArray(tools.items) ? tools.items : [];
  const hasTemplateTool = toolItems.some((item) => asRecord(item).name === TEMPLATE_TOOL_NAME);
  if (!hasTemplateTool) {
    notes.push(`${TEMPLATE_TOOL_NAME} is not advertised as a headless generated-graphics tool.`);
  }
  const presentation = asRecord(customHoumao.presentation);
  const templateGraphics = asRecord(presentation.templateGraphics);
  if (templateGraphics.toolName !== TEMPLATE_TOOL_NAME) {
    notes.push("Template graphics presentation metadata is not advertised by this gateway.");
  }
  const renderers = Array.isArray(templateGraphics.renderers) ? templateGraphics.renderers : [];
  if (!renderers.includes("vega-lite")) {
    notes.push("Vega-Lite renderer metadata is not advertised by this gateway.");
  }
  if (features.generatedGraphics !== true) {
    notes.push("generatedGraphics is false; this smoke relies on agent-published GUI events.");
  }
  return notes;
}

function assertTemplateSchemaCommand(result: CommandResult): void {
  const payload = JSON.parse(result.stdout) as unknown;
  if (asRecord(payload).name !== TEMPLATE_TOOL_NAME) {
    throw new Error(`houmao-mgr did not return the ${TEMPLATE_TOOL_NAME} schema.`);
  }
}

function validationPrompt(nonce: string, threadId: string): string {
  return [
    "You are validating Houmao AG-UI template graphics.",
    "",
    "Do not answer with prose only. Publish one AG-UI GUI chart message to the current workbench GUI thread.",
    `If active-thread routing is unavailable, publish to this thread id exactly: ${threadId}.`,
    "",
    `Use the Houmao typed component ${TEMPLATE_TOOL_NAME}.`,
    "Generate events with `houmao-mgr internals ag-ui events render houmao.graphic.template --input payload.json`.",
    "Publish those events with `houmao-mgr agents self gateway ag-ui publish`.",
    "",
    "The payload must use:",
    "- schemaVersion: 1",
    "- chartType: bar",
    "- renderer.preferred: vega-lite",
    "- renderer.fallback: [recharts]",
    `- title: ${TITLE_PREFIX} ${nonce}`,
    "- data.values: [{status: Ready, count: 3}, {status: Review, count: 2}, {status: Blocked, count: 1}]",
    "- encoding.x field status, nominal",
    "- encoding.y field count, quantitative",
    "",
    `After publishing the chart, reply with exactly: ${DONE_PREFIX} ${nonce}`,
  ].join("\n");
}

async function writeFailureEvidence(
  page: Page,
  testInfo: TestInfo,
  smokeConfig: SmokeConfig,
  diagnostics: Diagnostics,
  error: unknown,
): Promise<void> {
  diagnostics.errors.push(errorMessage(error));
  const evidenceDir = smokeConfig.evidenceDir
    ? path.resolve(repoRoot, smokeConfig.evidenceDir)
    : testInfo.outputPath("evidence");
  await mkdir(evidenceDir, { recursive: true });

  const transcript = await textOrEmpty(page, "transcript-agent-1");
  const errors = await textOrEmpty(page, "errors-agent-1");
  const raw = await rawDiagnosticsOrEmpty(page);
  await page.screenshot({ path: path.join(evidenceDir, "screenshot.png"), fullPage: true }).catch(() => undefined);
  await writeFile(path.join(evidenceDir, "transcript.txt"), transcript, "utf8");
  await writeFile(path.join(evidenceDir, "errors.txt"), errors, "utf8");
  await writeFile(path.join(evidenceDir, "raw-events.txt"), raw, "utf8");
  await writeFile(path.join(evidenceDir, "summary.json"), `${JSON.stringify(diagnostics, null, 2)}\n`, "utf8");
}

async function textOrEmpty(page: Page, testId: string): Promise<string> {
  return page
    .getByTestId(testId)
    .innerText({ timeout: 1_000 })
    .catch(() => "");
}

async function rawDiagnosticsOrEmpty(page: Page): Promise<string> {
  const buttons = page.locator('[data-testid^="message-info-agent-1-"]');
  const buttonCount = await buttons.count().catch(() => 0);
  if (buttonCount > 0) {
    await buttons.nth(buttonCount - 1).click().catch(() => undefined);
  }
  return textOrEmpty(page, "raw-agent-1");
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function containsTextWithin(
  page: Page,
  testId: string,
  text: string,
  timeoutMs: number,
): Promise<boolean> {
  try {
    await expect(page.getByTestId(testId)).toContainText(text, { timeout: timeoutMs });
    return true;
  } catch {
    return false;
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.stack || error.message : String(error);
}

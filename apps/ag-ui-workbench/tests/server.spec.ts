import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";

import { expect, test } from "@playwright/test";
import { WebSocket } from "ws";

import { createWorkbenchFastifyApp } from "../src/server/app";
import { PresentationSessionRegistry } from "../src/server/presentationSessions";
import { detachTmuxAttachClient, tmuxAttachEnvironment } from "../src/server/tmuxBridge";
import type { RunAgentInput } from "../src/ag-ui/types";

test("Fastify app exposes health/status and cleans presentation sessions on shutdown", async () => {
  const registry = new PresentationSessionRegistry();
  registry.create({ paneId: "agent-1", kind: "plotly", metadata: { rows: 100, unsafe: { x: 1 } } });
  const server = await startWorkbenchTestServer({ presentationSessions: registry });

  const statusResponse = await fetch(`${server.baseUrl}/__houmao_workbench/status`);
  expect(statusResponse.ok).toBeTruthy();
  const status = (await statusResponse.json()) as {
    server: string;
    protocol: { agUiPeer: string };
    presentationSessions: { sessionCount: number; datasourceContentsStoredInBrowser: boolean };
  };
  expect(status.server).toBe("fastify");
  expect(status.protocol.agUiPeer).toBe("workbench-local-server");
  expect(status.presentationSessions.sessionCount).toBe(1);
  expect(status.presentationSessions.datasourceContentsStoredInBrowser).toBe(false);

  await server.close();
  expect(registry.diagnostics().sessionCount).toBe(0);
});

test("private protocol validation and target policy errors are deterministic", async () => {
  const server = await startWorkbenchTestServer();
  try {
    const malformedResponse = await fetch(`${server.baseUrl}/__houmao_workbench/ag-ui/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(malformedResponse.status).toBe(400);
    await expect(malformedResponse.json()).resolves.toMatchObject({
      code: "target_missing",
      path: "targetUrl",
    });

    const rejectedResponse = await fetch(`${server.baseUrl}/__houmao_workbench/fetch-json`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ targetUrl: "http://example.com/houmao/agents" }),
    });
    expect(rejectedResponse.status).toBe(403);
    await expect(rejectedResponse.json()).resolves.toMatchObject({
      code: "target_policy_rejected",
    });
  } finally {
    await server.close();
  }
});

test("Fastify AG-UI bridge forwards allowed capabilities and RUN_ERROR streams", async () => {
  const upstreamRequests: Array<{ path: string; body: unknown }> = [];
  const upstream = await startHttpServer(async (req, res) => {
    const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
    if (req.method === "GET" && requestUrl.pathname === "/v1/ag-ui/capabilities") {
      sendJson(res, 200, { capabilities: { transport: { streaming: true } } });
      return;
    }
    if (req.method === "POST" && requestUrl.pathname === "/v1/ag-ui/runs") {
      const body = await readJson(req);
      upstreamRequests.push({ path: requestUrl.pathname, body });
      res.writeHead(200, { "content-type": "text/event-stream" });
      res.write('data: {"type":"RUN_STARTED","threadId":"t-1","runId":"r-1"}\n\n');
      res.write('data: {"type":"RUN_ERROR","threadId":"t-1","runId":"r-1","message":"fixture run error"}\n\n');
      res.end();
      return;
    }
    sendJson(res, 404, { code: "not_found" });
  });
  const server = await startWorkbenchTestServer();

  try {
    const targetUrl = `${upstream.baseUrl}/v1/ag-ui`;
    const capabilitiesResponse = await fetch(`${server.baseUrl}/__houmao_workbench/ag-ui/capabilities`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ targetUrl }),
    });
    expect(capabilitiesResponse.ok).toBeTruthy();
    await expect(capabilitiesResponse.json()).resolves.toMatchObject({
      capabilities: { transport: { streaming: true } },
    });

    const input: RunAgentInput = {
      threadId: "t-1",
      runId: "r-1",
      state: {},
      messages: [],
      tools: [],
      context: [],
      forwardedProps: {},
    };
    const runResponse = await fetch(`${server.baseUrl}/__houmao_workbench/ag-ui/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ targetUrl, input }),
    });
    expect(runResponse.headers.get("content-type")).toContain("text/event-stream");
    const streamText = await runResponse.text();
    expect(streamText).toContain("RUN_ERROR");
    expect(streamText).toContain("fixture run error");
    expect(upstreamRequests[0].body).toMatchObject({ threadId: "t-1", messages: [] });
  } finally {
    await server.close();
    await upstream.close();
  }
});

test("private AG-UI stream abort closes the upstream stream", async () => {
  let upstreamClosed = false;
  const upstream = await startHttpServer(async (req, res) => {
    const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
    if (req.method === "POST" && requestUrl.pathname === "/v1/ag-ui/runs") {
      res.on("close", () => {
        upstreamClosed = true;
      });
      res.writeHead(200, { "content-type": "text/event-stream" });
      res.write('data: {"type":"RUN_STARTED","threadId":"t-1","runId":"r-1"}\n\n');
      return;
    }
    sendJson(res, 404, { code: "not_found" });
  });
  const server = await startWorkbenchTestServer();

  try {
    const controller = new AbortController();
    const runResponse = await fetch(`${server.baseUrl}/__houmao_workbench/ag-ui/run`, {
      method: "POST",
      signal: controller.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        targetUrl: `${upstream.baseUrl}/v1/ag-ui`,
        input: {
          threadId: "t-1",
          runId: "r-1",
          state: {},
          messages: [],
          tools: [],
          context: [],
          forwardedProps: {},
        },
      }),
    });
    await runResponse.body?.getReader().read();
    controller.abort();
    await expect.poll(() => upstreamClosed).toBeTruthy();
  } finally {
    await server.close();
    await upstream.close();
  }
});

test("Debug Agent module publishes validation errors and lifecycle diagnostics through Fastify", async () => {
  const server = await startWorkbenchTestServer();
  try {
    const capabilitiesResponse = await fetch(
      `${server.baseUrl}/__houmao_debug_agents/debug-agent-1/v1/ag-ui/capabilities`,
    );
    await expect(capabilitiesResponse.json()).resolves.toMatchObject({
      capabilities: { identity: { type: "debug-agent" } },
      houmao: { lifecycleBoundary: "debug-relay-only" },
    });

    const invalidResponse = await fetch(
      `${server.baseUrl}/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ threadId: "debug-agent-1-thread", events: [] }),
      },
    );
    expect(invalidResponse.status).toBe(400);
    await expect(invalidResponse.json()).resolves.toMatchObject({
      code: "ag_ui_event_validation_failed",
    });

    const validVegaLite = {
      schemaVersion: 1,
      library: "vega-lite",
      specVersion: "6",
      title: "Server Vega-Lite",
      spec: {
        $schema: "https://vega.github.io/schema/vega-lite/v6.4.1.json",
        data: { values: [{ status: "ready", count: 1 }] },
        mark: "bar",
        encoding: {
          x: { field: "status", type: "nominal" },
          y: { field: "count", type: "quantitative" },
        },
      },
    };
    const validComponentResponse = await fetch(
      `${server.baseUrl}/__houmao_debug_agents/debug-agent-1/components/houmao.graphic.vegalite`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          threadId: "debug-agent-1-thread",
          validateOnly: true,
          payload: validVegaLite,
        }),
      },
    );
    expect(validComponentResponse.status).toBe(200);
    await expect(validComponentResponse.json()).resolves.toMatchObject({
      status: "validated",
      componentName: "houmao.graphic.vegalite",
      acceptedCount: 3,
    });

    const invalidComponentResponse = await fetch(
      `${server.baseUrl}/__houmao_debug_agents/debug-agent-1/components/houmao.graphic.vegalite`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          threadId: "debug-agent-1-thread",
          validateOnly: true,
          payload: {
            ...validVegaLite,
            spec: {
              ...validVegaLite.spec,
              data: { url: "https://example.invalid/private.json" },
            },
          },
        }),
      },
    );
    expect(invalidComponentResponse.status).toBe(400);
    await expect(invalidComponentResponse.json()).resolves.toMatchObject({
      code: "component_validation_failed",
      path: "spec.data.url",
    });
  } finally {
    await server.close();
  }
});

test("tmux Fastify bridge fixture lists sessions and rejects read-only input", async () => {
  const previousFixture = process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE;
  process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE = "1";
  const server = await startWorkbenchTestServer();
  try {
    await fetch(`${server.baseUrl}/__houmao_tmux/fixture/reset`, { method: "POST" });
    const sessionsResponse = await fetch(`${server.baseUrl}/__houmao_tmux/sessions`);
    await expect(sessionsResponse.json()).resolves.toMatchObject({
      status: "ready",
      tmuxAvailable: true,
      sessions: expect.arrayContaining([expect.objectContaining({ sessionName: "houmao-alpha" })]),
    });

    const messages = await collectTmuxMessages(server.baseUrl, [
      { type: "attach", sessionName: "houmao-alpha", mode: "read-only", cols: 80, rows: 24 },
      { type: "input", data: "blocked-input" },
    ]);
    expect(messages).toContainEqual(expect.objectContaining({ type: "attached" }));
    expect(messages).toContainEqual(
      expect.objectContaining({ type: "error", code: "tmux_read_only" }),
    );
  } finally {
    await server.close();
    if (typeof previousFixture === "undefined") {
      delete process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE;
    } else {
      process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE = previousFixture;
    }
  }
});

test("tmux Fastify bridge fixture records valid attachment resizes", async () => {
  const previousFixture = process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE;
  process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE = "1";
  const server = await startWorkbenchTestServer();
  try {
    await fetch(`${server.baseUrl}/__houmao_tmux/fixture/reset`, { method: "POST" });
    const messages = await collectTmuxMessages(
      server.baseUrl,
      [
        { type: "attach", sessionName: "houmao-alpha", mode: "read-write", cols: 80, rows: 24 },
        { type: "resize", cols: 101, rows: 31 },
      ],
      3,
    );
    expect(messages).toContainEqual(expect.objectContaining({ type: "attached" }));
    expect(messages).toContainEqual(
      expect.objectContaining({ type: "output", data: expect.stringContaining("101x31") }),
    );

    const attachmentsResponse = await fetch(`${server.baseUrl}/__houmao_tmux/fixture/attachments`);
    await expect(attachmentsResponse.json()).resolves.toMatchObject({
      attachments: [
        expect.objectContaining({
          sessionName: "houmao-alpha",
          attachCols: 80,
          attachRows: 24,
          resizes: [expect.objectContaining({ cols: 101, rows: 31 })],
        }),
      ],
    });
  } finally {
    await server.close();
    restoreFixtureEnv(previousFixture);
  }
});

test("tmux Fastify bridge fixture handles resize and scroll validation", async () => {
  const previousFixture = process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE;
  process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE = "1";
  const server = await startWorkbenchTestServer();
  try {
    await fetch(`${server.baseUrl}/__houmao_tmux/fixture/reset`, { method: "POST" });
    const beforeAttachMessages = await collectTmuxMessages(
      server.baseUrl,
      [{ type: "resize", cols: 80, rows: 24 }],
      1,
    );
    expect(beforeAttachMessages).toContainEqual(
      expect.objectContaining({ type: "error", code: "tmux_not_attached" }),
    );
    const scrollBeforeAttachMessages = await collectTmuxMessages(
      server.baseUrl,
      [{ type: "scroll", direction: "up", lines: 5 }],
      1,
    );
    expect(scrollBeforeAttachMessages).toContainEqual(
      expect.objectContaining({ type: "error", code: "tmux_not_attached" }),
    );

    const invalidMessages = await collectTmuxMessages(
      server.baseUrl,
      [
        { type: "attach", sessionName: "houmao-alpha", mode: "read-write", cols: 80, rows: 24 },
        { type: "resize", cols: 1, rows: 24 },
      ],
      3,
    );
    expect(invalidMessages).toContainEqual(
      expect.objectContaining({ type: "error", code: "tmux_resize_invalid" }),
    );

    const scrollMessages = await collectTmuxMessages(
      server.baseUrl,
      [
        { type: "attach", sessionName: "houmao-alpha", mode: "read-write", cols: 80, rows: 24 },
        { type: "scroll", direction: "up", lines: 5 },
      ],
      3,
    );
    expect(scrollMessages).toContainEqual(
      expect.objectContaining({
        type: "output",
        data: expect.stringContaining("fixture scrolled houmao-alpha up 5"),
      }),
    );

    const closeMessages = await collectTmuxMessages(
      server.baseUrl,
      [
        { type: "attach", sessionName: "houmao-alpha", mode: "read-write", cols: 80, rows: 24 },
        { type: "close" },
      ],
      2,
    );
    expect(closeMessages).toContainEqual(expect.objectContaining({ type: "attached" }));
  } finally {
    await server.close();
    restoreFixtureEnv(previousFixture);
  }
});

test("tmux attach environment strips nested tmux variables", () => {
  const env = tmuxAttachEnvironment({
    PATH: "/usr/bin",
    HOME: "/tmp/home",
    TERM: "dumb",
    TMUX: "/tmp/tmux-1000/default,123,0",
    TMUX_PANE: "%12",
  });

  expect(env).toMatchObject({ PATH: "/usr/bin", HOME: "/tmp/home", TERM: "xterm-256color" });
  expect(env.TMUX).toBeUndefined();
  expect(env.TMUX_PANE).toBeUndefined();
});

test("tmux attach client cleanup detaches without killing the session and tolerates failures", async () => {
  const commands: Array<{ file: string; args: string[] }> = [];
  const runner = async (file: string, args: string[]) => {
    commands.push({ file, args });
    if (args[0] === "list-clients") {
      return {
        stdout: "12345\t/dev/pts/42\thoumao-alpha\n99999\t/dev/pts/99\tother-session\n",
      };
    }
    return {};
  };

  await detachTmuxAttachClient(" houmao-alpha ", 12345, runner);
  expect(commands).toEqual([
    {
      file: "tmux",
      args: [
        "list-clients",
        "-F",
        "#{client_pid}\t#{client_tty}\t#{session_name}",
        "-t",
        "houmao-alpha",
      ],
    },
    { file: "tmux", args: ["detach-client", "-t", "/dev/pts/42"] },
  ]);
  expect(commands.flatMap((command) => command.args)).not.toContain("kill-session");

  const warn = console.warn;
  const warnings: string[] = [];
  console.warn = (...args: unknown[]) => {
    warnings.push(String(args[0] ?? ""));
  };
  try {
    await expect(
      detachTmuxAttachClient("houmao-beta", 12345, async () => {
        throw new Error("detach failed");
      }),
    ).resolves.toBeUndefined();
  } finally {
    console.warn = warn;
  }
  expect(warnings[0] ?? "").toContain("Failed to detach tmux attach client");
});

test("presentation-session disposal is presentation-only", async () => {
  const server = await startWorkbenchTestServer();
  try {
    const createResponse = await fetch(`${server.baseUrl}/__houmao_workbench/presentation-sessions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        paneId: "agent-1",
        kind: "plotly",
        metadata: { datasource: "orders", rows: 500_000 },
      }),
    });
    expect(createResponse.status).toBe(201);
    const createBody = (await createResponse.json()) as { session: { sessionId: string } };

    const disposeResponse = await fetch(
      `${server.baseUrl}/__houmao_workbench/presentation-sessions/${createBody.session.sessionId}`,
      { method: "DELETE" },
    );
    await expect(disposeResponse.json()).resolves.toMatchObject({
      disposed: true,
      lifecycle: "presentation-only",
      houmaoAgentLifecycleControlled: false,
    });
  } finally {
    await server.close();
  }
});

async function startWorkbenchTestServer(options: Parameters<typeof createWorkbenchFastifyApp>[0] = {}): Promise<{
  baseUrl: string;
  close: () => Promise<void>;
}> {
  const app = await createWorkbenchFastifyApp({ ...options, mode: "test" });
  await app.listen({ host: "127.0.0.1", port: 0 });
  const address = app.server.address();
  if (!address || typeof address === "string") {
    throw new Error("Workbench test server did not bind a TCP port.");
  }
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: async () => {
      await app.close();
    },
  };
}

async function startHttpServer(
  handler: (req: IncomingMessage, res: ServerResponse) => void | Promise<void>,
): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  const server = createServer((req, res) => {
    void handler(req, res);
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Test HTTP server did not bind a TCP port.");
  }
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => closeServer(server),
  };
}

async function closeServer(server: Server): Promise<void> {
  await new Promise<void>((resolve) => server.close(() => resolve()));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function collectTmuxMessages(
  baseUrl: string,
  outgoing: unknown[],
  minimumMessages = 3,
): Promise<unknown[]> {
  const url = new URL(baseUrl);
  const wsUrl = `ws://${url.host}/__houmao_tmux/attach`;
  const messages: unknown[] = [];
  const socket = new WebSocket(wsUrl);
  await new Promise<void>((resolve, reject) => {
    socket.once("open", resolve);
    socket.once("error", reject);
  });
  socket.on("message", (data) => {
    messages.push(JSON.parse(data.toString()) as unknown);
  });
  for (const message of outgoing) {
    socket.send(JSON.stringify(message));
  }
  await expect.poll(() => messages.length).toBeGreaterThanOrEqual(minimumMessages);
  socket.close();
  return messages;
}

function restoreFixtureEnv(previousFixture: string | undefined): void {
  if (typeof previousFixture === "undefined") {
    delete process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE;
    return;
  }
  process.env.HOUMAO_AG_UI_WORKBENCH_TMUX_FIXTURE = previousFixture;
}

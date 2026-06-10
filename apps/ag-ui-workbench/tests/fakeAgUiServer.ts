import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";

interface RecordedRun {
  target: string;
  body: unknown;
}

interface RecordedDetach {
  target: string;
  connectionId: string;
}

interface RecordedConnect {
  target: string;
  body: Record<string, unknown>;
}

interface GatewayServerRecord {
  server: Server;
  port: number;
}

const GATEWAY_TARGETS = ["operator", "alpha", "beta", "manual"] as const;

export class FakeAgUiServer {
  private m_passiveServer: Server | null = null;
  private m_passivePort = 0;
  private readonly m_gateways = new Map<string, GatewayServerRecord>();
  private readonly m_openResponses = new Map<ServerResponse, string>();

  readonly runs: RecordedRun[] = [];
  readonly detaches: RecordedDetach[] = [];
  readonly connects: RecordedConnect[] = [];
  interruptRequests = 0;

  async start(): Promise<void> {
    for (const target of GATEWAY_TARGETS) {
      await this.startGateway(target);
    }
    this.m_passiveServer = createServer((req, res) => {
      void this.handlePassiveRequest(req, res);
    });
    await new Promise<void>((resolve) => {
      this.m_passiveServer!.listen(0, "127.0.0.1", resolve);
    });
    const address = this.m_passiveServer.address();
    if (!address || typeof address === "string") {
      throw new Error("Fake passive server did not bind a TCP port.");
    }
    this.m_passivePort = address.port;
  }

  async stop(): Promise<void> {
    for (const response of this.m_openResponses.keys()) {
      response.end();
    }
    await Promise.all(
      [...this.m_gateways.values()].map(
        (record) => new Promise<void>((resolve) => record.server.close(() => resolve())),
      ),
    );
    this.m_gateways.clear();
    await new Promise<void>((resolve) => this.m_passiveServer?.close(() => resolve()));
    this.m_passiveServer = null;
  }

  async restartGateway(target: string): Promise<void> {
    await this.stopGateway(target);
    await this.startGateway(target);
  }

  passiveBase(): string {
    return `http://127.0.0.1:${this.m_passivePort}`;
  }

  targetBase(target: string): string {
    const gateway = this.m_gateways.get(target);
    if (!gateway) {
      throw new Error(`Unknown fake AG-UI target ${target}.`);
    }
    return `http://127.0.0.1:${gateway.port}/v1/ag-ui`;
  }

  private async startGateway(target: string): Promise<void> {
    const server = createServer((req, res) => {
      void this.handleGatewayRequest(req, res, target);
    });
    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", resolve);
    });
    const address = server.address();
    if (!address || typeof address === "string") {
      throw new Error(`Fake gateway ${target} did not bind a TCP port.`);
    }
    this.m_gateways.set(target, { server, port: address.port });
  }

  private async stopGateway(target: string): Promise<void> {
    for (const [response, responseTarget] of [...this.m_openResponses.entries()]) {
      if (responseTarget === target) {
        response.end();
        this.m_openResponses.delete(response);
      }
    }
    const gateway = this.m_gateways.get(target);
    if (!gateway) {
      return;
    }
    this.m_gateways.delete(target);
    await new Promise<void>((resolve) => gateway.server.close(() => resolve()));
  }

  private async handlePassiveRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "127.0.0.1"}`);
    if (req.method === "GET" && url.pathname === "/houmao/agents") {
      sendJson(res, 200, {
        agents: [
          discoveredAgent("alpha", this.m_gateways.get("alpha") !== undefined),
          discoveredAgent("beta", this.m_gateways.get("beta") !== undefined),
          discoveredAgent("no-gateway", false),
        ],
      });
      return;
    }

    const resolveMatch = /^\/houmao\/agents\/([^/]+)\/resolve$/.exec(url.pathname);
    if (req.method === "GET" && resolveMatch) {
      const agentRef = decodeURIComponent(resolveMatch[1]);
      if (!["alpha", "beta", "no-gateway"].includes(agentRef)) {
        sendJson(res, 200, {
          status: "unknown",
          detail: `Agent not found: ${agentRef}`,
          agentRef,
        });
        return;
      }
      const gateway = this.m_gateways.get(agentRef);
      const agent = discoveredAgent(agentRef, gateway !== undefined) as Record<string, unknown>;
      sendJson(res, 200, {
        status: gateway ? "live_with_gateway" : "live_without_gateway",
        detail: gateway
          ? "Agent is live and current gateway coordinates are available."
          : "Agent is live but has no current gateway coordinates.",
        agentRef,
        agentId: agent.agent_id,
        agentName: agent.agent_name,
        generationId: agent.generation_id,
        lifecycleState: gateway ? "active" : "stopped",
        relaunchable: true,
        tool: agent.tool,
        backend: agent.backend,
        manifestPath: agent.manifest_path,
        sessionRoot: agent.session_root,
        gateway: gateway
          ? {
              host: "127.0.0.1",
              port: gateway.port,
              protocolVersion: "v1",
            }
          : null,
        candidates: [],
      });
      return;
    }

    const gatewayMatch = /^\/houmao\/agents\/([^/]+)\/gateway$/.exec(url.pathname);
    if (req.method === "GET" && gatewayMatch) {
      const agentRef = decodeURIComponent(gatewayMatch[1]);
      if (agentRef === "no-gateway") {
        sendJson(res, 502, {
          detail: "Managed agent does not have a live gateway attached.",
        });
        return;
      }
      const gateway = this.m_gateways.get(agentRef);
      if (!gateway) {
        sendJson(res, 404, { detail: "Agent not found." });
        return;
      }
      sendJson(res, 200, {
        status: "running",
        gateway_host: "127.0.0.1",
        gateway_port: gateway.port,
        backend: "fake_headless",
      });
      return;
    }

    sendJson(res, 404, { detail: "Passive route not found." });
  }

  private async handleGatewayRequest(req: IncomingMessage, res: ServerResponse, target: string): Promise<void> {
    const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "127.0.0.1"}`);
    if (req.method === "GET" && url.pathname.endsWith("/capabilities")) {
      sendJson(res, 200, capabilities(target));
      return;
    }
    if (req.method === "POST" && url.pathname.endsWith("/connect")) {
      const body = await readJson(req);
      const bodyRecord = isRecord(body) ? body : {};
      this.connects.push({ target, body: bodyRecord });
      this.handleConnect(res, target, bodyRecord);
      return;
    }
    if (req.method === "POST" && url.pathname.endsWith("/runs")) {
      const body = await readJson(req);
      this.runs.push({ target, body });
      this.handleRun(res, target, body);
      return;
    }
    if (req.method === "DELETE" && url.pathname.includes("/connections/")) {
      const connectionId = decodeURIComponent(url.pathname.split("/").pop() ?? "");
      this.detaches.push({ target, connectionId });
      sendJson(res, 200, {
        status: "detached",
        connectionId,
        detached: true,
        detail: "fake detach",
      });
      return;
    }
    if (url.pathname.includes("interrupt")) {
      this.interruptRequests += 1;
    }
    sendJson(res, 404, { code: "not_found" });
  }

  private handleConnect(res: ServerResponse, target: string, body: Record<string, unknown>): void {
    this.m_openResponses.set(res, target);
    res.on("close", () => {
      this.m_openResponses.delete(res);
    });
    res.writeHead(200, {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
    });
    writeSse(res, {
      type: "STATE_SNAPSHOT",
      snapshot: {
        houmao: {
          connection: {
            connectionId: `${target}-connection-1`,
            threadId: `${target}-thread`,
            runId: `${target}-connect`,
            detached: false,
          },
          gateway: {
            attachIdentity: target,
            backend: "fake_headless",
          },
        },
      },
    });
    const lastSeenEventId = typeof body.lastSeenEventId === "string" ? body.lastSeenEventId : "";
    const activityEventId = lastSeenEventId === `${target}-event-1` ? `${target}-event-2` : `${target}-event-1`;
    const activityMarker =
      activityEventId === `${target}-event-2`
        ? `${target}-reconnect-evidence`
        : `${target}-connect-evidence`;
    writeSse(res, {
      type: "ACTIVITY_SNAPSHOT",
      messageId: `${target}-activity`,
      activityType: "fake-connect",
      content: {
        marker: activityMarker,
      },
    }, activityEventId);
  }

  private handleRun(res: ServerResponse, target: string, body: unknown): void {
    res.writeHead(200, {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
    });
    const runId = stringField(body, "runId", `${target}-run`);
    const threadId = stringField(body, "threadId", `${target}-thread`);
    const messageId = `${target}-assistant`;
    writeSse(res, { type: "RUN_STARTED", runId, threadId });
    writeSse(res, { type: "TEXT_MESSAGE_START", messageId, role: "assistant" });
    writeSse(res, {
      type: "TEXT_MESSAGE_CONTENT",
      messageId,
      delta: target === "operator" ? "operator-only-run-evidence" : `${target}-run-evidence`,
    });
    writeSse(res, { type: "TEXT_MESSAGE_END", messageId });
    if (target === "alpha") {
      writeSse(res, {
        type: "TOOL_CALL_START",
        toolCallId: "alpha-graphic-tool",
        toolCallName: "houmao_render_graphic",
        parentMessageId: messageId,
      });
      writeSse(res, {
        type: "TOOL_CALL_ARGS",
        toolCallId: "alpha-graphic-tool",
        delta: JSON.stringify({
          title: "Alpha SVG Graphic",
          format: "svg",
          altText: "Alpha graphic alt text",
          content:
            '<svg viewBox="0 0 220 90" xmlns="http://www.w3.org/2000/svg"><title>Alpha SVG Graphic</title><rect width="220" height="90" fill="#f7f3e8"/><circle cx="48" cy="45" r="24" fill="#6f8656"/><text x="88" y="51" font-size="20" fill="#1c1a16">alpha svg content</text></svg>',
        }),
      });
      writeSse(res, { type: "TOOL_CALL_END", toolCallId: "alpha-graphic-tool" });
      writeSse(res, {
        type: "TOOL_CALL_START",
        toolCallId: "alpha-dashboard-tool",
        toolCallName: "houmao.dashboard",
        parentMessageId: messageId,
      });
      writeSse(res, {
        type: "TOOL_CALL_ARGS",
        toolCallId: "alpha-dashboard-tool",
        delta: JSON.stringify({
          schemaVersion: 1,
          title: "Alpha Dashboard",
          children: [
            {
              component: "houmao.metric_grid",
              width: "full",
              props: {
                schemaVersion: 1,
                title: "Alpha Metrics",
                metrics: [
                  { label: "Pass rate", value: "98%", delta: "+4%", trend: "up" },
                  { label: "Open blockers", value: 1, delta: "-2", trend: "down" },
                ],
              },
            },
            {
              component: "houmao.chart.bar",
              width: "half",
              props: {
                schemaVersion: 1,
                title: "Alpha Counts",
                data: [
                  { label: "Done", value: 18 },
                  { label: "Review", value: 4 },
                  { label: "Blocked", value: 1 },
                ],
              },
            },
            {
              component: "houmao.table",
              width: "half",
              props: {
                schemaVersion: 1,
                title: "Alpha Table",
                columns: [
                  { key: "name", label: "Name" },
                  { key: "count", label: "Count", kind: "number", align: "right" },
                ],
                rows: [
                  { name: "Alpha count", count: 18 },
                  { name: "Review", count: 4 },
                ],
              },
            },
          ],
        }),
      });
      writeSse(res, { type: "TOOL_CALL_END", toolCallId: "alpha-dashboard-tool" });
    }
    if (target === "beta") {
      writeSse(res, {
        type: "TOOL_CALL_START",
        toolCallId: "beta-graphic-tool",
        toolCallName: "houmao_render_graphic",
        parentMessageId: messageId,
      });
      writeSse(res, {
        type: "TOOL_CALL_ARGS",
        toolCallId: "beta-graphic-tool",
        delta: JSON.stringify({
          title: "Beta Unsupported Graphic",
          format: "iframe",
          content: "<iframe></iframe>",
        }),
      });
      writeSse(res, { type: "TOOL_CALL_END", toolCallId: "beta-graphic-tool" });
      writeSse(res, {
        type: "TOOL_CALL_START",
        toolCallId: "beta-invalid-chart",
        toolCallName: "houmao.chart.bar",
        parentMessageId: messageId,
      });
      writeSse(res, {
        type: "TOOL_CALL_ARGS",
        toolCallId: "beta-invalid-chart",
        delta: JSON.stringify({ schemaVersion: 1, title: "Broken Chart", data: [] }),
      });
      writeSse(res, { type: "TOOL_CALL_END", toolCallId: "beta-invalid-chart" });
      writeSse(res, {
        type: "TOOL_CALL_START",
        toolCallId: "beta-unknown-component",
        toolCallName: "houmao.chart.scatter",
        parentMessageId: messageId,
      });
      writeSse(res, {
        type: "TOOL_CALL_ARGS",
        toolCallId: "beta-unknown-component",
        delta: JSON.stringify({ marker: "beta unknown raw marker" }),
      });
      writeSse(res, { type: "TOOL_CALL_END", toolCallId: "beta-unknown-component" });
    }
    writeSse(res, {
      type: "STATE_SNAPSHOT",
      snapshot: {
        houmao: {
          gateway: {
            attachIdentity: target,
          },
        },
      },
    });
    writeSse(res, { type: "RUN_FINISHED", runId, threadId });
    res.end();
  }
}

function discoveredAgent(agentId: string, hasGateway: boolean): unknown {
  return {
    agent_id: agentId,
    agent_name: `HOUMAO-${agentId}`,
    generation_id: `gen-${agentId}`,
    tool: "kimi",
    backend: "fake_headless",
    tmux_session_name: `houmao-${agentId}`,
    manifest_path: `/tmp/houmao/${agentId}/manifest.json`,
    session_root: `/tmp/houmao/${agentId}`,
    has_gateway: hasGateway,
    has_mailbox: agentId !== "no-gateway",
    published_at: "2026-06-08T00:00:00Z",
    lease_expires_at: "2099-01-01T00:00:00Z",
  };
}

function capabilities(target: string): unknown {
  return {
    capabilities: {
      identity: {
        name: target,
        type: "fake-houmao-gateway",
        provider: "houmao",
      },
      transport: {
        streaming: true,
      },
      state: {
        snapshots: true,
        deltas: false,
      },
      tools: {
        supported: true,
        clientProvided: false,
        items: [
          { name: "houmao_render_graphic" },
          { name: "houmao.chart.bar" },
          { name: "houmao.table" },
          { name: "houmao.metric_grid" },
          { name: "houmao.dashboard" },
        ],
      },
      multimodal: {
        input: { image: false },
      },
    },
    houmao: {
      features: {
        httpSse: true,
        guiConnect: true,
        textInputParsing: true,
        stateSnapshots: true,
        taskRunSubmission: true,
        stateDeltas: false,
        frontendToolExecution: false,
        generatedGraphics: true,
        openGenerativeUi: false,
        multimodalInput: false,
      },
      gateway: {
        attachIdentity: target,
      },
    },
  };
}

function writeSse(res: ServerResponse, event: unknown, eventId?: string): void {
  if (eventId) {
    res.write(`id: ${eventId}\n`);
  }
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  if (chunks.length === 0) {
    return {};
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8")) as unknown;
}

function stringField(value: unknown, key: string, fallback: string): string {
  if (value && typeof value === "object" && typeof (value as Record<string, unknown>)[key] === "string") {
    return (value as Record<string, string>)[key];
  }
  return fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

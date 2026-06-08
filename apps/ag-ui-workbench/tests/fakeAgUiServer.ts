import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";

interface RecordedRun {
  target: string;
  body: unknown;
}

interface RecordedDetach {
  target: string;
  connectionId: string;
}

export class FakeAgUiServer {
  private m_server: Server | null = null;
  private m_port = 0;
  private readonly m_openResponses = new Set<ServerResponse>();

  readonly runs: RecordedRun[] = [];
  readonly detaches: RecordedDetach[] = [];
  interruptRequests = 0;

  async start(): Promise<void> {
    this.m_server = createServer((req, res) => {
      void this.handle(req, res);
    });
    await new Promise<void>((resolve) => {
      this.m_server!.listen(0, "127.0.0.1", resolve);
    });
    const address = this.m_server.address();
    if (!address || typeof address === "string") {
      throw new Error("Fake AG-UI server did not bind a TCP port.");
    }
    this.m_port = address.port;
  }

  async stop(): Promise<void> {
    for (const response of this.m_openResponses) {
      response.end();
    }
    await new Promise<void>((resolve) => this.m_server?.close(() => resolve()));
    this.m_server = null;
  }

  targetBase(target: string): string {
    return `http://127.0.0.1:${this.m_port}/${target}/v1/ag-ui`;
  }

  private async handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "127.0.0.1"}`);
    const target = url.pathname.split("/").filter(Boolean)[0] ?? "unknown";
    if (req.method === "GET" && url.pathname.endsWith("/capabilities")) {
      sendJson(res, 200, capabilities(target));
      return;
    }
    if (req.method === "POST" && url.pathname.endsWith("/connect")) {
      this.handleConnect(req, res, target);
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

  private handleConnect(req: IncomingMessage, res: ServerResponse, target: string): void {
    this.m_openResponses.add(res);
    req.on("close", () => {
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
    writeSse(res, {
      type: "ACTIVITY_SNAPSHOT",
      messageId: `${target}-activity`,
      activityType: "fake-connect",
      content: {
        marker: `${target}-connect-evidence`,
      },
    });
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
        items: [{ name: "houmao_render_graphic" }],
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

function writeSse(res: ServerResponse, event: unknown): void {
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

import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import fastifyStatic from "@fastify/static";
import fastify, {
  type FastifyInstance,
  type FastifyReply,
  type FastifyRequest,
} from "fastify";
import { createServer as createViteServer, type ViteDevServer } from "vite";
import { WebSocketServer } from "ws";

import { detachUrl, normalizeAgUiTargetUrl } from "../shared/agUiTarget";
import {
  WORKBENCH_API_PREFIX,
  validateActiveThreadClearRequest,
  validateActiveThreadSetRequest,
  validateAgUiDetachRequest,
  validateAgUiStreamRequest,
  validateAgUiTargetRequest,
  validateFetchJsonRequest,
  validatePresentationSessionCreateRequest,
  OPERATOR_SESSION_HEADER,
  type AgUiTargetRequest,
  type OperatorSignerSelection,
  type WorkbenchErrorPayload,
} from "../shared/workbenchProtocol";
import {
  configuredAllowedHosts,
  handleProxyRequest,
  HOP_BY_HOP_HEADERS,
  pipeFetchResponseToServerResponse,
  PROXY_PREFIX,
  resolveAllowedTarget,
  sendJson,
} from "./agUiProxy";
import {
  closeDebugAgentStreams,
  closeDebugAgentStreamsForAgent,
  DEBUG_PREFIX,
  debugStatus,
  handleDebugRequest,
} from "./debugAgent";
import { isOperatorLoopbackHost, OperatorSession } from "./operatorSession";
import {
  createProofHelper,
  OperatorSigner,
  OperatorSignerError,
  type OperatorSignerConfig,
  type ProofHelper,
} from "./operatorSigner";
import { PresentationSessionRegistry } from "./presentationSessions";
import { handleTmuxAttachSocket, handleTmuxHttpRequest, TMUX_PREFIX } from "./tmuxBridge";
import type { TmuxPtyAdapterFactory } from "./tmuxPtyAdapter";

export type WorkbenchServerMode = "development" | "static" | "test";

export interface WorkbenchServerOptions {
  host?: string;
  port?: number;
  mode?: WorkbenchServerMode;
  appRoot?: string;
  staticDir?: string;
  presentationSessions?: PresentationSessionRegistry;
  logger?: boolean;
  tmuxPtyAdapterFactory?: TmuxPtyAdapterFactory;
  operatorSignerConfig?: OperatorSignerConfig;
  proofHelper?: ProofHelper;
}

export interface RunningWorkbenchServer {
  app: FastifyInstance;
  url: string;
  operatorLaunchUrl?: string;
  host: string;
  port: number;
  close: () => Promise<void>;
}

interface FetchUpstreamOptions {
  targetUrl: string;
  request: FastifyRequest;
  method: string;
  headers?: HeadersInit;
  body?: string;
  isolate?: boolean;
  signer?: OperatorSignerSelection;
  operator?: OperatorSigner;
}

interface ActiveAgUiStream {
  controller: AbortController;
  targetUrl: string;
}

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 5177;

export async function createWorkbenchFastifyApp(
  options: WorkbenchServerOptions = {},
): Promise<FastifyInstance> {
  const appRoot = options.appRoot ?? defaultAppRoot();
  const mode = options.mode ?? "static";
  const presentationSessions = options.presentationSessions ?? new PresentationSessionRegistry();
  const activeAgUiStreams = new Set<ActiveAgUiStream>();
  const operatorSession = options.operatorSignerConfig ? new OperatorSession() : undefined;
  if (operatorSession && options.host !== undefined && !isOperatorLoopbackHost(options.host)) {
    throw new Error("Local operator signing requires a 127.0.0.1 or ::1 listener.");
  }
  const operator = options.operatorSignerConfig
    ? new OperatorSigner(
        options.operatorSignerConfig,
        options.proofHelper ?? createProofHelper(path.join(appRoot, "src/server/sign_ag_ui_request.py")),
      )
    : undefined;
  if (operatorSession && mode === "development") {
    throw new Error("Build the workbench and use static mode for local operator signing.");
  }
  const app = fastify({
    logger: options.logger ?? false,
    bodyLimit: 2 * 1024 * 1024,
  });

  app.decorate("presentationSessions", presentationSessions);
  app.decorate("operatorSession", operatorSession ?? null);

  operatorSession?.register(app, [WORKBENCH_API_PREFIX, PROXY_PREFIX, DEBUG_PREFIX, TMUX_PREFIX]);
  registerStatusRoutes(app, options, presentationSessions);
  registerAgUiRoutes(app, activeAgUiStreams, operator);
  registerMountedRawRoutes(app, PROXY_PREFIX, operator ? handleIsolatedProxyStatus : handleProxyRequest);
  registerMountedRawRoutes(app, DEBUG_PREFIX, handleDebugRequest);
  registerMountedRawRoutes(app, TMUX_PREFIX, handleTmuxHttpRequest);
  registerTmuxWebSocket(app, options);
  registerPresentationSessionRoutes(app, presentationSessions);

  if (mode === "development") {
    await registerViteDevelopmentFrontend(app, appRoot);
  } else {
    await registerStaticFrontend(app, appRoot, options.staticDir);
  }

  app.addHook("onClose", async () => {
    closeDebugAgentStreams();
    abortActiveAgUiStreams(activeAgUiStreams);
    presentationSessions.clear();
  });

  return app;
}

export async function startWorkbenchServer(
  options: WorkbenchServerOptions = {},
): Promise<RunningWorkbenchServer> {
  const host = options.host ?? process.env.HOUMAO_AG_UI_WORKBENCH_HOST ?? DEFAULT_HOST;
  const port = options.port ?? portFromEnv() ?? DEFAULT_PORT;
  if (options.operatorSignerConfig && !isOperatorLoopbackHost(host)) {
    throw new Error("Local operator signing requires a 127.0.0.1 or ::1 listener.");
  }
  const app = await createWorkbenchFastifyApp(options);
  const address = await app.listen({ host, port });
  return {
    app,
    url: address,
    host,
    port: boundPort(app) ?? port,
    operatorLaunchUrl: app.operatorSession?.setOrigin(address),
    close: async () => {
      await app.close();
    },
  };
}

function registerStatusRoutes(
  app: FastifyInstance,
  options: WorkbenchServerOptions,
  presentationSessions: PresentationSessionRegistry,
): void {
  app.get(`${WORKBENCH_API_PREFIX}/status`, async () => ({
    status: "ready",
    application: "houmao-ag-ui-workbench",
    server: "fastify",
    mode: options.mode ?? "static",
    loopbackHostDefault: DEFAULT_HOST,
    loopbackTargetsAllowed: true,
    extraAllowedHosts: configuredAllowedHosts(),
    protocol: {
      privatePrefix: WORKBENCH_API_PREFIX,
      agUiPeer: "workbench-local-server",
      agUiTransport: "server-owned-http-sse",
    },
    presentationSessions: presentationSessions.diagnostics(),
  }));

  app.get("/healthz", async () => ({
    status: "ready",
    server: "fastify",
  }));
}

function registerAgUiRoutes(
  app: FastifyInstance,
  activeAgUiStreams: Set<ActiveAgUiStream>,
  operator: OperatorSigner | undefined,
): void {
  const sign = (target: AgUiTargetRequest) => ({
    signer: target.signer,
    operator,
    isolate: operator !== undefined,
  });
  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/streams/close-all`, async () => {
    const abortedCount = abortActiveAgUiStreams(activeAgUiStreams);
    closeDebugAgentStreams();
    return {
      status: "closed",
      abortedCount,
      lifecycle: "workbench-streams-only",
      houmaoAgentLifecycleControlled: false,
    };
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/streams/close-target`, async (request, reply) => {
    const validated = validateAgUiTargetRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const abortedCount = abortActiveAgUiStreamsForTarget(activeAgUiStreams, target.baseUrl);
    const debugAgentId = debugAgentIdFromTarget(target.baseUrl);
    const debugClosedCount = debugAgentId ? closeDebugAgentStreamsForAgent(debugAgentId) : 0;
    return reply.send({
      status: "closed",
      abortedCount,
      debugClosedCount,
      lifecycle: "workbench-streams-only",
      houmaoAgentLifecycleControlled: false,
    });
  });


  app.post(`${WORKBENCH_API_PREFIX}/fetch-json`, async (request, reply) => {
    const validated = validateFetchJsonRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const upstream = await fetchAllowedTarget({
      targetUrl: validated.value.targetUrl,
      request,
      method: validated.value.method ?? "GET",
      headers: { accept: "application/json" },
      isolate: operator !== undefined,
    });
    return sendUpstreamAsText(reply, upstream);
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/capabilities`, async (request, reply) => {
    const validated = validateAgUiTargetRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const upstream = await fetchAllowedTarget({
      targetUrl: target.capabilitiesUrl,
      ...sign(validated.value),
      request,
      method: "GET",
      headers: { accept: "application/json" },
    });
    return sendUpstreamAsText(reply, upstream);
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/connect`, async (request, reply) => {
    const validated = validateAgUiStreamRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    return streamUpstream(
      reply,
      {
        targetUrl: target.connectUrl,
        ...sign(validated.value),
        request,
        method: "POST",
        headers: {
          accept: "text/event-stream",
          "content-type": "application/json",
        },
        body: JSON.stringify(validated.value.input),
      },
      activeAgUiStreams,
    );
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/run`, async (request, reply) => {
    const validated = validateAgUiStreamRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    return streamUpstream(
      reply,
      {
        targetUrl: target.runsUrl,
        ...sign(validated.value),
        request,
        method: "POST",
        headers: {
          accept: "text/event-stream",
          "content-type": "application/json",
        },
        body: JSON.stringify(validated.value.input),
      },
      activeAgUiStreams,
    );
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/detach`, async (request, reply) => {
    const validated = validateAgUiDetachRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    if (!validated.value.connectionId) {
      return reply.send({ detached: false, skipped: true });
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const upstream = await fetchAllowedTarget({
      targetUrl: detachUrl(target, validated.value.connectionId),
      ...sign(validated.value),
      request,
      method: "DELETE",
      headers: { accept: "application/json" },
    });
    const response = await sendUpstreamAsText(reply, upstream);
    abortActiveAgUiStreamsForTarget(activeAgUiStreams, target.baseUrl);
    return response;
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/destination`, async (request, reply) => {
    const validated = validateAgUiTargetRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const upstream = await fetchAllowedTarget({
      targetUrl: `${target.baseUrl}/destination`,
      ...sign(validated.value),
      request,
      method: "GET",
      headers: { accept: "application/json" },
    });
    return sendUpstreamAsText(reply, upstream);
  });

  app.post(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, async (request, reply) => {
    const validated = validateAgUiTargetRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const upstream = await fetchAllowedTarget({
      targetUrl: `${target.baseUrl}/active-thread`,
      ...sign(validated.value),
      request,
      method: "GET",
      headers: { accept: "application/json" },
    });
    return sendUpstreamAsText(reply, upstream);
  });

  app.put(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, async (request, reply) => {
    const validated = validateActiveThreadSetRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const upstream = await fetchAllowedTarget({
      targetUrl: `${target.baseUrl}/active-thread`,
      ...sign(validated.value),
      request,
      method: "PUT",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        threadId: validated.value.threadId,
        source: validated.value.source,
      }),
    });
    return sendUpstreamAsText(reply, upstream);
  });

  app.delete(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, async (request, reply) => {
    const validated = validateActiveThreadClearRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    const target = normalizeAgUiTargetUrl(validated.value.targetUrl);
    const endpoint = new URL(`${target.baseUrl}/active-thread`);
    if (validated.value.expectedThreadId) {
      endpoint.searchParams.set("threadId", validated.value.expectedThreadId);
    }
    const upstream = await fetchAllowedTarget({
      targetUrl: endpoint.toString(),
      ...sign(validated.value),
      request,
      method: "DELETE",
      headers: { accept: "application/json" },
    });
    return sendUpstreamAsText(reply, upstream);
  });
}

function registerMountedRawRoutes(
  app: FastifyInstance,
  prefix: string,
  handler: (req: FastifyRequest["raw"], res: FastifyReply["raw"]) => Promise<void>,
): void {
  const handle = async (request: FastifyRequest, reply: FastifyReply) => {
    const originalUrl = request.raw.url;
    const rawWithOverride = request.raw as FastifyRequest["raw"] & {
      __houmaoBodyOverride?: Buffer;
    };
    request.raw.url = stripMountedPrefix(originalUrl ?? "/", prefix);
    rawWithOverride.__houmaoBodyOverride = bodyOverrideBuffer(request.body);
    reply.hijack();
    try {
      await handler(request.raw, reply.raw);
    } finally {
      request.raw.url = originalUrl;
      delete rawWithOverride.__houmaoBodyOverride;
    }
  };
  app.all(prefix, handle);
  app.all(`${prefix}/*`, handle);
}

function registerTmuxWebSocket(app: FastifyInstance, options: WorkbenchServerOptions): void {
  const wss = new WebSocketServer({ noServer: true });
  wss.on("connection", (ws) => {
    if (app.operatorSession) {
      const expiry = setTimeout(
        () => ws.close(1008, "operator session expired"),
        app.operatorSession.remainingSessionMs(),
      );
      expiry.unref();
      ws.once("close", () => clearTimeout(expiry));
    }
    handleTmuxAttachSocket(ws, {
      ptyAdapterFactory: options.tmuxPtyAdapterFactory,
    });
  });
  app.server.on("upgrade", (req, socket, head) => {
    const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
    if (requestUrl.pathname !== `${TMUX_PREFIX}/attach`) {
      return;
    }
    if (app.operatorSession && !app.operatorSession.authorizesUpgrade(req)) {
      socket.end("HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n");
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  });
  app.addHook("onClose", async () => {
    for (const client of wss.clients) {
      client.close(1001, "workbench server closing");
    }
    wss.close();
  });
}

async function handleIsolatedProxyStatus(
  request: FastifyRequest["raw"],
  reply: FastifyReply["raw"],
): Promise<void> {
  if (request.method === "GET" && request.url === "/status") {
    sendJson(reply, 200, {
      status: "ready",
      loopbackTargetsAllowed: true,
      extraAllowedHosts: configuredAllowedHosts(),
      operatorSigning: true,
    });
    return;
  }
  sendJson(reply, 403, {
    code: "generic_proxy_unavailable",
    detail: "Use the workbench's private JSON and AG-UI operations.",
  });
}

function registerPresentationSessionRoutes(
  app: FastifyInstance,
  presentationSessions: PresentationSessionRegistry,
): void {
  app.get(`${WORKBENCH_API_PREFIX}/presentation-sessions`, async () => ({
    sessions: presentationSessions.list(),
    diagnostics: presentationSessions.diagnostics(),
  }));

  app.post(`${WORKBENCH_API_PREFIX}/presentation-sessions`, async (request, reply) => {
    const validated = validatePresentationSessionCreateRequest(request.body);
    if (!validated.ok) {
      return sendValidationError(reply, validated.error);
    }
    return reply.status(201).send({
      session: presentationSessions.create(validated.value),
      diagnostics: presentationSessions.diagnostics(),
    });
  });

  app.get(`${WORKBENCH_API_PREFIX}/presentation-sessions/:sessionId`, async (request, reply) => {
    const sessionId = stringParam(request.params, "sessionId");
    const session = presentationSessions.get(sessionId);
    if (!session) {
      return reply.status(404).send({
        code: "session_missing",
        detail: "Presentation session was not found.",
      });
    }
    return reply.send({
      session,
      diagnostics: presentationSessions.diagnostics(),
    });
  });

  app.delete(`${WORKBENCH_API_PREFIX}/presentation-sessions/:sessionId`, async (request, reply) => {
    const sessionId = stringParam(request.params, "sessionId");
    const disposed = presentationSessions.dispose(sessionId);
    return reply.send({
      disposed,
      sessionId,
      lifecycle: "presentation-only",
      houmaoAgentLifecycleControlled: false,
      diagnostics: presentationSessions.diagnostics(),
    });
  });
}

async function registerStaticFrontend(
  app: FastifyInstance,
  appRoot: string,
  staticDir: string | undefined,
): Promise<void> {
  const root = staticDir ?? path.join(appRoot, "dist");
  if (!existsSync(root)) {
    app.setNotFoundHandler(async (_request, reply) => {
      reply.status(404).send({
        code: "frontend_not_built",
        detail: `Built frontend assets were not found at ${root}. Run bun run build first or start development mode.`,
      });
    });
    return;
  }
  await app.register(fastifyStatic, {
    root,
    prefix: "/",
    decorateReply: true,
  });
  app.setNotFoundHandler(async (request, reply) => {
    if (request.method === "GET" && acceptsHtml(request)) {
      return reply.sendFile("index.html");
    }
    return reply.status(404).send({
      code: "not_found",
      detail: "Workbench route not found.",
    });
  });
}

async function registerViteDevelopmentFrontend(
  app: FastifyInstance,
  appRoot: string,
): Promise<void> {
  const previous = process.env.HOUMAO_AG_UI_WORKBENCH_FASTIFY_FRONTEND;
  process.env.HOUMAO_AG_UI_WORKBENCH_FASTIFY_FRONTEND = "1";
  let vite: ViteDevServer;
  try {
    vite = await createViteServer({
      root: appRoot,
      configFile: path.join(appRoot, "vite.config.ts"),
      server: {
        middlewareMode: true,
        hmr: {
          server: app.server,
        },
      },
      appType: "spa",
    });
  } finally {
    if (typeof previous === "undefined") {
      delete process.env.HOUMAO_AG_UI_WORKBENCH_FASTIFY_FRONTEND;
    } else {
      process.env.HOUMAO_AG_UI_WORKBENCH_FASTIFY_FRONTEND = previous;
    }
  }
  app.addHook("onClose", async () => {
    await vite.close();
  });
  app.all("/*", async (request, reply) => {
    reply.hijack();
    vite.middlewares(request.raw, reply.raw, (error?: unknown) => {
      if (error) {
        if (error instanceof Error) {
          vite.ssrFixStacktrace(error);
        }
        if (!reply.raw.writableEnded) {
          reply.raw.statusCode = 500;
          reply.raw.end(error instanceof Error ? error.message : "Vite middleware failed.");
        }
        return;
      }
      if (!reply.raw.writableEnded) {
        reply.raw.statusCode = 404;
        reply.raw.end("Not found");
      }
    });
  });
}

async function fetchAllowedTarget(options: FetchUpstreamOptions): Promise<Response> {
  const policy = resolveAllowedTarget(options.targetUrl);
  if (!policy.allowed) {
    return new Response(JSON.stringify({ code: policy.code, detail: policy.detail }), {
      status: policy.status,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  }
  const abortController = new AbortController();
  const abortUpstream = () => abortController.abort();
  options.request.raw.on("aborted", abortUpstream);
  try {
    return await performUpstreamRequest(options, policy.url, abortController.signal);
  } catch (error) {
    if (abortController.signal.aborted) {
      return new Response("", { status: 499, statusText: "Client Closed Request" });
    }
    return new Response(
      JSON.stringify({
        code: "upstream_failed",
        detail: error instanceof Error ? error.message : "AG-UI upstream request failed.",
      }),
      {
        status: 502,
        headers: { "content-type": "application/json; charset=utf-8" },
      },
    );
  } finally {
    options.request.raw.off("aborted", abortUpstream);
  }
}

async function streamUpstream(
  reply: FastifyReply,
  options: FetchUpstreamOptions,
  activeAgUiStreams: Set<ActiveAgUiStream>,
): Promise<void> {
  const policy = resolveAllowedTarget(options.targetUrl);
  if (!policy.allowed) {
    reply.hijack();
    sendJson(reply.raw, policy.status, {
      code: policy.code,
      detail: policy.detail,
    });
    return;
  }

  const abortController = new AbortController();
  const streamRecord: ActiveAgUiStream = {
    controller: abortController,
    targetUrl: options.targetUrl,
  };
  activeAgUiStreams.add(streamRecord);
  const abortUpstream = () => abortController.abort();
  options.request.raw.on("aborted", abortUpstream);
  reply.raw.on("close", abortUpstream);
  try {
    const upstream = await performUpstreamRequest(options, policy.url, abortController.signal);
    reply.hijack();
    await pipeFetchResponseToServerResponse(upstream, reply.raw);
  } catch (error) {
    reply.hijack();
    if (abortController.signal.aborted) {
      if (!reply.raw.writableEnded) {
        reply.raw.end();
      }
      return;
    }
    sendJson(reply.raw, 502, {
      code: "upstream_failed",
      detail: error instanceof Error ? error.message : "AG-UI upstream stream failed.",
    });
  } finally {
    options.request.raw.off("aborted", abortUpstream);
    reply.raw.off("close", abortUpstream);
    activeAgUiStreams.delete(streamRecord);
  }
}

async function performUpstreamRequest(
  options: FetchUpstreamOptions,
  url: string,
  signal: AbortSignal,
): Promise<Response> {
  const headers = forwardedPrivateHeaders(options.headers);
  let destination = url;
  if (options.signer !== undefined) {
    if (options.operator === undefined) {
      return errorResponse(403, "operator_signer_unavailable", "This workbench has no configured operator signer.");
    }
    try {
      const proof = await options.operator.prepare(
        options.signer, url, options.method, options.body ?? "", signal,
      );
      destination = proof.url;
      for (const [name, value] of Object.entries(proof.headers)) {
        headers.set(name, value);
      }
    } catch (error) {
      if (error instanceof OperatorSignerError) {
        return errorResponse(error.status, error.code, error.message);
      }
      return errorResponse(502, "operator_proof_unavailable", "The configured operator proof is unavailable.");
    }
  }
  const upstreamUrl = new URL(destination);
  if (
    options.isolate &&
    options.signer === undefined &&
    upstreamUrl.protocol === "http:" &&
    upstreamUrl.host === options.request.headers.host &&
    upstreamUrl.pathname.startsWith(`${DEBUG_PREFIX}/`)
  ) {
    const session = options.request.headers[OPERATOR_SESSION_HEADER];
    if (typeof session === "string") {
      headers.set(OPERATOR_SESSION_HEADER, session);
      headers.set("origin", upstreamUrl.origin);
    }
  }
  const upstream = await fetch(destination, {
    method: options.method,
    headers,
    body: options.body,
    redirect: options.isolate ? "manual" : "follow",
    signal,
  });
  if (!options.isolate) {
    return upstream;
  }
  if (upstream.status >= 300 && upstream.status < 400) {
    await upstream.body?.cancel();
    return errorResponse(403, "upstream_redirect_refused", "The workbench refused an upstream redirect.");
  }
  if (upstream.status === 401 || upstream.status === 403) {
    await upstream.body?.cancel();
    return errorResponse(upstream.status, "upstream_authorization_refused", "The gateway refused the selected operation.");
  }
  const contentType = upstream.headers.get("content-type")?.split(";", 1)[0].toLowerCase();
  const acceptsSse = headers.get("accept") === "text/event-stream";
  if (
    upstream.body !== null &&
    contentType !== "application/json" &&
    !(acceptsSse && contentType === "text/event-stream")
  ) {
    await upstream.body.cancel();
    return errorResponse(502, "upstream_content_refused", "The workbench requires JSON or AG-UI event data.");
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": `${contentType ?? "application/json"}; charset=utf-8`,
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
    },
  });
}

function errorResponse(status: number, code: string, detail: string): Response {
  return Response.json({ code, detail }, { status });
}

async function sendUpstreamAsText(reply: FastifyReply, upstream: Response): Promise<FastifyReply> {
  reply.status(upstream.status);
  for (const [name, value] of upstream.headers.entries()) {
    if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) {
      reply.header(name, value);
    }
  }
  return reply.send(await upstream.text());
}

function sendValidationError(reply: FastifyReply, payload: WorkbenchErrorPayload): FastifyReply {
  return reply.status(payload.code === "target_missing" ? 400 : 422).send(payload);
}

function forwardedPrivateHeaders(extra: HeadersInit = {}): Headers {
  const headers = new Headers(extra);
  headers.set("x-houmao-ag-ui-workbench-server", "1");
  return headers;
}

function stripMountedPrefix(value: string, prefix: string): string {
  const url = new URL(value, "http://127.0.0.1");
  if (url.pathname === prefix) {
    url.pathname = "/";
  } else if (url.pathname.startsWith(`${prefix}/`)) {
    url.pathname = url.pathname.slice(prefix.length);
  }
  return `${url.pathname}${url.search}`;
}

function acceptsHtml(request: FastifyRequest): boolean {
  const accept = request.headers.accept;
  return typeof accept === "string" && accept.includes("text/html");
}

function stringParam(params: unknown, key: string): string {
  if (params && typeof params === "object") {
    const value = (params as Record<string, unknown>)[key];
    return typeof value === "string" ? value : "";
  }
  return "";
}

function bodyOverrideBuffer(body: unknown): Buffer | undefined {
  if (typeof body === "undefined") {
    return undefined;
  }
  if (Buffer.isBuffer(body)) {
    return body;
  }
  if (typeof body === "string") {
    return Buffer.from(body);
  }
  return Buffer.from(JSON.stringify(body));
}

function abortActiveAgUiStreams(activeAgUiStreams: Set<ActiveAgUiStream>): number {
  const streams = [...activeAgUiStreams];
  for (const stream of streams) {
    stream.controller.abort();
  }
  activeAgUiStreams.clear();
  return streams.length;
}

function abortActiveAgUiStreamsForTarget(
  activeAgUiStreams: Set<ActiveAgUiStream>,
  targetBaseUrl: string,
): number {
  const streams = [...activeAgUiStreams].filter((stream) =>
    stream.targetUrl.startsWith(targetBaseUrl),
  );
  for (const stream of streams) {
    stream.controller.abort();
    activeAgUiStreams.delete(stream);
  }
  return streams.length;
}

function debugAgentIdFromTarget(targetBaseUrl: string): string | null {
  let url: URL;
  try {
    url = new URL(targetBaseUrl);
  } catch {
    return null;
  }
  const segments = url.pathname.split("/").filter(Boolean);
  const debugIndex = segments.indexOf(DEBUG_PREFIX.replace(/^\//, ""));
  if (debugIndex < 0) {
    return null;
  }
  const agentId = segments[debugIndex + 1];
  return agentId || null;
}

function defaultAppRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
}

function portFromEnv(): number | undefined {
  const raw = process.env.HOUMAO_AG_UI_WORKBENCH_PORT;
  if (!raw) {
    return undefined;
  }
  const port = Number.parseInt(raw, 10);
  return Number.isInteger(port) && port > 0 ? port : undefined;
}

function boundPort(app: FastifyInstance): number | undefined {
  const address = app.server.address();
  if (!address || typeof address === "string") {
    return undefined;
  }
  return address.port;
}

declare module "fastify" {
  interface FastifyInstance {
    presentationSessions: PresentationSessionRegistry;
    operatorSession: OperatorSession | null;
  }
}

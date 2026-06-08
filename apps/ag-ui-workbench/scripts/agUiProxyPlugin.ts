import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

const PROXY_PREFIX = "/__houmao_ag_ui_proxy";
const ALLOWED_HOSTS_ENV = "HOUMAO_AG_UI_WORKBENCH_ALLOWED_HOSTS";
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

export function houmaoAgUiProxyPlugin(): Plugin {
  return {
    name: "houmao-ag-ui-proxy",
    configureServer(server) {
      server.middlewares.use(PROXY_PREFIX, (req, res) => {
        void handleProxyRequest(req, res);
      });
    },
  };
}

async function handleProxyRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
  if (req.method === "GET" && requestUrl.pathname === "/status") {
    sendJson(res, 200, {
      status: "ready",
      loopbackTargetsAllowed: true,
      extraAllowedHosts: configuredAllowedHosts(),
    });
    return;
  }

  const targetValue = requestUrl.searchParams.get("target");
  const policy = resolveAllowedTarget(targetValue);
  if (!policy.allowed) {
    sendJson(res, policy.status, {
      code: policy.code,
      detail: policy.detail,
    });
    return;
  }

  const abortController = new AbortController();
  const abortUpstream = () => abortController.abort();
  req.on("aborted", abortUpstream);
  res.on("close", abortUpstream);

  try {
    const body = await readRequestBody(req);
    const upstream = await fetch(policy.url, {
      method: req.method ?? "GET",
      headers: forwardedRequestHeaders(req),
      body: body ? new Uint8Array(body) : undefined,
      signal: abortController.signal,
    });
    res.statusCode = upstream.status;
    res.statusMessage = upstream.statusText;
    for (const [name, value] of upstream.headers.entries()) {
      if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) {
        res.setHeader(name, value);
      }
    }
    if (!upstream.body) {
      res.end();
      return;
    }
    const reader = upstream.body.getReader();
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) {
        break;
      }
      if (!res.write(Buffer.from(chunk.value))) {
        await new Promise<void>((resolve) => res.once("drain", resolve));
      }
    }
    res.end();
  } catch (error) {
    if (abortController.signal.aborted) {
      if (!res.writableEnded) {
        res.end();
      }
      return;
    }
    sendJson(res, 502, {
      code: "ag_ui_proxy_failed",
      detail: error instanceof Error ? error.message : "AG-UI proxy request failed.",
    });
  } finally {
    req.off("aborted", abortUpstream);
    res.off("close", abortUpstream);
  }
}

function forwardedRequestHeaders(req: IncomingMessage): Headers {
  const headers = new Headers();
  for (const [name, value] of Object.entries(req.headers)) {
    const lowered = name.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lowered) || lowered === "host" || typeof value === "undefined") {
      continue;
    }
    if (Array.isArray(value)) {
      for (const entry of value) {
        headers.append(name, entry);
      }
    } else {
      headers.set(name, value);
    }
  }
  headers.set("x-houmao-ag-ui-workbench-proxy", "1");
  return headers;
}

async function readRequestBody(req: IncomingMessage): Promise<Buffer | undefined> {
  if (req.method === "GET" || req.method === "HEAD") {
    return undefined;
  }
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return chunks.length > 0 ? Buffer.concat(chunks) : undefined;
}

interface TargetPolicyResult {
  allowed: boolean;
  status: number;
  code: string;
  detail: string;
  url: string;
}

function resolveAllowedTarget(value: string | null): TargetPolicyResult {
  if (!value) {
    return {
      allowed: false,
      status: 400,
      code: "target_missing",
      detail: "Missing AG-UI target URL.",
      url: "",
    };
  }
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return {
      allowed: false,
      status: 400,
      code: "target_invalid",
      detail: "AG-UI target URL is invalid.",
      url: "",
    };
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    return {
      allowed: false,
      status: 403,
      code: "target_policy_rejected",
      detail: "AG-UI proxy only allows HTTP or HTTPS targets.",
      url: url.toString(),
    };
  }
  if (!isLoopbackHostname(url.hostname) && !isConfiguredAllowedHost(url)) {
    return {
      allowed: false,
      status: 403,
      code: "target_policy_rejected",
      detail: "AG-UI proxy rejected a non-loopback target.",
      url: url.toString(),
    };
  }
  return {
    allowed: true,
    status: 200,
    code: "ok",
    detail: "Allowed.",
    url: url.toString(),
  };
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replace(/^\[/, "").replace(/\]$/, "");
  return (
    normalized === "localhost" ||
    normalized === "::1" ||
    normalized === "0:0:0:0:0:0:0:1" ||
    normalized === "0.0.0.0" ||
    normalized.startsWith("127.")
  );
}

function isConfiguredAllowedHost(url: URL): boolean {
  const allowed = new Set(configuredAllowedHosts());
  return allowed.has(url.hostname) || allowed.has(url.host);
}

function configuredAllowedHosts(): string[] {
  return (process.env[ALLOWED_HOSTS_ENV] ?? "")
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  if (res.writableEnded) {
    return;
  }
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

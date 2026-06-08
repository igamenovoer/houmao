import { proxiedTargetUrl } from "./target";
import type {
  DiscoveredAgentListResponse,
  DiscoveredAgentSummary,
  GatewayStatusSubset,
  ResolvedDiscoveredTarget,
} from "./types";

export class DiscoveryHttpError extends Error {
  readonly status: number;
  readonly body: string;

  constructor(message: string, status: number, body: string) {
    super(message);
    this.name = "DiscoveryHttpError";
    this.status = status;
    this.body = body;
  }
}

export async function fetchDiscoveredAgents(
  passiveServerUrl: string,
  signal?: AbortSignal,
): Promise<DiscoveredAgentSummary[]> {
  const base = normalizePassiveServerBase(passiveServerUrl);
  const response = await fetchJson<DiscoveredAgentListResponse>(routeUrl(base, "/houmao/agents"), signal);
  return Array.isArray(response.agents) ? response.agents : [];
}

export async function resolveDiscoveredAgentTarget(
  passiveServerUrl: string,
  agent: DiscoveredAgentSummary,
  signal?: AbortSignal,
): Promise<ResolvedDiscoveredTarget> {
  if (!agent.has_gateway) {
    throw new DiscoveryHttpError(
      `${agent.agent_name} has no gateway attached.`,
      502,
      `${agent.agent_name} has no gateway attached.`,
    );
  }
  const base = normalizePassiveServerBase(passiveServerUrl);
  const gatewayStatus = await fetchJson<GatewayStatusSubset>(
    routeUrl(base, `/houmao/agents/${encodeURIComponent(agent.agent_id)}/gateway`),
    signal,
  );
  const gatewayHost = typeof gatewayStatus.gateway_host === "string" ? gatewayStatus.gateway_host : "";
  const gatewayPort = typeof gatewayStatus.gateway_port === "number" ? gatewayStatus.gateway_port : 0;
  if (!gatewayHost || !Number.isInteger(gatewayPort) || gatewayPort <= 0) {
    throw new DiscoveryHttpError(
      `${agent.agent_name} gateway coordinates are unavailable.`,
      502,
      `${agent.agent_name} gateway coordinates are unavailable.`,
    );
  }
  const targetHost = browserReachableGatewayHost(gatewayHost, base);
  const targetUrl = new URL("http://127.0.0.1");
  targetUrl.hostname = targetHost;
  targetUrl.port = String(gatewayPort);
  targetUrl.pathname = "/v1/ag-ui";
  return {
    agent,
    gatewayStatus,
    target: {
      label: agent.agent_name || agent.agent_id,
      url: targetUrl.toString(),
      threadId: threadIdForAgent(agent),
      source: {
        kind: "discovered",
        passiveServerUrl: base.toString(),
        agentId: agent.agent_id,
        agentName: agent.agent_name,
        generationId: agent.generation_id,
        tool: agent.tool,
        backend: agent.backend,
      },
    },
  };
}

export function normalizePassiveServerUrlValue(value: string): string {
  return normalizePassiveServerBase(value).toString();
}

export function discoveryErrorMessage(error: unknown): string {
  if (error instanceof DiscoveryHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "Houmao agent discovery failed.";
}

export function agentRowTestId(agent: DiscoveredAgentSummary): string {
  return `agent-row-${safeToken(agent.agent_id || agent.agent_name)}`;
}

function normalizePassiveServerBase(value: string): URL {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error("Passive server URL is required.");
  }
  const url = new URL(trimmed);
  url.hash = "";
  url.search = "";
  const segments = url.pathname.split("/").filter(Boolean);
  const agentsIndex = lastSubsequenceIndex(segments, ["houmao", "agents"]);
  if (agentsIndex >= 0) {
    url.pathname = `/${segments.slice(0, agentsIndex).join("/")}`;
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  if (!url.pathname) {
    url.pathname = "/";
  }
  return url;
}

function routeUrl(base: URL, path: string): string {
  const url = new URL(base.toString());
  const prefix = url.pathname.replace(/\/+$/, "");
  url.pathname = `${prefix === "/" ? "" : prefix}${path}`;
  return url.toString();
}

async function fetchJson<T>(targetUrl: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(proxiedTargetUrl(targetUrl), {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  const body = await response.text();
  if (!response.ok) {
    throw new DiscoveryHttpError(
      response.statusText || `HTTP ${response.status}`,
      response.status,
      errorBodyText(body),
    );
  }
  if (!body) {
    throw new DiscoveryHttpError("Discovery response was empty.", response.status, "empty_response");
  }
  try {
    return JSON.parse(body) as T;
  } catch {
    throw new DiscoveryHttpError("Discovery response was not JSON.", response.status, body.slice(0, 240));
  }
}

function errorBodyText(body: string): string {
  if (!body) {
    return "request_failed";
  }
  try {
    const parsed = JSON.parse(body) as unknown;
    if (isRecord(parsed)) {
      const detail = parsed.detail;
      const code = parsed.code;
      if (typeof detail === "string" && typeof code === "string") {
        return `${code}: ${detail}`;
      }
      if (typeof detail === "string") {
        return detail;
      }
      if (typeof code === "string") {
        return code;
      }
    }
  } catch {
    return body.slice(0, 240);
  }
  return body.slice(0, 240);
}

function browserReachableGatewayHost(gatewayHost: string, passiveServerUrl: URL): string {
  const normalized = gatewayHost.toLowerCase().replace(/^\[/, "").replace(/\]$/, "");
  if (normalized === "0.0.0.0" || normalized === "::" || normalized === "") {
    const passiveHost = passiveServerUrl.hostname.replace(/^\[/, "").replace(/\]$/, "");
    return passiveHost === "0.0.0.0" || passiveHost === "::" ? "127.0.0.1" : passiveHost;
  }
  return gatewayHost;
}

function threadIdForAgent(agent: DiscoveredAgentSummary): string {
  const base = safeToken(agent.agent_id || agent.agent_name || "agent");
  return `${base}-thread`;
}

function safeToken(value: string): string {
  const sanitized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return sanitized || "agent";
}

function lastSubsequenceIndex(values: string[], subsequence: string[]): number {
  for (let index = values.length - subsequence.length; index >= 0; index -= 1) {
    if (subsequence.every((value, offset) => values[index + offset] === value)) {
      return index;
    }
  }
  return -1;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

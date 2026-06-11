import type {
  AgentAddressResolvedAgent,
  DiscoveredAgentListResponse,
  DiscoveredAgentSummary,
  GatewayStatusSubset,
  PassiveAgentAddressResolveResponse,
  ResolvedDiscoveredTarget,
  TargetConfig,
} from "./types";
import { WORKBENCH_API_PREFIX } from "../shared/workbenchProtocol";

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

export class AgentAddressUnavailableError extends Error {
  constructor(
    readonly address: PassiveAgentAddressResolveResponse,
  ) {
    super(address.detail || "Agent gateway is not currently available.");
    this.name = "AgentAddressUnavailableError";
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
  return resolveAgentAddressTarget(passiveServerUrl, agent.agent_id, signal, {
    agent,
  });
}

export async function resolveStoredDiscoveredTarget(
  target: TargetConfig,
  signal?: AbortSignal,
): Promise<ResolvedDiscoveredTarget> {
  const source = target.source;
  if (source?.kind !== "discovered") {
    throw new Error("Target is not a discovered Houmao agent.");
  }
  return resolveAgentAddressTarget(
    source.passiveServerUrl,
    source.agentRef || source.agentId || source.agentName,
    signal,
    {
      threadId: target.threadId,
      label: target.label,
      source,
    },
  );
}

export async function resolveTargetConfigForConnect(
  target: TargetConfig,
  signal?: AbortSignal,
): Promise<TargetConfig> {
  if (target.source?.kind !== "discovered") {
    return target;
  }
  const resolved = await resolveStoredDiscoveredTarget(target, signal);
  if (resolved.address.status !== "live_with_gateway") {
    throw new AgentAddressUnavailableError(resolved.address);
  }
  return resolved.target;
}

export async function resolveAgentAddressTarget(
  passiveServerUrl: string,
  agentRef: string,
  signal?: AbortSignal,
  context: {
    agent?: DiscoveredAgentSummary;
    source?: Extract<TargetConfig["source"], { kind: "discovered" }>;
    threadId?: string;
    label?: string;
  } = {},
): Promise<ResolvedDiscoveredTarget> {
  const base = normalizePassiveServerBase(passiveServerUrl);
  const address = await fetchJson<PassiveAgentAddressResolveResponse>(
    routeUrl(base, `/houmao/agents/${encodeURIComponent(agentRef)}/resolve`),
    signal,
  );
  if (address.status === "unknown" || address.status === "ambiguous") {
    throw new DiscoveryHttpError(
      address.detail || `Agent address resolution failed for ${agentRef}.`,
      address.status === "ambiguous" ? 409 : 404,
      address.detail || address.status,
    );
  }
  const agent = agentFromAddress(address, context.agent);
  const gateway = address.gateway ?? null;
  const targetUrl = gateway ? gatewayUrlForAddress(gateway.host, gateway.port, base) : "";
  const source = context.source;
  return {
    agent,
    address,
    gatewayStatus: gateway
      ? {
          gateway_host: gateway.host,
          gateway_port: gateway.port,
          protocol_version: gateway.protocolVersion,
        }
      : undefined,
    target: {
      label: context.label || agent.agent_name || agent.agent_id,
      url: targetUrl,
      threadId: context.threadId || threadIdForAgent(agent),
      source: {
        kind: "discovered",
        passiveServerUrl: base.toString(),
        agentId: agent.agent_id,
        agentName: agent.agent_name,
        agentRef,
        generationId: agent.generation_id || source?.generationId,
        tool: agent.tool || source?.tool,
        backend: agent.backend || source?.backend,
        addressStatus: address.status,
      },
    },
  };
}

export function normalizePassiveServerUrlValue(value: string): string {
  return normalizePassiveServerBase(value).toString();
}

export function discoveryErrorMessage(error: unknown): string {
  if (error instanceof AgentAddressUnavailableError) {
    return error.address.detail || error.message;
  }
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
  const response = await fetch(`${WORKBENCH_API_PREFIX}/fetch-json`, {
    method: "POST",
    signal,
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ targetUrl, method: "GET" }),
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

function gatewayUrlForAddress(gatewayHost: string, gatewayPort: number, passiveServerUrl: URL): string {
  if (!gatewayHost || !Number.isInteger(gatewayPort) || gatewayPort <= 0) {
    return "";
  }
  const targetHost = browserReachableGatewayHost(gatewayHost, passiveServerUrl);
  const targetUrl = new URL("http://127.0.0.1");
  targetUrl.hostname = targetHost;
  targetUrl.port = String(gatewayPort);
  targetUrl.pathname = "/v1/ag-ui";
  return targetUrl.toString();
}

function browserReachableGatewayHost(gatewayHost: string, passiveServerUrl: URL): string {
  const normalized = gatewayHost.toLowerCase().replace(/^\[/, "").replace(/\]$/, "");
  if (normalized === "0.0.0.0" || normalized === "::" || normalized === "") {
    const passiveHost = passiveServerUrl.hostname.replace(/^\[/, "").replace(/\]$/, "");
    return passiveHost === "0.0.0.0" || passiveHost === "::" ? "127.0.0.1" : passiveHost;
  }
  return gatewayHost;
}

function agentFromAddress(
  address: PassiveAgentAddressResolveResponse,
  fallback?: DiscoveredAgentSummary,
): AgentAddressResolvedAgent {
  return {
    agent_id: address.agentId || fallback?.agent_id || address.agentRef,
    agent_name: address.agentName || fallback?.agent_name || address.agentRef,
    generation_id: address.generationId || fallback?.generation_id,
    tool: address.tool || fallback?.tool,
    backend: address.backend || fallback?.backend,
  };
}

function threadIdForAgent(agent: AgentAddressResolvedAgent | DiscoveredAgentSummary): string {
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

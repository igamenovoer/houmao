import type { SerializedDockview } from "dockview-react";

import type { AgentAddressResolveStatus, TargetConfig } from "./ag-ui/types";

export type PaneKind = "operator" | "agent" | "debug-agent";

export interface DebugAgentConfig {
  debugAgentId: string;
  replayEnabled: boolean;
}

export interface PaneRecord {
  paneId: string;
  kind: PaneKind;
  target: TargetConfig;
  resetToken?: number;
  debugAgent?: DebugAgentConfig;
}

export interface DiscoveryConfig {
  passiveServerUrl: string;
}

export interface WorkbenchStorage {
  discovery: DiscoveryConfig;
  layout?: unknown;
  panes: Record<string, PaneRecord>;
  nextAgentIndex: number;
  nextDebugAgentIndex: number;
}

const STORAGE_KEY = "houmao.agUiWorkbench.v1";
const DEFAULT_PASSIVE_SERVER_URL = "http://127.0.0.1:9891";

export function defaultTarget(paneId: string, kind: PaneKind): TargetConfig {
  if (kind === "debug-agent") {
    const debugAgentId = defaultDebugAgentConfig(paneId).debugAgentId;
    return {
      label: debugAgentId.replace(/-/g, " "),
      url: debugAgentUrl(debugAgentId),
      threadId: `${debugAgentId}-thread`,
      source: { kind: "manual" },
    };
  }
  return {
    label: kind === "operator" ? "Operator" : paneId.replace(/-/g, " "),
    url: "",
    threadId: kind === "operator" ? "operator-thread" : `${paneId}-thread`,
    source: { kind: "manual" },
  };
}

export function defaultDebugAgentConfig(paneId: string): DebugAgentConfig {
  return {
    debugAgentId: paneId.startsWith("debug-agent-") ? paneId : "debug-agent-1",
    replayEnabled: true,
  };
}

export function defaultStorage(): WorkbenchStorage {
  return {
    discovery: {
      passiveServerUrl: DEFAULT_PASSIVE_SERVER_URL,
    },
    panes: {
      operator: {
        paneId: "operator",
        kind: "operator",
        target: defaultTarget("operator", "operator"),
      },
    },
    nextAgentIndex: 1,
    nextDebugAgentIndex: 1,
  };
}

export function loadWorkbenchStorage(): WorkbenchStorage {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return defaultStorage();
  }
  try {
    const parsed = JSON.parse(raw) as Partial<WorkbenchStorage>;
    return {
      discovery: sanitizeDiscoveryConfig(parsed.discovery),
      layout: sanitizeDockviewLayout(parsed.layout),
      panes: sanitizePaneRecords(parsed.panes),
      nextAgentIndex: typeof parsed.nextAgentIndex === "number" ? parsed.nextAgentIndex : 1,
      nextDebugAgentIndex:
        typeof parsed.nextDebugAgentIndex === "number" ? parsed.nextDebugAgentIndex : 1,
    };
  } catch {
    return defaultStorage();
  }
}

export function saveWorkbenchStorage(storage: WorkbenchStorage): void {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      ...storage,
      layout: sanitizeDockviewLayout(storage.layout),
    }),
  );
}

export function sanitizeDockviewLayout(layout: unknown): SerializedDockview | undefined {
  if (!layout || typeof layout !== "object") {
    return undefined;
  }
  return dropFloatingState(layout) as SerializedDockview;
}

export function storageSnapshotForTests(): WorkbenchStorage {
  return loadWorkbenchStorage();
}

function sanitizePaneRecords(value: unknown): Record<string, PaneRecord> {
  const defaults = defaultStorage().panes;
  if (!value || typeof value !== "object") {
    return defaults;
  }
  const records: Record<string, PaneRecord> = { ...defaults };
  for (const [paneId, record] of Object.entries(value as Record<string, Partial<PaneRecord>>)) {
    const kind =
      record.kind === "agent"
        ? "agent"
        : record.kind === "operator"
          ? "operator"
          : record.kind === "debug-agent"
            ? "debug-agent"
            : undefined;
    if (!kind) {
      continue;
    }
    const target = sanitizeTarget(record.target, defaultTarget(paneId, kind));
    const resetToken = typeof record.resetToken === "number" ? record.resetToken : undefined;
    const debugAgent = kind === "debug-agent" ? sanitizeDebugAgent(record.debugAgent, paneId) : undefined;
    records[paneId] = { paneId, kind, target, resetToken, debugAgent };
  }
  return records;
}

function sanitizeDiscoveryConfig(value: unknown): DiscoveryConfig {
  if (!value || typeof value !== "object") {
    return defaultStorage().discovery;
  }
  const config = value as Partial<DiscoveryConfig>;
  return {
    passiveServerUrl:
      typeof config.passiveServerUrl === "string" && config.passiveServerUrl.trim()
        ? config.passiveServerUrl
        : DEFAULT_PASSIVE_SERVER_URL,
  };
}

function sanitizeTarget(value: unknown, fallback: TargetConfig): TargetConfig {
  if (!value || typeof value !== "object") {
    return fallback;
  }
  const target = value as Partial<TargetConfig>;
  return {
    label: typeof target.label === "string" ? target.label : fallback.label,
    url: typeof target.url === "string" ? target.url : fallback.url,
    threadId: typeof target.threadId === "string" ? target.threadId : fallback.threadId,
    source: sanitizeTargetSource(target.source),
  };
}

function sanitizeTargetSource(value: unknown): TargetConfig["source"] {
  if (!value || typeof value !== "object") {
    return { kind: "manual" };
  }
  const source = value as Partial<NonNullable<TargetConfig["source"]>>;
  if (source.kind === "discovered") {
    const agentId = stringField(source, "agentId");
    const agentName = stringField(source, "agentName");
    const passiveServerUrl = stringField(source, "passiveServerUrl");
    if (!agentId || !agentName || !passiveServerUrl) {
      return { kind: "manual" };
    }
    return {
      kind: "discovered",
      passiveServerUrl,
      agentId,
      agentName,
      agentRef: stringField(source, "agentRef") || agentId,
      generationId: stringField(source, "generationId") || undefined,
      tool: stringField(source, "tool") || undefined,
      backend: stringField(source, "backend") || undefined,
      addressStatus: safeAddressStatus(stringField(source, "addressStatus")),
    };
  }
  return { kind: "manual" };
}

function safeAddressStatus(value: string): AgentAddressResolveStatus | undefined {
  if (
    value === "unknown" ||
    value === "ambiguous" ||
    value === "offline" ||
    value === "live_without_gateway" ||
    value === "live_with_gateway"
  ) {
    return value;
  }
  return undefined;
}

function sanitizeDebugAgent(value: unknown, paneId: string): DebugAgentConfig {
  const fallback = defaultDebugAgentConfig(paneId);
  if (!value || typeof value !== "object") {
    return fallback;
  }
  const config = value as Partial<DebugAgentConfig>;
  const debugAgentId =
    typeof config.debugAgentId === "string" && safeDebugAgentId(config.debugAgentId)
      ? config.debugAgentId
      : fallback.debugAgentId;
  return {
    debugAgentId,
    replayEnabled:
      typeof config.replayEnabled === "boolean" ? config.replayEnabled : fallback.replayEnabled,
  };
}

function safeDebugAgentId(value: string): boolean {
  return /^debug-agent-[a-z0-9_.-]+$/.test(value);
}

export function debugAgentUrl(debugAgentId: string): string {
  return `${debugAgentRelayBaseUrl(debugAgentId)}/v1/ag-ui`;
}

export function debugAgentRelayBaseUrl(debugAgentId: string): string {
  const origin =
    typeof window === "undefined" ? "http://127.0.0.1:5177" : window.location.origin;
  return `${origin}/__houmao_debug_agents/${encodeURIComponent(debugAgentId)}`;
}

function stringField(value: object, key: string): string {
  const record = value as Record<string, unknown>;
  return typeof record[key] === "string" ? record[key] : "";
}

function dropFloatingState(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(dropFloatingState);
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  const sanitized: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    if (key === "floatingGroups" || key === "popoutGroups") {
      continue;
    }
    sanitized[key] = dropFloatingState(entry);
  }
  return sanitized;
}

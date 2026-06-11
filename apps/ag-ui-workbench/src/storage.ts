import type { SerializedDockview } from "dockview-react";

import type { AgentAddressResolveStatus, TargetConfig } from "./ag-ui/types";
import type { WatchedTargetRecord } from "./ag-ui/watchedTargets";
import { watchedTargetKey } from "./ag-ui/watchedTargets";

export type PaneKind = "agent" | "debug-agent" | "tmux";
export type TemplateGraphicBackendOverride = "auto" | "vega-lite" | "recharts";

export interface DebugAgentConfig {
  debugAgentId: string;
  replayEnabled: boolean;
}

export interface TmuxTabConfig {
  sessionName?: string;
  mode: "read-write" | "read-only";
  houmaoOnly: boolean;
}

export interface PanePresentationConfig {
  templateGraphicBackend: TemplateGraphicBackendOverride;
}

export interface PaneRecord {
  paneId: string;
  kind: PaneKind;
  target: TargetConfig;
  resetToken?: number;
  debugAgent?: DebugAgentConfig;
  presentation?: PanePresentationConfig;
  tmux?: TmuxTabConfig;
}

export interface DiscoveryConfig {
  passiveServerUrl: string;
}

export interface WorkbenchStorage {
  discovery: DiscoveryConfig;
  layout?: unknown;
  panes: Record<string, PaneRecord>;
  watchedTargets: Record<string, WatchedTargetRecord>;
  operatorPaneId?: string;
  nextAgentIndex: number;
  nextDebugAgentIndex: number;
  nextTmuxIndex: number;
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
    label: paneId.replace(/-/g, " "),
    url: "",
    threadId: `${paneId}-thread`,
    source: { kind: "manual" },
  };
}

export function defaultDebugAgentConfig(paneId: string): DebugAgentConfig {
  return {
    debugAgentId: paneId.startsWith("debug-agent-") ? paneId : "debug-agent-1",
    replayEnabled: true,
  };
}

export function defaultTmuxTabConfig(): TmuxTabConfig {
  return {
    mode: "read-write",
    houmaoOnly: true,
  };
}

export function defaultPanePresentationConfig(): PanePresentationConfig {
  return { templateGraphicBackend: "auto" };
}

export function defaultStorage(): WorkbenchStorage {
  return {
    discovery: {
      passiveServerUrl: DEFAULT_PASSIVE_SERVER_URL,
    },
    panes: {},
    watchedTargets: {},
    nextAgentIndex: 1,
    nextDebugAgentIndex: 1,
    nextTmuxIndex: 1,
  };
}

export function loadWorkbenchStorage(): WorkbenchStorage {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return defaultStorage();
  }
  try {
    const parsed = JSON.parse(raw) as Partial<WorkbenchStorage>;
    const panes = sanitizePaneRecords(parsed.panes);
    return {
      discovery: sanitizeDiscoveryConfig(parsed.discovery),
      layout: sanitizeDockviewLayout(parsed.layout),
      panes,
      watchedTargets: sanitizeWatchedTargetRecords(parsed.watchedTargets),
      operatorPaneId: validOperatorPaneId(
        typeof parsed.operatorPaneId === "string" ? parsed.operatorPaneId : undefined,
        panes,
      ),
      nextAgentIndex: typeof parsed.nextAgentIndex === "number" ? parsed.nextAgentIndex : 1,
      nextDebugAgentIndex:
        typeof parsed.nextDebugAgentIndex === "number" ? parsed.nextDebugAgentIndex : 1,
      nextTmuxIndex: typeof parsed.nextTmuxIndex === "number" ? parsed.nextTmuxIndex : 1,
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
      panes: sanitizePaneRecords(storage.panes),
      watchedTargets: sanitizeWatchedTargetRecords(storage.watchedTargets),
      operatorPaneId: validOperatorPaneId(storage.operatorPaneId, storage.panes),
    }),
  );
}

export function sanitizeDockviewLayout(layout: unknown): SerializedDockview | undefined {
  if (!layout || typeof layout !== "object") {
    return undefined;
  }
  const sanitized = dropFloatingState(layout);
  return sanitized && typeof sanitized === "object" ? (sanitized as SerializedDockview) : undefined;
}

export function storageSnapshotForTests(): WorkbenchStorage {
  return loadWorkbenchStorage();
}

function sanitizePaneRecords(value: unknown): Record<string, PaneRecord> {
  if (!value || typeof value !== "object") {
    return {};
  }
  const records: Record<string, PaneRecord> = {};
  for (const [paneId, record] of Object.entries(value as Record<string, Partial<PaneRecord>>)) {
    const kind =
      record.kind === "agent"
        ? "agent"
        : record.kind === "debug-agent"
            ? "debug-agent"
            : record.kind === "tmux"
              ? "tmux"
              : undefined;
    if (!kind) {
      continue;
    }
    const target = sanitizeTarget(record.target, defaultTarget(paneId, kind));
    const resetToken = typeof record.resetToken === "number" ? record.resetToken : undefined;
    const debugAgent = kind === "debug-agent" ? sanitizeDebugAgent(record.debugAgent, paneId) : undefined;
    const presentation = sanitizePanePresentationConfig(record.presentation);
    const tmux = kind === "tmux" ? sanitizeTmuxTabConfig(record.tmux) : undefined;
    records[paneId] = { paneId, kind, target, resetToken, debugAgent, presentation, tmux };
  }
  return records;
}

function sanitizeWatchedTargetRecords(value: unknown): Record<string, WatchedTargetRecord> {
  if (!value || typeof value !== "object") {
    return {};
  }
  const records: Record<string, WatchedTargetRecord> = {};
  for (const [storedKey, record] of Object.entries(
    value as Record<string, Partial<WatchedTargetRecord>>,
  )) {
    const fallbackTarget = defaultTarget("watched-target", "agent");
    const target = sanitizeTarget(record.target, fallbackTarget);
    if (!target.threadId) {
      continue;
    }
    const key = watchedTargetKey(target);
    if (storedKey !== key && !key) {
      continue;
    }
    records[key] = {
      key,
      target,
      createdAt: typeof record.createdAt === "string" ? record.createdAt : new Date().toISOString(),
      updatedAt: typeof record.updatedAt === "string" ? record.updatedAt : new Date().toISOString(),
    };
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

function sanitizePanePresentationConfig(value: unknown): PanePresentationConfig {
  if (!value || typeof value !== "object") {
    return defaultPanePresentationConfig();
  }
  const config = value as Partial<PanePresentationConfig>;
  return {
    templateGraphicBackend: sanitizeTemplateGraphicBackendOverride(config.templateGraphicBackend),
  };
}

function sanitizeTemplateGraphicBackendOverride(value: unknown): TemplateGraphicBackendOverride {
  if (value === "vega-lite" || value === "recharts") {
    return value;
  }
  return "auto";
}

function sanitizeTmuxTabConfig(value: unknown): TmuxTabConfig {
  const fallback = defaultTmuxTabConfig();
  if (!value || typeof value !== "object") {
    return fallback;
  }
  const config = value as Partial<TmuxTabConfig>;
  const sessionName =
    typeof config.sessionName === "string" && config.sessionName.trim()
      ? config.sessionName.trim()
      : undefined;
  return {
    sessionName,
    mode: config.mode === "read-only" ? "read-only" : "read-write",
    houmaoOnly: typeof config.houmaoOnly === "boolean" ? config.houmaoOnly : fallback.houmaoOnly,
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
    return value.map(dropFloatingState).filter((entry) => entry !== null);
  }
  if (!value || typeof value !== "object") {
    return value;
  }
  if (isLegacyOperatorPanel(value)) {
    return null;
  }
  const sanitized: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    if (key === "floatingGroups" || key === "popoutGroups") {
      continue;
    }
    const next = dropFloatingState(entry);
    if (next !== null) {
      sanitized[key] = next;
    }
  }
  return sanitized;
}

function isLegacyOperatorPanel(value: object): boolean {
  const record = value as Record<string, unknown>;
  if (record.id === "operator") {
    return true;
  }
  if (record.component === "operator") {
    return true;
  }
  const params = record.params;
  if (!params || typeof params !== "object") {
    return false;
  }
  return (params as Record<string, unknown>).kind === "operator";
}

function validOperatorPaneId(
  paneId: string | undefined,
  panes: Record<string, PaneRecord>,
): string | undefined {
  if (!paneId) {
    return undefined;
  }
  const pane = panes[paneId];
  if (pane?.kind !== "agent" || pane.target.source?.kind !== "discovered") {
    return undefined;
  }
  return paneId;
}

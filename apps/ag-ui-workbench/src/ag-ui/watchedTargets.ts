import type { TargetConfig } from "./types";

export interface WatchedTargetRecord {
  key: string;
  target: TargetConfig;
  createdAt: string;
  updatedAt: string;
}

export type WatcherStatus =
  | "empty"
  | "connecting"
  | "waiting"
  | "offline"
  | "reconnecting"
  | "connected"
  | "running"
  | "finished"
  | "error"
  | "disconnected";

export function watchedTargetKey(target: TargetConfig): string {
  const threadId = safeKeyPart(target.threadId || "default-thread");
  if (target.source?.kind === "discovered") {
    const address = target.source.agentId || target.source.agentName || target.source.agentRef || target.label;
    return `discovered:${safeKeyPart(address)}:${threadId}`;
  }
  return `manual:${safeKeyPart(normalizedManualUrl(target.url))}:${threadId}`;
}

export function watchedTargetLabel(record: WatchedTargetRecord): string {
  if (record.target.label) {
    return record.target.label;
  }
  if (record.target.source?.kind === "discovered") {
    return record.target.source.agentName || record.target.source.agentId || record.key;
  }
  return record.key;
}

export function createWatchedTargetRecord(target: TargetConfig): WatchedTargetRecord {
  const now = new Date().toISOString();
  return {
    key: watchedTargetKey(target),
    target,
    createdAt: now,
    updatedAt: now,
  };
}

export function updateWatchedTargetRecord(
  current: WatchedTargetRecord,
  target: TargetConfig,
): WatchedTargetRecord {
  return {
    ...current,
    target,
    updatedAt: new Date().toISOString(),
  };
}

function normalizedManualUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  try {
    const url = new URL(trimmed);
    url.hash = "";
    return url.toString();
  } catch {
    return trimmed;
  }
}

function safeKeyPart(value: string): string {
  const sanitized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return sanitized || "unknown";
}

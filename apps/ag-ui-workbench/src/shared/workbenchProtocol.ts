import type { RunAgentInput } from "../ag-ui/types";

export const WORKBENCH_API_PREFIX = "/__houmao_workbench";

export type WorkbenchErrorCode =
  | "request_invalid"
  | "target_missing"
  | "target_invalid"
  | "target_policy_rejected"
  | "upstream_failed"
  | "session_missing";

export interface WorkbenchErrorPayload {
  code: WorkbenchErrorCode | string;
  detail: string;
  path?: string;
}

export interface AgUiTargetRequest {
  targetUrl: string;
}

export interface AgUiStreamRequest extends AgUiTargetRequest {
  input: RunAgentInput;
}

export interface AgUiDetachRequest extends AgUiTargetRequest {
  connectionId?: string | null;
}

export interface AgUiActiveThreadSetRequest extends AgUiTargetRequest {
  threadId: string;
  source: "gui_button" | "gui_connect" | "manual";
}

export interface AgUiActiveThreadClearRequest extends AgUiTargetRequest {
  expectedThreadId?: string;
}

export interface WorkbenchFetchJsonRequest {
  targetUrl: string;
  method?: "GET" | "DELETE";
}

export interface PresentationSessionCreateRequest {
  paneId?: string;
  kind?: string;
  metadata?: Record<string, unknown>;
}

export interface PresentationSessionView {
  sessionId: string;
  paneId: string | null;
  kind: string;
  metadata: Record<string, unknown>;
  createdAtUtc: string;
  updatedAtUtc: string;
  owner: "workbench-local-server";
}

export type TmuxClientMessage =
  | {
      type: "attach";
      sessionName: string;
      mode: "read-write" | "read-only";
      cols?: number;
      rows?: number;
    }
  | {
      type: "input";
      data: string;
    }
  | {
      type: "resize";
      cols: number;
      rows: number;
    }
  | {
      type: "scroll";
      direction: "up" | "down";
      lines: number;
    }
  | {
      type: "close";
    };

export type TmuxServerMessage =
  | {
      type: "attached";
      sessionName?: string;
      mode?: "read-write" | "read-only";
    }
  | {
      type: "output";
      data: string;
    }
  | {
      type: "exit";
      exitCode: number;
      signal: number;
    }
  | {
      type: "error";
      code: string;
      detail: string;
    };

export type ValidationResult<T> =
  | {
      ok: true;
      value: T;
    }
  | {
      ok: false;
      error: WorkbenchErrorPayload;
    };

export function validateAgUiTargetRequest(value: unknown): ValidationResult<AgUiTargetRequest> {
  const record = objectRecord(value);
  if (!record.ok) {
    return record;
  }
  const targetUrl = stringField(record.value, "targetUrl");
  if (!targetUrl) {
    return invalid("target_missing", "targetUrl must be a non-empty string.", "targetUrl");
  }
  return { ok: true, value: { targetUrl } };
}

export function validateAgUiStreamRequest(value: unknown): ValidationResult<AgUiStreamRequest> {
  const target = validateAgUiTargetRequest(value);
  if (!target.ok) {
    return target;
  }
  const record = value as Record<string, unknown>;
  if (!isRecord(record.input)) {
    return invalid("request_invalid", "input must be an object.", "input");
  }
  return {
    ok: true,
    value: {
      targetUrl: target.value.targetUrl,
      input: record.input as RunAgentInput,
    },
  };
}

export function validateAgUiDetachRequest(value: unknown): ValidationResult<AgUiDetachRequest> {
  const target = validateAgUiTargetRequest(value);
  if (!target.ok) {
    return target;
  }
  const record = value as Record<string, unknown>;
  const connectionId =
    typeof record.connectionId === "string" && record.connectionId.trim()
      ? record.connectionId.trim()
      : null;
  return {
    ok: true,
    value: {
      targetUrl: target.value.targetUrl,
      connectionId,
    },
  };
}

export function validateActiveThreadSetRequest(
  value: unknown,
): ValidationResult<AgUiActiveThreadSetRequest> {
  const target = validateAgUiTargetRequest(value);
  if (!target.ok) {
    return target;
  }
  const record = value as Record<string, unknown>;
  const threadId = stringField(record, "threadId");
  if (!threadId) {
    return invalid("request_invalid", "threadId must be a non-empty string.", "threadId");
  }
  const source = record.source;
  if (source !== "gui_button" && source !== "gui_connect" && source !== "manual") {
    return invalid("request_invalid", "source is invalid.", "source");
  }
  return {
    ok: true,
    value: {
      targetUrl: target.value.targetUrl,
      threadId,
      source,
    },
  };
}

export function validateActiveThreadClearRequest(
  value: unknown,
): ValidationResult<AgUiActiveThreadClearRequest> {
  const target = validateAgUiTargetRequest(value);
  if (!target.ok) {
    return target;
  }
  const record = value as Record<string, unknown>;
  const expectedThreadId = stringField(record, "expectedThreadId");
  return {
    ok: true,
    value: {
      targetUrl: target.value.targetUrl,
      expectedThreadId: expectedThreadId || undefined,
    },
  };
}

export function validateFetchJsonRequest(value: unknown): ValidationResult<WorkbenchFetchJsonRequest> {
  const target = validateAgUiTargetRequest(value);
  if (!target.ok) {
    return target;
  }
  const record = value as Record<string, unknown>;
  const method = record.method === "DELETE" ? "DELETE" : "GET";
  return {
    ok: true,
    value: {
      targetUrl: target.value.targetUrl,
      method,
    },
  };
}

export function validatePresentationSessionCreateRequest(
  value: unknown,
): ValidationResult<PresentationSessionCreateRequest> {
  if (typeof value === "undefined" || value === null) {
    return { ok: true, value: {} };
  }
  const record = objectRecord(value);
  if (!record.ok) {
    return record;
  }
  const paneId = stringField(record.value, "paneId") || undefined;
  const kind = stringField(record.value, "kind") || undefined;
  const metadata = isRecord(record.value.metadata) ? safeMetadata(record.value.metadata) : undefined;
  return {
    ok: true,
    value: { paneId, kind, metadata },
  };
}

export function safeMetadata(value: Record<string, unknown>): Record<string, unknown> {
  const metadata: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value).slice(0, 64)) {
    if (!safeMetadataKey(key)) {
      continue;
    }
    if (typeof entry === "string") {
      metadata[key] = entry.slice(0, 512);
    } else if (typeof entry === "number" || typeof entry === "boolean" || entry === null) {
      metadata[key] = entry;
    }
  }
  return metadata;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function objectRecord(value: unknown): ValidationResult<Record<string, unknown>> {
  if (!isRecord(value)) {
    return invalid("request_invalid", "request body must be an object.");
  }
  return { ok: true, value };
}

function stringField(value: Record<string, unknown>, key: string): string {
  const entry = value[key];
  return typeof entry === "string" ? entry.trim() : "";
}

function safeMetadataKey(key: string): boolean {
  return /^[A-Za-z0-9_.:-]{1,80}$/.test(key);
}

function invalid(
  code: WorkbenchErrorCode,
  detail: string,
  path?: string,
): ValidationResult<never> {
  return {
    ok: false,
    error: { code, detail, path },
  };
}

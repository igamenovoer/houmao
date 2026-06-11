import type { CapabilitiesResponse, RunAgentInput, TargetConfig, RawTimelineEntry, AgUiEvent } from "./types";
import { detachUrl, normalizeAgUiTarget, proxiedTargetUrl } from "./target";
import { SseParser } from "./sse";

export interface CanvasSize {
  w: number;
  h: number;
}

export type ActiveThreadSource = "gui_button" | "gui_connect" | "manual";

export interface AgUiThreadDestination {
  status: "empty" | "active" | "sent";
  threadId?: string | null;
  updatedAtUtc?: string | null;
  source?: string | null;
}

export interface AgUiDestinationState {
  activeThread: AgUiThreadDestination;
  lastSentThread: AgUiThreadDestination;
}

export class AgUiHttpError extends Error {
  constructor(
    readonly status: number,
    readonly statusText: string,
    readonly body: string,
  ) {
    super(`AG-UI HTTP ${status}: ${statusText}${body ? ` ${body}` : ""}`);
  }
}

export interface StreamHandlers {
  onOpen?: () => void;
  onEvent: (event: AgUiEvent, raw: RawTimelineEntry) => void;
  onRaw: (raw: RawTimelineEntry) => void;
  onParseError: (raw: RawTimelineEntry) => void;
}

export async function fetchCapabilities(config: TargetConfig, signal?: AbortSignal): Promise<CapabilitiesResponse> {
  const target = normalizeAgUiTarget(config);
  const response = await fetch(proxiedTargetUrl(target.capabilitiesUrl), {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  return (await response.json()) as CapabilitiesResponse;
}

export async function runAgUi(
  config: TargetConfig,
  input: RunAgentInput,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const target = normalizeAgUiTarget(config);
  await streamAgUi(target.runsUrl, "POST", input, handlers, signal);
}

export async function connectAgUi(
  config: TargetConfig,
  input: RunAgentInput,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const target = normalizeAgUiTarget(config);
  await streamAgUi(target.connectUrl, "POST", input, handlers, signal);
}

export async function detachAgUi(config: TargetConfig, connectionId: string | null | undefined): Promise<void> {
  if (!connectionId) {
    return;
  }
  const target = normalizeAgUiTarget(config);
  const response = await fetch(proxiedTargetUrl(detachUrl(target, connectionId)), {
    method: "DELETE",
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok && response.status !== 404) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
}

export async function fetchAgUiDestination(config: TargetConfig, signal?: AbortSignal): Promise<AgUiDestinationState> {
  const target = normalizeAgUiTarget(config);
  const response = await fetch(proxiedTargetUrl(`${target.baseUrl}/destination`), {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  return (await response.json()) as AgUiDestinationState;
}

export async function fetchActiveAgUiThread(config: TargetConfig, signal?: AbortSignal): Promise<AgUiThreadDestination> {
  const target = normalizeAgUiTarget(config);
  const response = await fetch(proxiedTargetUrl(`${target.baseUrl}/active-thread`), {
    method: "GET",
    signal,
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  return (await response.json()) as AgUiThreadDestination;
}

export async function setActiveAgUiThread(
  config: TargetConfig,
  threadId: string,
  source: ActiveThreadSource = "manual",
): Promise<AgUiThreadDestination> {
  const target = normalizeAgUiTarget(config);
  const response = await fetch(proxiedTargetUrl(`${target.baseUrl}/active-thread`), {
    method: "PUT",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ threadId, source }),
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  return (await response.json()) as AgUiThreadDestination;
}

export async function clearActiveAgUiThread(
  config: TargetConfig,
  expectedThreadId?: string,
): Promise<AgUiThreadDestination | null> {
  const target = normalizeAgUiTarget(config);
  const endpoint = new URL(`${target.baseUrl}/active-thread`);
  if (expectedThreadId) {
    endpoint.searchParams.set("threadId", expectedThreadId);
  }
  const response = await fetch(proxiedTargetUrl(endpoint.toString()), {
    method: "DELETE",
    headers: {
      accept: "application/json",
    },
  });
  if (!response.ok && response.status !== 404) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  if (response.status === 404) {
    return null;
  }
  return (await response.json()) as AgUiThreadDestination;
}

async function streamAgUi(
  endpointUrl: string,
  method: "POST",
  body: unknown,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(proxiedTargetUrl(endpointUrl), {
    method,
    signal,
    headers: {
      accept: "text/event-stream",
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
  handlers.onOpen?.();
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  if (!response.body) {
    throw new Error("AG-UI stream response had no body.");
  }
  const decoder = new TextDecoder();
  const parser = new SseParser({
    onEvent: (event, raw) => {
      handlers.onRaw(raw);
      handlers.onEvent(event, raw);
    },
    onParseError: (raw) => {
      handlers.onRaw(raw);
      handlers.onParseError(raw);
    },
  });
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      parser.finish();
      return;
    }
    parser.feed(decoder.decode(value, { stream: true }));
  }
}

export function buildRunInput({
  paneId,
  threadId,
  message,
  canvasSize,
}: {
  paneId: string;
  threadId: string;
  message: string;
  canvasSize?: CanvasSize | null;
}): RunAgentInput {
  const runId = `run-${paneId}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  return {
    threadId,
    runId,
    state: {},
    messages: [
      {
        id: `msg-${runId}`,
        role: "user",
        content: message,
      },
    ],
    tools: [],
    context: canvasContext(canvasSize),
    forwardedProps: {},
  };
}

export function buildConnectInput({
  paneId,
  threadId,
}: {
  paneId: string;
  threadId: string;
}): RunAgentInput {
  const runId = `connect-${paneId}-${Date.now()}`;
  return {
    threadId,
    runId,
    state: {},
    messages: [],
    tools: [],
    context: [],
    forwardedProps: {},
  };
}

export function canvasContext(canvasSize: CanvasSize | null | undefined): RunAgentInput["context"] {
  if (!canvasSize) {
    return [];
  }
  const w = Math.round(canvasSize.w);
  const h = Math.round(canvasSize.h);
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    return [];
  }
  return [
    {
      description: "houmao.canvas_size_px.v1",
      value: JSON.stringify({ widthPx: w, heightPx: h }),
    },
  ];
}

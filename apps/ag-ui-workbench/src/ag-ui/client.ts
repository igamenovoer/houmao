import type { CapabilitiesResponse, RunAgentInput, TargetConfig, RawTimelineEntry, AgUiEvent } from "./types";
import { SseParser } from "./sse";
import { fetchWorkbench, hasOperatorSession } from "../operatorSession";
import { WORKBENCH_API_PREFIX, type AgUiTargetRequest } from "../shared/workbenchProtocol";

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

export function isAgUiAuthorizationRefusal(error: unknown): boolean {
  return error instanceof AgUiHttpError && (error.status === 401 || error.status === 403);
}

export interface StreamHandlers {
  onOpen?: () => void;
  onEvent: (event: AgUiEvent, raw: RawTimelineEntry) => void;
  onRaw: (raw: RawTimelineEntry) => void;
  onParseError: (raw: RawTimelineEntry) => void;
}

export async function fetchCapabilities(config: TargetConfig, signal?: AbortSignal): Promise<CapabilitiesResponse> {
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/capabilities`, {
    method: "POST",
    signal,
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(targetRequest(config)),
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
  await streamAgUi(workbenchStreamUrl("run"), config, input, handlers, signal);
}

export async function connectAgUi(
  config: TargetConfig,
  input: RunAgentInput,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await streamAgUi(workbenchStreamUrl("connect"), config, input, handlers, signal);
}

export async function detachAgUi(config: TargetConfig, connectionId: string | null | undefined): Promise<void> {
  if (!connectionId) {
    return;
  }
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/detach`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ ...targetRequest(config), connectionId }),
  });
  if (!response.ok && response.status !== 404) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
}

export async function fetchAgUiDestination(config: TargetConfig, signal?: AbortSignal): Promise<AgUiDestinationState> {
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/destination`, {
    method: "POST",
    signal,
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(targetRequest(config)),
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  return (await response.json()) as AgUiDestinationState;
}

export async function fetchActiveAgUiThread(config: TargetConfig, signal?: AbortSignal): Promise<AgUiThreadDestination> {
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, {
    method: "POST",
    signal,
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify(targetRequest(config)),
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
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, {
    method: "PUT",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ ...targetRequest(config), threadId, source }),
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
  const response = await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/active-thread`, {
    method: "DELETE",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ ...targetRequest(config), expectedThreadId }),
  });
  if (!response.ok && response.status !== 404) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  if (response.status === 404) {
    return null;
  }
  return (await response.json()) as AgUiThreadDestination;
}

export function closeAllWorkbenchAgUiStreams(): void {
  const url = `${WORKBENCH_API_PREFIX}/ag-ui/streams/close-all`;
  if (!hasOperatorSession() && navigator.sendBeacon) {
    const payload = new Blob(["{}"], { type: "application/json" });
    if (navigator.sendBeacon(url, payload)) {
      return;
    }
  }
  void fetchWorkbench(url, {
    method: "POST",
    keepalive: true,
    headers: {
      "content-type": "application/json",
    },
    body: "{}",
  }).catch(() => undefined);
}

export async function closeWorkbenchAgUiStreamsForTarget(config: TargetConfig): Promise<void> {
  await fetchWorkbench(`${WORKBENCH_API_PREFIX}/ag-ui/streams/close-target`, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({ targetUrl: config.url }),
  }).catch(() => undefined);
}

async function streamAgUi(
  endpointUrl: string,
  config: TargetConfig,
  input: RunAgentInput,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetchWorkbench(endpointUrl, {
    method: "POST",
    signal,
    headers: {
      accept: "text/event-stream",
      "content-type": "application/json",
    },
    body: JSON.stringify({ ...targetRequest(config), input }),
  });
  if (!response.ok) {
    throw new AgUiHttpError(response.status, response.statusText, await response.text());
  }
  handlers.onOpen?.();
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

function targetRequest(config: TargetConfig): AgUiTargetRequest {
  const request: AgUiTargetRequest = { targetUrl: config.url };
  if (config.useOperatorSigner) {
    const source = config.source;
    request.signer = source?.kind === "discovered"
      ? { kind: "discovered", agentId: source.agentId, passiveServerUrl: source.passiveServerUrl }
      : { kind: "manual" };
  }
  return request;
}

function workbenchStreamUrl(route: "connect" | "run"): string {
  return `${WORKBENCH_API_PREFIX}/ag-ui/${route}`;
}

export function buildRunInput({
  paneId,
  threadId,
  message,
}: {
  paneId: string;
  threadId: string;
  message: string;
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
    context: [],
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

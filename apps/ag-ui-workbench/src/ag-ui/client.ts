import type { CapabilitiesResponse, RunAgentInput, TargetConfig, RawTimelineEntry, AgUiEvent } from "./types";
import { detachUrl, normalizeAgUiTarget, proxiedTargetUrl } from "./target";
import { SseParser } from "./sse";

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
  input: RunAgentInput & { lastSeenEventId?: string },
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
  paneKind,
}: {
  paneId: string;
  threadId: string;
  message: string;
  paneKind: "operator" | "agent";
}): RunAgentInput {
  const runId = `run-${paneId}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  return {
    threadId,
    runId,
    state: {
      houmaoWorkbench: {
        paneId,
        paneKind,
      },
    },
    messages: [
      {
        id: `msg-${runId}`,
        role: "user",
        content: message,
      },
    ],
    tools: [],
    context: [],
    forwardedProps: {
      source: "houmao-ag-ui-workbench",
      paneId,
      paneKind,
    },
  };
}

export function buildConnectInput({
  paneId,
  threadId,
  paneKind,
}: {
  paneId: string;
  threadId: string;
  paneKind: "operator" | "agent";
}): RunAgentInput & { lastSeenEventId?: string } {
  const runId = `connect-${paneId}-${Date.now()}`;
  return {
    threadId,
    runId,
    state: {
      houmaoWorkbench: {
        paneId,
        paneKind,
      },
    },
    messages: [],
    tools: [],
    context: [],
    forwardedProps: {
      source: "houmao-ag-ui-workbench",
      paneId,
      paneKind,
      attachOnly: true,
    },
  };
}

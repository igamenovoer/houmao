import type { AgUiEvent, JsonObject, RawTimelineEntry } from "./types";

export type PaneRunStatus = "empty" | "connecting" | "connected" | "running" | "finished" | "error" | "disconnected";

export interface TranscriptMessage {
  id: string;
  role: string;
  content: string;
  done: boolean;
}

export interface ToolCallRecord {
  id: string;
  name: string;
  parentMessageId?: string;
  argsText: string;
  result?: string;
  complete: boolean;
}

export interface ActivityRecord {
  id: string;
  type: string;
  content: unknown;
}

export interface PaneEventState {
  status: PaneRunStatus;
  transcript: TranscriptMessage[];
  toolCalls: ToolCallRecord[];
  stateSnapshot: unknown;
  activity: ActivityRecord[];
  custom: ActivityRecord[];
  errors: string[];
  raw: RawTimelineEntry[];
}

export function initialPaneEventState(): PaneEventState {
  return {
    status: "empty",
    transcript: [],
    toolCalls: [],
    stateSnapshot: undefined,
    activity: [],
    custom: [],
    errors: [],
    raw: [],
  };
}

export function reduceAgUiEvent(
  state: PaneEventState,
  event: AgUiEvent,
  raw: RawTimelineEntry,
): PaneEventState {
  const next = { ...state, raw: appendRaw(state.raw, raw) };
  switch (event.type) {
    case "RUN_STARTED":
      return { ...next, status: "running" };
    case "RUN_FINISHED":
      return { ...next, status: "finished" };
    case "RUN_ERROR":
      return {
        ...next,
        status: "error",
        errors: [...state.errors, eventMessage(event, "AG-UI run error.")],
      };
    case "TEXT_MESSAGE_START":
      return startMessage(next, event);
    case "TEXT_MESSAGE_CONTENT":
      return appendMessageContent(next, event);
    case "TEXT_MESSAGE_CHUNK":
      return appendChunkMessage(next, event);
    case "TEXT_MESSAGE_END":
      return finishMessage(next, event);
    case "MESSAGES_SNAPSHOT":
      return snapshotMessages(next, event);
    case "STATE_SNAPSHOT":
      return { ...next, stateSnapshot: event.snapshot };
    case "ACTIVITY_SNAPSHOT":
    case "ACTIVITY_DELTA":
      return {
        ...next,
        activity: appendActivity(state.activity, event),
      };
    case "CUSTOM":
      return {
        ...next,
        custom: appendCustom(state.custom, event),
      };
    case "TOOL_CALL_START":
      return startToolCall(next, event);
    case "TOOL_CALL_ARGS":
    case "TOOL_CALL_CHUNK":
      return appendToolCallArgs(next, event);
    case "TOOL_CALL_RESULT":
      return resultToolCall(next, event);
    case "TOOL_CALL_END":
      return finishToolCall(next, event);
    default:
      return next;
  }
}

export function reduceParseError(state: PaneEventState, raw: RawTimelineEntry): PaneEventState {
  return {
    ...state,
    status: "error",
    raw: appendRaw(state.raw, raw),
    errors: [...state.errors, raw.parseError ?? "AG-UI SSE parse error."],
  };
}

export function reduceHttpError(state: PaneEventState, message: string): PaneEventState {
  return {
    ...state,
    status: "error",
    errors: [...state.errors, message],
  };
}

export function extractConnectionId(event: AgUiEvent): string | null {
  if (event.type !== "STATE_SNAPSHOT") {
    return null;
  }
  const snapshot = event.snapshot;
  if (!isRecord(snapshot)) {
    return null;
  }
  const houmao = snapshot.houmao;
  if (!isRecord(houmao)) {
    return null;
  }
  const connection = houmao.connection;
  if (!isRecord(connection) || typeof connection.connectionId !== "string") {
    return null;
  }
  return connection.connectionId;
}

function appendRaw(raw: RawTimelineEntry[], entry: RawTimelineEntry): RawTimelineEntry[] {
  return [...raw, entry].slice(-200);
}

function startMessage(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.messageId, `message-${state.transcript.length + 1}`);
  const role = stringValue(event.role, "assistant");
  if (state.transcript.some((message) => message.id === id)) {
    return state;
  }
  return {
    ...state,
    transcript: [...state.transcript, { id, role, content: "", done: false }],
  };
}

function appendMessageContent(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.messageId, "message");
  const delta = stringValue(event.delta, "");
  return {
    ...state,
    transcript: state.transcript.map((message) =>
      message.id === id ? { ...message, content: `${message.content}${delta}` } : message,
    ),
  };
}

function appendChunkMessage(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.messageId, `chunk-${state.transcript.length + 1}`);
  const role = stringValue(event.role, "assistant");
  const delta = stringValue(event.delta, "");
  const existing = state.transcript.find((message) => message.id === id);
  if (!existing) {
    return {
      ...state,
      transcript: [...state.transcript, { id, role, content: delta, done: false }],
    };
  }
  return appendMessageContent(state, { ...event, messageId: id, delta });
}

function finishMessage(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.messageId, "message");
  return {
    ...state,
    transcript: state.transcript.map((message) =>
      message.id === id ? { ...message, done: true } : message,
    ),
  };
}

function snapshotMessages(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const messages = Array.isArray(event.messages) ? event.messages : [];
  return {
    ...state,
    transcript: messages.flatMap((message, index) => {
      if (!isRecord(message)) {
        return [];
      }
      return [
        {
          id: stringValue(message.id, `snapshot-${index}`),
          role: stringValue(message.role, "assistant"),
          content: typeof message.content === "string" ? message.content : JSON.stringify(message.content ?? ""),
          done: true,
        },
      ];
    }),
  };
}

function appendActivity(records: ActivityRecord[], event: AgUiEvent): ActivityRecord[] {
  return [
    ...records,
    {
      id: stringValue(event.messageId, `activity-${records.length + 1}`),
      type: stringValue(event.activityType, event.type),
      content: event.content ?? event.patch ?? event,
    },
  ].slice(-50);
}

function appendCustom(records: ActivityRecord[], event: AgUiEvent): ActivityRecord[] {
  return [
    ...records,
    {
      id: stringValue(event.name, `custom-${records.length + 1}`),
      type: stringValue(event.name, "custom"),
      content: event.value ?? event,
    },
  ].slice(-50);
}

function startToolCall(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.toolCallId, `tool-${state.toolCalls.length + 1}`);
  return {
    ...state,
    toolCalls: [
      ...state.toolCalls.filter((toolCall) => toolCall.id !== id),
      {
        id,
        name: stringValue(event.toolCallName, "unknown_tool"),
        parentMessageId: typeof event.parentMessageId === "string" ? event.parentMessageId : undefined,
        argsText: "",
        complete: false,
      },
    ],
  };
}

function appendToolCallArgs(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.toolCallId, "tool");
  const delta = stringValue(event.delta, "");
  return {
    ...state,
    toolCalls: state.toolCalls.map((toolCall) =>
      toolCall.id === id ? { ...toolCall, argsText: `${toolCall.argsText}${delta}` } : toolCall,
    ),
  };
}

function resultToolCall(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.toolCallId, "tool");
  const content = stringValue(event.content, "");
  return {
    ...state,
    toolCalls: state.toolCalls.map((toolCall) =>
      toolCall.id === id ? { ...toolCall, result: content } : toolCall,
    ),
  };
}

function finishToolCall(state: PaneEventState, event: AgUiEvent): PaneEventState {
  const id = stringValue(event.toolCallId, "tool");
  return {
    ...state,
    toolCalls: state.toolCalls.map((toolCall) => (toolCall.id === id ? { ...toolCall, complete: true } : toolCall)),
  };
}

function eventMessage(event: AgUiEvent, fallback: string): string {
  if (typeof event.message === "string") {
    return event.code ? `${event.code}: ${event.message}` : event.message;
  }
  return fallback;
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" && value ? value : fallback;
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

const DEBUG_PREFIX = "/__houmao_debug_agents";
const MAX_BODY_BYTES = 256 * 1024;
const MAX_EVENTS = 100;
const MAX_CONNECTIONS_PER_AGENT = 32;
const MAX_REPLAY_BATCHES_PER_THREAD = 20;
const HEARTBEAT_MS = 15_000;

type JsonObject = Record<string, unknown>;
type ValidationResult<T> = { ok: true; value: T } | { ok: false; error: string; path?: string };
type ReplayMode = "debug_thread_buffer" | "none";

interface AgUiEvent {
  type: string;
  [key: string]: unknown;
}

interface DebugAgentState {
  agentId: string;
  nextConnectionIndex: number;
  nextToolCallIndex: number;
  subscriptions: Map<string, DebugSubscription>;
  replayBuffers: Map<string, ReplayBatch[]>;
}

interface DebugSubscription {
  connectionId: string;
  threadId: string;
  runId?: string;
  response: ServerResponse;
  heartbeat: ReturnType<typeof setInterval>;
  createdAt: string;
}

interface ReplayBatch {
  threadId: string;
  runId?: string;
  events: AgUiEvent[];
  createdAt: string;
}

interface PublishTarget {
  threadId: string;
  runId?: string;
  connectionId?: string;
}

interface PublishResult {
  deliveredCount: number;
  storedCount: number;
  replay: ReplayMode;
}

interface EventsRequest {
  threadId?: unknown;
  runId?: unknown;
  connectionId?: unknown;
  replay?: unknown;
  validateOnly?: unknown;
  events?: unknown;
}

interface ComponentRequest {
  threadId?: unknown;
  runId?: unknown;
  connectionId?: unknown;
  replay?: unknown;
  validateOnly?: unknown;
  payload?: unknown;
}

const COMPONENT_NAMES = [
  "houmao.chart.bar",
  "houmao.chart.line",
  "houmao.chart.pie",
  "houmao.table",
  "houmao.metric_grid",
  "houmao.dashboard",
] as const;

type ComponentName = (typeof COMPONENT_NAMES)[number];

const COMPONENT_NAME_SET = new Set<string>(COMPONENT_NAMES);

const COMPONENT_TEMPLATES: Record<ComponentName, unknown> = {
  "houmao.chart.bar": {
    schemaVersion: 1,
    title: "Debug Bar Chart",
    subtitle: "Posted through the Debug Agent relay",
    xLabel: "Bucket",
    yLabel: "Count",
    data: [
      { label: "Alpha", value: 18, color: "#79a35d" },
      { label: "Beta", value: 31, color: "#d3a749" },
      { label: "Gamma", value: 24, color: "#6aa6b8" },
    ],
  },
  "houmao.chart.line": {
    schemaVersion: 1,
    title: "Debug Line Chart",
    xLabel: "Step",
    yLabel: "Value",
    series: [
      {
        name: "Score",
        data: [
          { label: "T1", value: 4 },
          { label: "T2", value: 7 },
          { label: "T3", value: 5 },
        ],
      },
    ],
  },
  "houmao.chart.pie": {
    schemaVersion: 1,
    title: "Debug Pie Chart",
    data: [
      { label: "Open", value: 12 },
      { label: "Closed", value: 28 },
      { label: "Blocked", value: 3 },
    ],
  },
  "houmao.table": {
    schemaVersion: 1,
    title: "Debug Table",
    columns: [
      { key: "name", label: "Name", kind: "text" },
      { key: "count", label: "Count", kind: "number", align: "right" },
    ],
    rows: [
      { name: "Alpha", count: 18 },
      { name: "Beta", count: 31 },
    ],
  },
  "houmao.metric_grid": {
    schemaVersion: 1,
    title: "Debug Metrics",
    metrics: [
      { label: "Delivered", value: 1, trend: "up", delta: "+1" },
      { label: "Replay", value: "on", trend: "neutral" },
    ],
  },
  "houmao.dashboard": {
    schemaVersion: 1,
    title: "Debug Dashboard",
    children: [
      {
        component: "houmao.metric_grid",
        width: "full",
        props: {
          schemaVersion: 1,
          title: "Dashboard Metrics",
          metrics: [
            { label: "Accepted", value: 3 },
            { label: "Delivered", value: 1 },
          ],
        },
      },
      {
        component: "houmao.chart.bar",
        width: "half",
        props: {
          schemaVersion: 1,
          title: "Dashboard Chart",
          data: [
            { label: "A", value: 8 },
            { label: "B", value: 13 },
          ],
        },
      },
      {
        component: "houmao.table",
        width: "half",
        props: {
          schemaVersion: 1,
          title: "Dashboard Table",
          columns: [
            { key: "name", label: "Name", kind: "text" },
            { key: "state", label: "State", kind: "text" },
          ],
          rows: [
            { name: "Relay", state: "ready" },
            { name: "Display", state: "connected" },
          ],
        },
      },
    ],
  },
};

const states = new Map<string, DebugAgentState>();

export function houmaoAgUiDebugAgentPlugin(): Plugin {
  return {
    name: "houmao-ag-ui-debug-agent",
    configureServer(server) {
      server.middlewares.use(DEBUG_PREFIX, (req, res) => {
        void handleDebugRequest(req, res);
      });
    },
  };
}

async function handleDebugRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");

  if (req.method === "GET" && requestUrl.pathname === "/status") {
    sendJson(res, 200, debugStatus());
    return;
  }

  const route = parseRoute(requestUrl.pathname);
  if (!route.ok) {
    sendJson(res, route.status, {
      code: route.code,
      detail: route.detail,
    });
    return;
  }

  const state = stateFor(route.agentId);
  if (route.kind === "ag-ui") {
    await handleAgUiRoute(req, res, state, route.route, route.connectionId);
    return;
  }
  await handleComponentRoute(req, res, state, route.componentName);
}

async function handleAgUiRoute(
  req: IncomingMessage,
  res: ServerResponse,
  state: DebugAgentState,
  route: string,
  connectionId?: string,
): Promise<void> {
  if (req.method === "GET" && route === "capabilities") {
    sendJson(res, 200, capabilities(state.agentId));
    return;
  }

  if (req.method === "POST" && (route === "connect" || route === "runs")) {
    const body = await readJson(req);
    if (!body.ok) {
      sendJson(res, body.status, {
        code: body.code,
        detail: body.detail,
      });
      return;
    }
    openStream(res, state, body.value, route);
    return;
  }

  if (req.method === "POST" && route === "events") {
    const body = await readJson(req);
    if (!body.ok) {
      sendJson(res, body.status, {
        code: body.code,
        detail: body.detail,
      });
      return;
    }
    handleEventsPublish(res, state, body.value, body.bytes);
    return;
  }

  if (req.method === "DELETE" && route === "connections" && connectionId) {
    detachConnection(state, connectionId);
    sendJson(res, 200, {
      status: "detached",
      detached: true,
      agentId: state.agentId,
      connectionId,
      lifecycle: "debug-relay-only",
    });
    return;
  }

  sendJson(res, 404, { code: "not_found", detail: "Debug Agent route not found." });
}

async function handleComponentRoute(
  req: IncomingMessage,
  res: ServerResponse,
  state: DebugAgentState,
  componentName: string,
): Promise<void> {
  if (req.method !== "POST") {
    sendJson(res, 404, { code: "not_found", detail: "Debug Agent component route not found." });
    return;
  }
  if (!COMPONENT_NAME_SET.has(componentName)) {
    sendJson(res, 400, {
      code: "component_unknown",
      detail: `Unknown Houmao component: ${componentName}.`,
      componentName,
    });
    return;
  }
  const body = await readJson(req);
  if (!body.ok) {
    sendJson(res, body.status, {
      code: body.code,
      detail: body.detail,
    });
    return;
  }
  const request = body.value as ComponentRequest;
  const payloadValidation = validateComponentPayload(componentName, request.payload);
  if (!payloadValidation.ok) {
    sendJson(res, 400, {
      code: "component_validation_failed",
      detail: payloadValidation.error,
      path: payloadValidation.path,
      componentName,
    });
    return;
  }

  const target = publishTarget(state.agentId, request);
  const events = componentEvents(state, componentName, target, request.payload);
  if (request.validateOnly === true) {
    sendJson(res, 200, {
      status: "validated",
      componentName,
      acceptedCount: events.length,
      deliveredCount: 0,
      storedCount: 0,
      replay: "none",
      threadId: target.threadId,
      runId: target.runId ?? null,
      connectionId: target.connectionId ?? null,
      events,
    });
    return;
  }

  const result = publish(state, target, events, request.replay !== false);
  sendJson(res, 200, {
    status: "accepted",
    componentName,
    acceptedCount: events.length,
    deliveredCount: result.deliveredCount,
    storedCount: result.storedCount,
    replay: result.replay,
    threadId: target.threadId,
    runId: target.runId ?? null,
    connectionId: target.connectionId ?? null,
    events,
  });
}

function handleEventsPublish(
  res: ServerResponse,
  state: DebugAgentState,
  value: unknown,
  bytes: number,
): void {
  const request = value as EventsRequest;
  const eventsValidation = validateEvents(request.events);
  if (!eventsValidation.ok) {
    sendJson(res, 400, {
      code: "ag_ui_event_validation_failed",
      detail: eventsValidation.error,
      path: eventsValidation.path,
    });
    return;
  }
  const target = publishTarget(state.agentId, request);
  if (request.validateOnly === true) {
    sendJson(res, 200, {
      status: "validated",
      acceptedCount: eventsValidation.value.length,
      deliveredCount: 0,
      storedCount: 0,
      replay: "none",
      threadId: target.threadId,
      runId: target.runId ?? null,
      connectionId: target.connectionId ?? null,
      payloadBytes: bytes,
    });
    return;
  }
  const result = publish(state, target, eventsValidation.value, request.replay !== false);
  sendJson(res, 200, {
    status: "accepted",
    acceptedCount: eventsValidation.value.length,
    deliveredCount: result.deliveredCount,
    storedCount: result.storedCount,
    replay: result.replay,
    threadId: target.threadId,
    runId: target.runId ?? null,
    connectionId: target.connectionId ?? null,
    payloadBytes: bytes,
  });
}

function openStream(
  res: ServerResponse,
  state: DebugAgentState,
  input: unknown,
  route: "connect" | "runs",
): void {
  if (state.subscriptions.size >= MAX_CONNECTIONS_PER_AGENT) {
    sendJson(res, 429, {
      code: "connection_limit_reached",
      detail: `Debug Agent ${state.agentId} already has ${MAX_CONNECTIONS_PER_AGENT} open display streams.`,
    });
    return;
  }
  const record = isRecord(input) ? input : {};
  const threadId = stringField(record, "threadId", `${state.agentId}-thread`);
  const runId = stringField(
    record,
    "runId",
    `${route}-${state.agentId}-${Date.now()}-${state.nextConnectionIndex + 1}`,
  );
  const connectionId = `${state.agentId}-connection-${state.nextConnectionIndex + 1}`;
  state.nextConnectionIndex += 1;

  res.writeHead(200, {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
    "x-houmao-debug-agent": state.agentId,
  });

  const heartbeat = setInterval(() => {
    if (!res.writableEnded) {
      res.write(": heartbeat\n\n");
    }
  }, HEARTBEAT_MS);

  const subscription: DebugSubscription = {
    connectionId,
    threadId,
    runId,
    response: res,
    heartbeat,
    createdAt: new Date().toISOString(),
  };
  state.subscriptions.set(connectionId, subscription);
  res.on("close", () => cleanupSubscription(state, connectionId));

  writeSse(res, {
    type: "STATE_SNAPSHOT",
    snapshot: {
      houmao: {
        connection: {
          connectionId,
          threadId,
          runId,
          route,
          detached: false,
        },
        debugAgent: {
          agentId: state.agentId,
          relay: "houmao-ag-ui-workbench",
          managedAgent: false,
        },
      },
    },
  });

  if (route === "runs") {
    writeSse(res, { type: "RUN_STARTED", threadId, runId });
  }

  const replayEnabled = replayEnabledFromConnect(record);
  if (replayEnabled) {
    for (const batch of state.replayBuffers.get(threadId) ?? []) {
      for (const event of batch.events) {
        writeSse(res, event);
      }
    }
  }
}

function publish(
  state: DebugAgentState,
  target: PublishTarget,
  events: AgUiEvent[],
  storeReplay: boolean,
): PublishResult {
  const matches = matchingSubscriptions(state, target);
  for (const subscription of matches) {
    for (const event of events) {
      writeSse(subscription.response, event);
    }
  }
  if (!storeReplay) {
    return {
      deliveredCount: matches.length,
      storedCount: 0,
      replay: "none",
    };
  }
  const batches = state.replayBuffers.get(target.threadId) ?? [];
  batches.push({
    threadId: target.threadId,
    runId: target.runId,
    events,
    createdAt: new Date().toISOString(),
  });
  state.replayBuffers.set(target.threadId, batches.slice(-MAX_REPLAY_BATCHES_PER_THREAD));
  return {
    deliveredCount: matches.length,
    storedCount: events.length,
    replay: "debug_thread_buffer",
  };
}

function matchingSubscriptions(
  state: DebugAgentState,
  target: PublishTarget,
): DebugSubscription[] {
  const matches: DebugSubscription[] = [];
  for (const subscription of state.subscriptions.values()) {
    if (subscription.response.writableEnded) {
      cleanupSubscription(state, subscription.connectionId);
      continue;
    }
    if (target.connectionId && subscription.connectionId !== target.connectionId) {
      continue;
    }
    if (subscription.threadId !== target.threadId) {
      continue;
    }
    if (target.runId && subscription.runId !== target.runId) {
      continue;
    }
    matches.push(subscription);
  }
  return matches;
}

function detachConnection(state: DebugAgentState, connectionId: string): void {
  const subscription = state.subscriptions.get(connectionId);
  if (!subscription) {
    return;
  }
  cleanupSubscription(state, connectionId);
  if (!subscription.response.writableEnded) {
    subscription.response.end();
  }
}

function cleanupSubscription(state: DebugAgentState, connectionId: string): void {
  const subscription = state.subscriptions.get(connectionId);
  if (!subscription) {
    return;
  }
  clearInterval(subscription.heartbeat);
  state.subscriptions.delete(connectionId);
}

function componentEvents(
  state: DebugAgentState,
  componentName: string,
  target: PublishTarget,
  payload: unknown,
): AgUiEvent[] {
  const sequence = state.nextToolCallIndex + 1;
  state.nextToolCallIndex = sequence;
  const toolCallId = `${state.agentId}-tool-${sequence}`;
  const parentMessageId = `${state.agentId}-message-${sequence}`;
  return [
    {
      type: "TOOL_CALL_START",
      threadId: target.threadId,
      runId: target.runId,
      toolCallId,
      toolCallName: componentName,
      parentMessageId,
    },
    {
      type: "TOOL_CALL_ARGS",
      threadId: target.threadId,
      runId: target.runId,
      toolCallId,
      delta: JSON.stringify(payload),
    },
    {
      type: "TOOL_CALL_END",
      threadId: target.threadId,
      runId: target.runId,
      toolCallId,
    },
  ];
}

function validateEvents(value: unknown): ValidationResult<AgUiEvent[]> {
  if (!Array.isArray(value) || value.length === 0) {
    return invalid("events must be a non-empty array.", "events");
  }
  if (value.length > MAX_EVENTS) {
    return invalid(`events must contain at most ${MAX_EVENTS} items.`, "events");
  }
  const events: AgUiEvent[] = [];
  const toolStates = new Map<string, "started" | "ended">();
  for (const [index, item] of value.entries()) {
    if (!isRecord(item)) {
      return invalid(`events.${index} must be an object.`, `events.${index}`);
    }
    if (typeof item.type !== "string" || item.type.trim() === "") {
      return invalid(`events.${index}.type must be a non-empty string.`, `events.${index}.type`);
    }
    const event = item as AgUiEvent;
    const sequence = validateToolEventSequence(event, index, toolStates);
    if (!sequence.ok) {
      return sequence;
    }
    events.push(event);
  }
  for (const [toolCallId, state] of toolStates.entries()) {
    if (state !== "ended") {
      return invalid(`tool call ${toolCallId} is missing TOOL_CALL_END.`, "events");
    }
  }
  return { ok: true, value: events };
}

function validateToolEventSequence(
  event: AgUiEvent,
  index: number,
  toolStates: Map<string, "started" | "ended">,
): ValidationResult<void> {
  if (!event.type.startsWith("TOOL_CALL_")) {
    return { ok: true, value: undefined };
  }
  const toolCallId = stringValue(event.toolCallId);
  if (!toolCallId) {
    return invalid(`events.${index}.toolCallId must be a non-empty string.`, `events.${index}.toolCallId`);
  }
  if (event.type === "TOOL_CALL_START") {
    if (typeof event.toolCallName !== "string" || event.toolCallName.trim() === "") {
      return invalid(
        `events.${index}.toolCallName must be a non-empty string.`,
        `events.${index}.toolCallName`,
      );
    }
    if (toolStates.get(toolCallId) === "started") {
      return invalid(`tool call ${toolCallId} was started more than once.`, `events.${index}`);
    }
    toolStates.set(toolCallId, "started");
    return { ok: true, value: undefined };
  }
  const current = toolStates.get(toolCallId);
  if (!current) {
    return invalid(`tool call ${toolCallId} received ${event.type} before TOOL_CALL_START.`, `events.${index}`);
  }
  if (current === "ended") {
    return invalid(`tool call ${toolCallId} received ${event.type} after TOOL_CALL_END.`, `events.${index}`);
  }
  if ((event.type === "TOOL_CALL_ARGS" || event.type === "TOOL_CALL_CHUNK") && typeof event.delta !== "string") {
    return invalid(`events.${index}.delta must be a string.`, `events.${index}.delta`);
  }
  if (event.type === "TOOL_CALL_END") {
    toolStates.set(toolCallId, "ended");
  }
  return { ok: true, value: undefined };
}

function validateComponentPayload(componentName: string, payload: unknown, depth = 0): ValidationResult<unknown> {
  switch (componentName) {
    case "houmao.chart.bar":
    case "houmao.chart.pie":
      return validateChartPayload(payload);
    case "houmao.chart.line":
      return validateLinePayload(payload);
    case "houmao.table":
      return validateTablePayload(payload);
    case "houmao.metric_grid":
      return validateMetricGridPayload(payload);
    case "houmao.dashboard":
      return validateDashboardPayload(payload, depth);
    default:
      return invalid(`Unknown Houmao component: ${componentName}.`, "componentName");
  }
}

function validateChartPayload(payload: unknown): ValidationResult<unknown> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  const title = nonBlankString(record.value.title, "title");
  if (!title.ok) {
    return title;
  }
  if (!Array.isArray(record.value.data) || record.value.data.length === 0) {
    return invalid("data must be a non-empty array.", "data");
  }
  for (const [index, datum] of record.value.data.entries()) {
    const checked = validateDatum(datum, `data.${index}`);
    if (!checked.ok) {
      return checked;
    }
  }
  return { ok: true, value: payload };
}

function validateLinePayload(payload: unknown): ValidationResult<unknown> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  const title = nonBlankString(record.value.title, "title");
  if (!title.ok) {
    return title;
  }
  if (!Array.isArray(record.value.series) || record.value.series.length === 0) {
    return invalid("series must be a non-empty array.", "series");
  }
  for (const [seriesIndex, series] of record.value.series.entries()) {
    if (!isRecord(series)) {
      return invalid(`series.${seriesIndex} must be an object.`, `series.${seriesIndex}`);
    }
    const name = nonBlankString(series.name, `series.${seriesIndex}.name`);
    if (!name.ok) {
      return name;
    }
    if (!Array.isArray(series.data) || series.data.length === 0) {
      return invalid(
        `series.${seriesIndex}.data must be a non-empty array.`,
        `series.${seriesIndex}.data`,
      );
    }
    for (const [datumIndex, datum] of series.data.entries()) {
      const checked = validateDatum(datum, `series.${seriesIndex}.data.${datumIndex}`);
      if (!checked.ok) {
        return checked;
      }
    }
  }
  return { ok: true, value: payload };
}

function validateTablePayload(payload: unknown): ValidationResult<unknown> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  if (!Array.isArray(record.value.columns) || record.value.columns.length === 0) {
    return invalid("columns must be a non-empty array.", "columns");
  }
  const columnKeys: string[] = [];
  for (const [index, column] of record.value.columns.entries()) {
    if (!isRecord(column)) {
      return invalid(`columns.${index} must be an object.`, `columns.${index}`);
    }
    const key = nonBlankString(column.key, `columns.${index}.key`);
    if (!key.ok) {
      return key;
    }
    const label = nonBlankString(column.label, `columns.${index}.label`);
    if (!label.ok) {
      return label;
    }
    const kind = enumValue(column.kind ?? "text", ["text", "number", "boolean"], `columns.${index}.kind`);
    if (!kind.ok) {
      return kind;
    }
    columnKeys.push(key.value);
  }
  if (!Array.isArray(record.value.rows) || record.value.rows.length === 0) {
    return invalid("rows must be a non-empty array.", "rows");
  }
  for (const [rowIndex, row] of record.value.rows.entries()) {
    if (!isRecord(row)) {
      return invalid(`rows.${rowIndex} must be an object.`, `rows.${rowIndex}`);
    }
    for (const key of columnKeys) {
      if (!(key in row)) {
        return invalid(`rows.${rowIndex}.${key} is missing.`, `rows.${rowIndex}.${key}`);
      }
    }
  }
  return { ok: true, value: payload };
}

function validateMetricGridPayload(payload: unknown): ValidationResult<unknown> {
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  if (!Array.isArray(record.value.metrics) || record.value.metrics.length === 0) {
    return invalid("metrics must be a non-empty array.", "metrics");
  }
  for (const [index, metric] of record.value.metrics.entries()) {
    if (!isRecord(metric)) {
      return invalid(`metrics.${index} must be an object.`, `metrics.${index}`);
    }
    const label = nonBlankString(metric.label, `metrics.${index}.label`);
    if (!label.ok) {
      return label;
    }
    if (typeof metric.value !== "string" && typeof metric.value !== "number") {
      return invalid(`metrics.${index}.value must be a string or number.`, `metrics.${index}.value`);
    }
    if (typeof metric.trend !== "undefined") {
      const trend = enumValue(metric.trend, ["up", "down", "neutral"], `metrics.${index}.trend`);
      if (!trend.ok) {
        return trend;
      }
    }
  }
  return { ok: true, value: payload };
}

function validateDashboardPayload(payload: unknown, depth: number): ValidationResult<unknown> {
  if (depth >= 3) {
    return invalid("Dashboard nesting is too deep.", "children");
  }
  const record = versionedRecord(payload);
  if (!record.ok) {
    return record;
  }
  const title = nonBlankString(record.value.title, "title");
  if (!title.ok) {
    return title;
  }
  if (!Array.isArray(record.value.children) || record.value.children.length === 0) {
    return invalid("children must be a non-empty array.", "children");
  }
  for (const [index, child] of record.value.children.entries()) {
    if (!isRecord(child)) {
      return invalid(`children.${index} must be an object.`, `children.${index}`);
    }
    const component = nonBlankString(child.component, `children.${index}.component`);
    if (!component.ok) {
      return component;
    }
    if (!COMPONENT_NAME_SET.has(component.value)) {
      return invalid(
        `children.${index}.component must be a known Houmao component.`,
        `children.${index}.component`,
      );
    }
    if (!isRecord(child.props)) {
      return invalid(`children.${index}.props must be an object.`, `children.${index}.props`);
    }
    const width = enumValue(child.width ?? "full", ["full", "half", "third"], `children.${index}.width`);
    if (!width.ok) {
      return width;
    }
    const nested = validateComponentPayload(component.value, child.props, depth + 1);
    if (!nested.ok) {
      return invalid(nested.error, nested.path ? `children.${index}.props.${nested.path}` : `children.${index}.props`);
    }
  }
  return { ok: true, value: payload };
}

function validateDatum(value: unknown, path: string): ValidationResult<void> {
  if (!isRecord(value)) {
    return invalid(`${path} must be an object.`, path);
  }
  const label = nonBlankString(value.label, `${path}.label`);
  if (!label.ok) {
    return label;
  }
  if (typeof value.value !== "number" || !Number.isFinite(value.value)) {
    return invalid(`${path}.value must be a finite number.`, `${path}.value`);
  }
  return { ok: true, value: undefined };
}

function versionedRecord(value: unknown): ValidationResult<JsonObject> {
  if (!isRecord(value)) {
    return invalid("payload must be an object.", "payload");
  }
  if (value.schemaVersion !== 1) {
    return invalid("schemaVersion must be 1.", "schemaVersion");
  }
  return { ok: true, value };
}

function publishTarget(agentId: string, request: EventsRequest | ComponentRequest): PublishTarget {
  return {
    threadId: stringValue(request.threadId) ?? `${agentId}-thread`,
    runId: stringValue(request.runId),
    connectionId: stringValue(request.connectionId),
  };
}

function replayEnabledFromConnect(record: JsonObject): boolean {
  if (record.replay === false) {
    return false;
  }
  const forwarded = record.forwardedProps;
  if (isRecord(forwarded) && forwarded.replay === false) {
    return false;
  }
  return true;
}

function stateFor(agentId: string): DebugAgentState {
  const existing = states.get(agentId);
  if (existing) {
    return existing;
  }
  const state: DebugAgentState = {
    agentId,
    nextConnectionIndex: 0,
    nextToolCallIndex: 0,
    subscriptions: new Map(),
    replayBuffers: new Map(),
  };
  states.set(agentId, state);
  return state;
}

function parseRoute(pathname: string):
  | {
      ok: true;
      kind: "ag-ui";
      agentId: string;
      route: string;
      connectionId?: string;
    }
  | {
      ok: true;
      kind: "component";
      agentId: string;
      componentName: string;
    }
  | {
      ok: false;
      status: number;
      code: string;
      detail: string;
    } {
  const segments = pathname.split("/").filter(Boolean).map((segment) => decodeURIComponent(segment));
  const agentId = segments[0] ?? "";
  if (!safeAgentId(agentId)) {
    return {
      ok: false,
      status: 400,
      code: "debug_agent_id_invalid",
      detail: "Debug Agent ID must start with debug-agent- and contain only letters, numbers, dot, underscore, or hyphen.",
    };
  }
  if (segments[1] === "v1" && segments[2] === "ag-ui") {
    if (segments[3] === "connections" && segments[4]) {
      return {
        ok: true,
        kind: "ag-ui",
        agentId,
        route: "connections",
        connectionId: segments[4],
      };
    }
    if (segments[3]) {
      return { ok: true, kind: "ag-ui", agentId, route: segments[3] };
    }
  }
  if (segments[1] === "components" && segments[2]) {
    return { ok: true, kind: "component", agentId, componentName: segments[2] };
  }
  return {
    ok: false,
    status: 404,
    code: "not_found",
    detail: "Debug Agent route not found.",
  };
}

function debugStatus(): unknown {
  return {
    status: "ready",
    prefix: DEBUG_PREFIX,
    localOnly: true,
    limits: {
      maxBodyBytes: MAX_BODY_BYTES,
      maxEvents: MAX_EVENTS,
      maxConnectionsPerAgent: MAX_CONNECTIONS_PER_AGENT,
      maxReplayBatchesPerThread: MAX_REPLAY_BATCHES_PER_THREAD,
    },
    routes: [
      "GET /__houmao_debug_agents/status",
      "GET /__houmao_debug_agents/{agent_id}/v1/ag-ui/capabilities",
      "POST /__houmao_debug_agents/{agent_id}/v1/ag-ui/connect",
      "POST /__houmao_debug_agents/{agent_id}/v1/ag-ui/runs",
      "POST /__houmao_debug_agents/{agent_id}/v1/ag-ui/events",
      "DELETE /__houmao_debug_agents/{agent_id}/v1/ag-ui/connections/{connection_id}",
      "POST /__houmao_debug_agents/{agent_id}/components/{component_name}",
    ],
    components: COMPONENT_NAMES.map((name) => ({
      name,
      template: COMPONENT_TEMPLATES[name],
    })),
    agents: [...states.values()].map((state) => ({
      agentId: state.agentId,
      connectionCount: state.subscriptions.size,
      replayThreads: [...state.replayBuffers.keys()],
    })),
  };
}

function capabilities(agentId: string): unknown {
  return {
    capabilities: {
      identity: {
        name: agentId.replace(/-/g, " "),
        type: "debug-agent",
        provider: "houmao-ag-ui-workbench",
        metadata: {
          agentId,
          managedAgent: false,
          localOnly: true,
        },
      },
      transport: {
        streaming: true,
        websocket: false,
        httpBinary: false,
        pushNotifications: false,
        resumable: false,
      },
      state: {
        snapshots: true,
        deltas: false,
        memory: false,
        persistentState: false,
      },
      tools: {
        supported: true,
        clientProvided: false,
        items: COMPONENT_NAMES.map((name) => ({
          name,
          description: "Houmao typed component payload carried by AG-UI tool-call events.",
        })),
      },
      custom: {
        debugRelay: true,
        components: COMPONENT_NAMES,
      },
    },
    houmao: {
      features: {
        httpSse: true,
        guiConnect: true,
        textInputParsing: false,
        stateSnapshots: true,
        taskRunSubmission: false,
        stateDeltas: false,
        frontendToolExecution: false,
        generatedGraphics: true,
        openGenerativeUi: true,
        multimodalInput: false,
      },
      gateway: {
        kind: "debug-agent-relay",
        routePrefix: DEBUG_PREFIX,
        agentId,
      },
      lifecycleBoundary: "debug-relay-only",
      agentLifecycleManagedByGui: false,
    },
  };
}

async function readJson(req: IncomingMessage): Promise<
  | { ok: true; value: unknown; bytes: number }
  | { ok: false; status: number; code: string; detail: string }
> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += buffer.length;
    if (size > MAX_BODY_BYTES) {
      return {
        ok: false,
        status: 413,
        code: "payload_too_large",
        detail: `Request body must be at most ${MAX_BODY_BYTES} bytes.`,
      };
    }
    chunks.push(buffer);
  }
  if (size === 0) {
    return { ok: true, value: {}, bytes: 0 };
  }
  try {
    return { ok: true, value: JSON.parse(Buffer.concat(chunks).toString("utf8")) as unknown, bytes: size };
  } catch {
    return {
      ok: false,
      status: 400,
      code: "json_invalid",
      detail: "Request body must be valid JSON.",
    };
  }
}

function writeSse(res: ServerResponse, event: AgUiEvent): void {
  if (res.writableEnded) {
    return;
  }
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  if (res.writableEnded) {
    return;
  }
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function safeAgentId(value: string): boolean {
  return /^debug-agent-[A-Za-z0-9_.-]+$/.test(value);
}

function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function stringField(record: JsonObject, key: string, fallback: string): string {
  return stringValue(record[key]) ?? fallback;
}

function nonBlankString(value: unknown, path: string): ValidationResult<string> {
  if (typeof value !== "string" || value.trim() === "") {
    return invalid(`${path} must be a non-empty string.`, path);
  }
  return { ok: true, value: value.trim() };
}

function enumValue<T extends string>(
  value: unknown,
  values: readonly T[],
  path: string,
): ValidationResult<T> {
  if (typeof value !== "string" || !values.includes(value as T)) {
    return invalid(`${path} must be one of ${values.join(", ")}.`, path);
  }
  return { ok: true, value: value as T };
}

function invalid(error: string, path?: string): ValidationResult<never> {
  return { ok: false, error, path };
}

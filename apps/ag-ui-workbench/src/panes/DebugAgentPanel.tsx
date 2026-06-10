import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import { Cable, CheckCircle2, CircleStop, Clipboard, Eraser, Send, X } from "lucide-react";

import { AgUiHttpError, buildConnectInput, connectAgUi, detachAgUi } from "../ag-ui/client";
import {
  extractConnectionId,
  initialPaneEventState,
  reduceAgUiEvent,
  reduceHttpError,
  reduceParseError,
} from "../ag-ui/reducer";
import type { TargetConfig } from "../ag-ui/types";
import {
  debugAgentRelayBaseUrl,
  debugAgentUrl,
  defaultDebugAgentConfig,
  defaultTarget,
} from "../storage";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";
import { AgUiDisplaySurface } from "./AgUiDisplaySurface";

type SenderMode = "component" | "raw";
type ComponentName =
  | "houmao.chart.bar"
  | "houmao.chart.line"
  | "houmao.chart.pie"
  | "houmao.table"
  | "houmao.metric_grid"
  | "houmao.dashboard";

interface PanelParams {
  paneId: string;
}

interface PublishRequest {
  url: string;
  body: Record<string, unknown>;
}

const COMPONENT_NAMES: ComponentName[] = [
  "houmao.chart.bar",
  "houmao.chart.line",
  "houmao.chart.pie",
  "houmao.table",
  "houmao.metric_grid",
  "houmao.dashboard",
];

const COMPONENT_TEMPLATES: Record<ComponentName, unknown> = {
  "houmao.chart.bar": {
    schemaVersion: 1,
    title: "Debug Agent Sales",
    subtitle: "External AG-UI post rendered through the normal display path",
    xLabel: "Region",
    yLabel: "Units",
    data: [
      { label: "North", value: 42, color: "#79a35d" },
      { label: "South", value: 28, color: "#d3a749" },
      { label: "West", value: 36, color: "#6aa6b8" },
    ],
  },
  "houmao.chart.line": {
    schemaVersion: 1,
    title: "Debug Agent Trend",
    xLabel: "Step",
    yLabel: "Score",
    series: [
      {
        name: "Quality",
        data: [
          { label: "T1", value: 72 },
          { label: "T2", value: 81 },
          { label: "T3", value: 77 },
        ],
      },
    ],
  },
  "houmao.chart.pie": {
    schemaVersion: 1,
    title: "Debug Agent Split",
    data: [
      { label: "Ready", value: 58 },
      { label: "Queued", value: 23 },
      { label: "Blocked", value: 6 },
    ],
  },
  "houmao.table": {
    schemaVersion: 1,
    title: "Debug Agent Table",
    columns: [
      { key: "name", label: "Name", kind: "text" },
      { key: "count", label: "Count", kind: "number", align: "right" },
    ],
    rows: [
      { name: "North", count: 42 },
      { name: "South", count: 28 },
    ],
  },
  "houmao.metric_grid": {
    schemaVersion: 1,
    title: "Debug Agent Metrics",
    metrics: [
      { label: "Delivered", value: 1, delta: "+1", trend: "up" },
      { label: "Replay", value: "enabled", trend: "neutral" },
    ],
  },
  "houmao.dashboard": {
    schemaVersion: 1,
    title: "Debug Agent Dashboard",
    children: [
      {
        component: "houmao.metric_grid",
        width: "full",
        props: {
          schemaVersion: 1,
          title: "Delivery Metrics",
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
          title: "Dashboard Bars",
          data: [
            { label: "A", value: 18 },
            { label: "B", value: 31 },
          ],
        },
      },
      {
        component: "houmao.table",
        width: "half",
        props: {
          schemaVersion: 1,
          title: "Dashboard Rows",
          columns: [
            { key: "item", label: "Item", kind: "text" },
            { key: "state", label: "State", kind: "text" },
          ],
          rows: [
            { item: "Relay", state: "ready" },
            { item: "Display", state: "connected" },
          ],
        },
      },
    ],
  },
};

export function DebugAgentPanel(props: IDockviewPanelProps<PanelParams>) {
  const { storage, updateDebugAgent, removePaneRecord } = useWorkbench();
  const { paneId } = props.params;
  const record = paneRecordOrDefault(storage, paneId, "debug-agent");
  const debugAgent = record.debugAgent ?? defaultDebugAgentConfig(paneId);
  const target = debugTarget(record.target, debugAgent.debugAgentId);
  const activeTargetRef = useRef<TargetConfig>(target);
  const abortRef = useRef<AbortController | null>(null);
  const connectionIdRef = useRef<string | null>(null);
  const [eventState, setEventState] = useState(initialPaneEventState);
  const [panelStatus, setPanelStatus] = useState(eventState.status);
  const [mode, setMode] = useState<SenderMode>("component");
  const [componentName, setComponentName] = useState<ComponentName>("houmao.chart.bar");
  const [editor, setEditor] = useState(() => formatJson(COMPONENT_TEMPLATES["houmao.chart.bar"]));
  const [publishResponse, setPublishResponse] = useState<unknown>({
    status: "idle",
    detail: "No message has been sent.",
  });

  const relayBaseUrl = debugAgentRelayBaseUrl(debugAgent.debugAgentId);
  const eventsEndpoint = `${relayBaseUrl}/v1/ag-ui/events`;
  const componentEndpoint = `${relayBaseUrl}/components/${encodeURIComponent(componentName)}`;
  const latestErrors = useMemo(() => eventState.errors.slice(-3), [eventState.errors]);
  const curlCommand = useMemo(
    () => {
      try {
        const request = buildPublishRequest({
          mode,
          componentName,
          editor,
          eventsEndpoint,
          componentEndpoint,
          threadId: target.threadId,
          replayEnabled: debugAgent.replayEnabled,
          validateOnly: false,
        });
        return curlCommandFor(request);
      } catch (error) {
        return `# ${error instanceof Error ? error.message : "Fix the JSON before copying curl."}`;
      }
    },
    [
      componentEndpoint,
      componentName,
      debugAgent.replayEnabled,
      editor,
      eventsEndpoint,
      mode,
      target.threadId,
    ],
  );

  useEffect(() => {
    props.api.setTitle(target.label || paneId);
  }, [paneId, props.api, target]);

  useEffect(() => {
    activeTargetRef.current = target;
    void connect();
    return () => {
      abortRef.current?.abort();
      void detachAgUi(activeTargetRef.current, connectionIdRef.current).catch(() => undefined);
      abortRef.current = null;
      connectionIdRef.current = null;
    };
  }, [target.url, target.threadId]);

  async function connect(): Promise<void> {
    abortRef.current?.abort();
    abortRef.current = null;
    const controller = new AbortController();
    abortRef.current = controller;
    activeTargetRef.current = target;
    setPanelStatus("connecting");
    const input = {
      ...buildConnectInput({ paneId, threadId: target.threadId }),
      replay: debugAgent.replayEnabled,
    };
    void connectAgUi(
      target,
      input,
      {
        onOpen: () => setPanelStatus("connected"),
        onRaw: () => undefined,
        onParseError: (raw) => setEventState((current) => reduceParseError(current, raw)),
        onEvent: (event, raw) => {
          if (controller.signal.aborted) {
            return;
          }
          const connectionId = extractConnectionId(event);
          if (connectionId) {
            connectionIdRef.current = connectionId;
          }
          setEventState((current) => reduceAgUiEvent(current, event, raw));
        },
      },
      controller.signal,
    )
      .then(() => {
        if (!controller.signal.aborted) {
          setPanelStatus("disconnected");
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          showRequestError(error);
        }
      });
  }

  async function disconnect(): Promise<void> {
    await stopActiveStream(true);
    setPanelStatus("disconnected");
  }

  async function closePane(): Promise<void> {
    await stopActiveStream(true);
    removePaneRecord(paneId);
    props.api.close();
  }

  async function stopActiveStream(detach: boolean): Promise<void> {
    const detachTarget = activeTargetRef.current;
    abortRef.current?.abort();
    abortRef.current = null;
    if (detach) {
      await detachAgUi(detachTarget, connectionIdRef.current).catch((error) => {
        setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
      });
      connectionIdRef.current = null;
    }
  }

  function showRequestError(error: unknown): void {
    setPanelStatus("error");
    setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
  }

  const switchMode = (nextMode: SenderMode) => {
    setMode(nextMode);
    setEditor(
      nextMode === "component"
        ? formatJson(COMPONENT_TEMPLATES[componentName])
        : formatJson(rawEventBatch(target.threadId)),
    );
  };

  const switchComponent = (nextName: ComponentName) => {
    setComponentName(nextName);
    if (mode === "component") {
      setEditor(formatJson(COMPONENT_TEMPLATES[nextName]));
    }
  };

  const validate = async () => {
    await postEditor(true);
  };

  const send = async () => {
    await postEditor(false);
  };

  const postEditor = async (validateOnly: boolean) => {
    try {
      const request = buildPublishRequest({
        mode,
        componentName,
        editor,
        eventsEndpoint,
        componentEndpoint,
        threadId: target.threadId,
        replayEnabled: debugAgent.replayEnabled,
        validateOnly,
      });
      const response = await fetch(request.url, {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify(request.body),
      });
      const responseText = await response.text();
      setPublishResponse({
        httpStatus: response.status,
        httpStatusText: response.statusText,
        body: parseJson(responseText),
      });
    } catch (error) {
      setPublishResponse({
        status: "editor_error",
        detail: error instanceof Error ? error.message : "Debug Agent publish failed.",
      });
    }
  };

  const copyCurl = async () => {
    try {
      await navigator.clipboard?.writeText(curlCommand);
      setPublishResponse({
        status: "copied",
        detail: "curl command copied to clipboard.",
      });
    } catch {
      setPublishResponse({
        status: "copy_unavailable",
        detail: "Clipboard access is unavailable. Select the curl command manually.",
      });
    }
  };

  const clearDisplay = () => {
    setEventState(initialPaneEventState());
  };

  const setReplayEnabled = (replayEnabled: boolean) => {
    updateDebugAgent(paneId, {
      ...debugAgent,
      replayEnabled,
    });
  };

  const visibleStatus = panelStatus === "empty" ? eventState.status : panelStatus;

  return (
    <section className="debug-agent-panel" data-testid={`panel-${paneId}`}>
      <header className="pane-header">
        <div>
          <span className={`status-dot ${visibleStatus}`} />
          <strong>{target.label || paneId}</strong>
          <span data-testid={`status-${paneId}`}>{visibleStatus}</span>
        </div>
        <div className="icon-row">
          <button title="Connect display" data-testid={`connect-${paneId}`} onClick={() => void connect()}>
            <Cable size={15} />
          </button>
          <button title="Disconnect display" data-testid={`disconnect-${paneId}`} onClick={() => void disconnect()}>
            <CircleStop size={15} />
          </button>
          <button title="Close debug pane" data-testid={`close-${paneId}`} onClick={() => void closePane()}>
            <X size={15} />
          </button>
        </div>
      </header>

      <div className="debug-agent-grid">
        <section className="debug-sender" data-testid={`debug-sender-${paneId}`}>
          <div className="debug-endpoints">
            <label>
              <span>Events endpoint</span>
              <input data-testid={`debug-events-endpoint-${paneId}`} readOnly value={eventsEndpoint} />
            </label>
            <label>
              <span>Thread ID</span>
              <input data-testid={`debug-thread-${paneId}`} readOnly value={target.threadId} />
            </label>
          </div>

          <div className="debug-controls">
            <label>
              <span>Mode</span>
              <select
                data-testid={`debug-mode-${paneId}`}
                value={mode}
                onChange={(event) => switchMode(event.target.value as SenderMode)}
              >
                <option value="component">Typed component</option>
                <option value="raw">Raw AG-UI events</option>
              </select>
            </label>
            <label>
              <span>Component</span>
              <select
                data-testid={`debug-component-${paneId}`}
                value={componentName}
                disabled={mode !== "component"}
                onChange={(event) => switchComponent(event.target.value as ComponentName)}
              >
                {COMPONENT_NAMES.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label className="debug-toggle">
              <input
                data-testid={`debug-replay-${paneId}`}
                type="checkbox"
                checked={debugAgent.replayEnabled}
                onChange={(event) => setReplayEnabled(event.target.checked)}
              />
              <span>Replay posted batches for future display connections</span>
            </label>
          </div>

          <textarea
            className="debug-editor"
            data-testid={`debug-editor-${paneId}`}
            value={editor}
            spellCheck={false}
            onChange={(event) => setEditor(event.target.value)}
          />

          <div className="debug-action-row">
            <button data-testid={`debug-validate-${paneId}`} title="Validate message" onClick={() => void validate()}>
              <CheckCircle2 size={15} />
              Validate
            </button>
            <button className="primary" data-testid={`debug-send-${paneId}`} title="Send to display" onClick={() => void send()}>
              <Send size={15} />
              Send
            </button>
            <button data-testid={`debug-copy-curl-${paneId}`} title="Copy curl command" onClick={() => void copyCurl()}>
              <Clipboard size={15} />
              Copy curl
            </button>
            <button data-testid={`debug-clear-${paneId}`} title="Clear display" onClick={clearDisplay}>
              <Eraser size={15} />
              Clear display
            </button>
          </div>

          <details className="debug-curl" open>
            <summary>curl</summary>
            <textarea data-testid={`debug-curl-${paneId}`} readOnly value={curlCommand} />
          </details>

          <section className="debug-response">
            <h3>Publish response</h3>
            <pre data-testid={`debug-response-${paneId}`}>{formatJson(publishResponse)}</pre>
          </section>
        </section>

        <section className="debug-display" data-testid={`debug-display-${paneId}`}>
          <AgUiDisplaySurface paneId={paneId} eventState={eventState} latestErrors={latestErrors} />
        </section>
      </div>
    </section>
  );
}

function debugTarget(target: TargetConfig, debugAgentId: string): TargetConfig {
  const fallback = defaultTarget(debugAgentId, "debug-agent");
  return {
    label: target.label || fallback.label,
    url: debugAgentUrl(debugAgentId),
    threadId: target.threadId || fallback.threadId,
    source: { kind: "manual" },
  };
}

function buildPublishRequest({
  mode,
  componentName,
  editor,
  eventsEndpoint,
  componentEndpoint,
  threadId,
  replayEnabled,
  validateOnly,
}: {
  mode: SenderMode;
  componentName: ComponentName;
  editor: string;
  eventsEndpoint: string;
  componentEndpoint: string;
  threadId: string;
  replayEnabled: boolean;
  validateOnly: boolean;
}): PublishRequest {
  const parsed = parseJson(editor);
  if (mode === "component") {
    return {
      url: componentEndpoint,
      body: {
        threadId,
        replay: replayEnabled,
        validateOnly,
        payload: parsed,
      },
    };
  }
  if (Array.isArray(parsed)) {
    return {
      url: eventsEndpoint,
      body: {
        threadId,
        replay: replayEnabled,
        validateOnly,
        events: parsed,
      },
    };
  }
  if (!isRecord(parsed)) {
    throw new Error("Raw AG-UI mode expects a JSON object with events or an events array.");
  }
  return {
    url: eventsEndpoint,
    body: {
      ...parsed,
      threadId: typeof parsed.threadId === "string" && parsed.threadId ? parsed.threadId : threadId,
      replay: replayEnabled,
      validateOnly,
    },
  };
}

function rawEventBatch(threadId: string): Record<string, unknown> {
  return {
    threadId,
    events: [
      {
        type: "TOOL_CALL_START",
        toolCallId: "debug-raw-bar",
        toolCallName: "houmao.chart.bar",
        parentMessageId: "debug-raw-message",
      },
      {
        type: "TOOL_CALL_ARGS",
        toolCallId: "debug-raw-bar",
        delta: JSON.stringify(COMPONENT_TEMPLATES["houmao.chart.bar"]),
      },
      {
        type: "TOOL_CALL_END",
        toolCallId: "debug-raw-bar",
      },
    ],
  };
}

function curlCommandFor(request: PublishRequest): string {
  return [
    "curl -sS",
    "-X POST",
    shellQuote(request.url),
    "-H",
    shellQuote("content-type: application/json"),
    "--data",
    shellQuote(JSON.stringify(request.body)),
  ].join(" ");
}

function shellQuote(value: string): string {
  return `'${value.replace(/'/g, "'\\''")}'`;
}

function parseJson(value: string): unknown {
  return JSON.parse(value) as unknown;
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof AgUiHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "AG-UI request failed.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

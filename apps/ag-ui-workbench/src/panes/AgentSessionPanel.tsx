import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import { Activity, Braces, Cable, CircleStop, PanelRightOpen, Play, RefreshCw, Trash2, X } from "lucide-react";

import { buildConnectInput, buildRunInput, connectAgUi, detachAgUi, fetchCapabilities, runAgUi, AgUiHttpError } from "../ag-ui/client";
import { ToolCallRenderer } from "../ag-ui/componentRenderers";
import { extractConnectionId, initialPaneEventState, reduceAgUiEvent, reduceHttpError, reduceParseError } from "../ag-ui/reducer";
import type { CapabilitiesResponse, TargetConfig } from "../ag-ui/types";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";
import { CapabilityBadges } from "./CapabilityBadges";
import { TargetForm } from "./TargetForm";

interface PanelParams {
  paneId: string;
  kind: "operator" | "agent";
}

export function AgentSessionPanel(props: IDockviewPanelProps<PanelParams>) {
  const { storage, updateTarget, removePaneRecord, openAgentPicker } = useWorkbench();
  const { paneId, kind } = props.params;
  const record = paneRecordOrDefault(storage, paneId, kind);
  const target = record.target;
  const activeTargetRef = useRef<TargetConfig>(target);
  const resetTokenRef = useRef(record.resetToken ?? 0);
  const abortRef = useRef<AbortController | null>(null);
  const connectionIdRef = useRef<string | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [eventState, setEventState] = useState(initialPaneEventState);
  const [prompt, setPrompt] = useState("");
  const [panelStatus, setPanelStatus] = useState(eventState.status);

  useEffect(() => {
    props.api.setTitle(target.label || (kind === "operator" ? "Operator" : paneId));
  }, [kind, paneId, props.api, target]);

  useEffect(() => {
    const resetToken = record.resetToken ?? 0;
    if (resetToken === resetTokenRef.current) {
      return;
    }
    resetTokenRef.current = resetToken;
    const detachTarget = activeTargetRef.current;
    const connectionId = connectionIdRef.current;
    abortRef.current?.abort();
    abortRef.current = null;
    connectionIdRef.current = null;
    activeTargetRef.current = target;
    setCapabilities(null);
    setEventState(initialPaneEventState());
    setPanelStatus("empty");
    setPrompt("");
    void detachAgUi(detachTarget, connectionId).catch((error) => {
      setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
    });
  }, [record.resetToken, target]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      void detachAgUi(activeTargetRef.current, connectionIdRef.current).catch(() => undefined);
    };
  }, []);

  const latestErrors = useMemo(() => eventState.errors.slice(-3), [eventState.errors]);

  const setTarget = (nextTarget: TargetConfig) => {
    updateTarget(paneId, nextTarget);
  };

  const refreshCapabilities = async () => {
    const controller = new AbortController();
    setPanelStatus("connecting");
    try {
      const response = await fetchCapabilities(target, controller.signal);
      setCapabilities(response);
      setPanelStatus("connected");
    } catch (error) {
      showRequestError(error);
    }
  };

  const connect = async () => {
    await stopActiveStream(false);
    const controller = new AbortController();
    abortRef.current = controller;
    activeTargetRef.current = target;
    setPanelStatus("connecting");
    const input = buildConnectInput({ paneId, threadId: target.threadId, paneKind: kind });
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
  };

  const run = async () => {
    const text = prompt.trim();
    if (!text) {
      return;
    }
    await stopActiveStream(false);
    setPrompt("");
    const controller = new AbortController();
    abortRef.current = controller;
    activeTargetRef.current = target;
    setPanelStatus("running");
    const input = buildRunInput({ paneId, threadId: target.threadId, message: text, paneKind: kind });
    void runAgUi(
      target,
      input,
      {
        onOpen: () => setPanelStatus("running"),
        onRaw: () => undefined,
        onParseError: (raw) => setEventState((current) => reduceParseError(current, raw)),
        onEvent: (event, raw) => {
          if (controller.signal.aborted) {
            return;
          }
          setEventState((current) => reduceAgUiEvent(current, event, raw));
        },
      },
      controller.signal,
    )
      .then(() => {
        if (!controller.signal.aborted) {
          setPanelStatus("finished");
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          showRequestError(error);
        }
      });
  };

  const disconnect = async () => {
    await stopActiveStream(true);
    setPanelStatus("disconnected");
  };

  const closePane = async () => {
    await stopActiveStream(true);
    removePaneRecord(paneId);
    props.api.close();
  };

  const moveRight = () => {
    const operator = props.containerApi.getPanel("operator");
    props.api.moveTo({
      group: operator?.api.group ?? props.api.group,
      position: "right",
    });
  };

  const stopActiveStream = async (detach: boolean) => {
    const detachTarget = activeTargetRef.current;
    abortRef.current?.abort();
    abortRef.current = null;
    if (detach) {
      await detachAgUi(detachTarget, connectionIdRef.current).catch((error) => {
        setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
      });
      connectionIdRef.current = null;
    }
  };

  const showRequestError = (error: unknown) => {
    setPanelStatus("error");
    setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
  };

  const visibleStatus = panelStatus === "empty" ? eventState.status : panelStatus;

  return (
    <section className="session-panel" data-testid={`panel-${paneId}`}>
      <header className="pane-header">
        <div>
          <span className={`status-dot ${visibleStatus}`} />
          <strong>{target.label || paneId}</strong>
          <span data-testid={`status-${paneId}`}>{visibleStatus}</span>
        </div>
        <div className="icon-row">
          <button title="Refresh capabilities" data-testid={`capabilities-${paneId}`} onClick={() => void refreshCapabilities()}>
            <RefreshCw size={15} />
          </button>
          <button title="Connect" data-testid={`connect-${paneId}`} onClick={() => void connect()}>
            <Cable size={15} />
          </button>
          <button title="Disconnect" data-testid={`disconnect-${paneId}`} onClick={() => void disconnect()}>
            <CircleStop size={15} />
          </button>
          {kind === "agent" ? (
            <>
              <button title="Move to right split" data-testid={`split-right-${paneId}`} onClick={moveRight}>
                <PanelRightOpen size={15} />
              </button>
              <button title="Close pane" data-testid={`close-${paneId}`} onClick={() => void closePane()}>
                <X size={15} />
              </button>
            </>
          ) : null}
        </div>
      </header>

      <TargetForm
        paneId={paneId}
        target={target}
        onChange={setTarget}
        onChooseAgent={() => openAgentPicker({ mode: "retarget", paneId })}
      />
      <CapabilityBadges capabilities={capabilities} />

      <div className="composer">
        <textarea
          data-testid={`prompt-${paneId}`}
          value={prompt}
          placeholder={kind === "operator" ? "Operator prompt" : "Pane prompt"}
          onChange={(event) => setPrompt(event.target.value)}
        />
        <button className="run-button" title="Submit AG-UI run" data-testid={`run-${paneId}`} onClick={() => void run()}>
          <Play size={16} />
          Run
        </button>
      </div>

      {latestErrors.length > 0 ? (
        <div className="error-stack" data-testid={`errors-${paneId}`}>
          {latestErrors.map((error, index) => (
            <div key={`${error}-${index}`}>{error}</div>
          ))}
        </div>
      ) : null}

      <div className="pane-body">
        <section className="surface" data-testid={`transcript-${paneId}`}>
          <h3>
            <Activity size={14} />
            Transcript
          </h3>
          {eventState.transcript.length === 0 ? <p className="empty">No messages</p> : null}
          {eventState.transcript.map((message) => (
            <article key={message.id} className="message">
              <span>{message.role}</span>
              <p>{message.content}</p>
            </article>
          ))}
          {eventState.toolCalls.map((toolCall) => (
            <ToolCallRenderer key={toolCall.id} toolCall={toolCall} paneId={paneId} />
          ))}
        </section>

        <section className="surface diagnostics">
          <h3>
            <Braces size={14} />
            Diagnostics
          </h3>
          <details open>
            <summary>State</summary>
            <pre data-testid={`state-${paneId}`}>{formatJson(eventState.stateSnapshot)}</pre>
          </details>
          <details>
            <summary>Activity</summary>
            <pre>{formatJson(eventState.activity)}</pre>
          </details>
          <details>
            <summary>Tool Calls</summary>
            <pre>{formatJson(eventState.toolCalls)}</pre>
          </details>
          <details>
            <summary>Raw</summary>
            <pre data-testid={`raw-${paneId}`}>{formatJson(eventState.raw.map((entry) => entry.event ?? entry.parseError ?? entry.data))}</pre>
          </details>
        </section>
      </div>
      {kind === "agent" ? (
        <button className="danger-link" title="Remove pane" onClick={() => void closePane()}>
          <Trash2 size={13} />
          Remove
        </button>
      ) : null}
    </section>
  );
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof AgUiHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "AG-UI request failed.";
}

function formatJson(value: unknown): string {
  if (typeof value === "undefined") {
    return "{}";
  }
  return JSON.stringify(value, null, 2);
}

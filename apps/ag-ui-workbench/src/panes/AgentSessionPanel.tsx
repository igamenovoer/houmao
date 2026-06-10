import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import { Cable, CircleStop, PanelRightOpen, Play, RefreshCw, Trash2, X } from "lucide-react";

import { buildConnectInput, buildRunInput, connectAgUi, detachAgUi, fetchCapabilities, runAgUi, AgUiHttpError } from "../ag-ui/client";
import { AgentAddressUnavailableError, resolveTargetConfigForConnect } from "../ag-ui/discovery";
import { extractConnectionId, initialPaneEventState, reduceAgUiEvent, reduceHttpError, reduceParseError, type PaneRunStatus } from "../ag-ui/reducer";
import type { CapabilitiesResponse, TargetConfig } from "../ag-ui/types";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";
import { AgUiDisplaySurface } from "./AgUiDisplaySurface";
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
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const stoppedRef = useRef(false);
  const latestEventIdRef = useRef<string | null>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const threadRef = useRef(target.threadId);
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
    clearReconnectTimer();
    stoppedRef.current = true;
    abortRef.current?.abort();
    abortRef.current = null;
    connectionIdRef.current = null;
    resetReplayCursor(target.threadId);
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
      clearReconnectTimer();
      stoppedRef.current = true;
      abortRef.current?.abort();
      void detachAgUi(activeTargetRef.current, connectionIdRef.current).catch(() => undefined);
    };
  }, []);

  const latestErrors = useMemo(() => eventState.errors.slice(-3), [eventState.errors]);

  const setTarget = (nextTarget: TargetConfig) => {
    resetReplayCursor(nextTarget.threadId);
    updateTarget(paneId, nextTarget);
  };

  const refreshCapabilities = async () => {
    const controller = new AbortController();
    setPanelStatus("connecting");
    try {
      const resolvedTarget = await resolveTargetConfigForConnect(target, controller.signal);
      if (!sameTarget(target, resolvedTarget)) {
        activeTargetRef.current = resolvedTarget;
        updateTarget(paneId, resolvedTarget);
      }
      const response = await fetchCapabilities(resolvedTarget, controller.signal);
      setCapabilities(response);
      setPanelStatus("connected");
    } catch (error) {
      showRequestError(error);
    }
  };

  const connect = async () => {
    await stopActiveStream(false);
    stoppedRef.current = false;
    reconnectAttemptRef.current = 0;
    activeTargetRef.current = target;
    syncReplayThread(target.threadId);
    void connectAttempt();
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
    syncReplayThread(target.threadId);
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
          if (!acceptReplayEvent(raw.sseEventId)) {
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
    stoppedRef.current = true;
    clearReconnectTimer();
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

  const connectAttempt = async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    const baseTarget = activeTargetRef.current;
    setPanelStatus(reconnectAttemptRef.current > 0 ? "reconnecting" : "connecting");
    try {
      const resolvedTarget = await resolveTargetConfigForConnect(baseTarget, controller.signal);
      if (controller.signal.aborted || stoppedRef.current) {
        return;
      }
      activeTargetRef.current = resolvedTarget;
      syncReplayThread(resolvedTarget.threadId);
      if (!sameTarget(baseTarget, resolvedTarget)) {
        updateTarget(paneId, resolvedTarget);
      }
      const input = buildConnectInput({
        paneId,
        threadId: resolvedTarget.threadId,
        paneKind: kind,
        lastSeenEventId: latestEventIdRef.current,
      });
      await connectAgUi(
        resolvedTarget,
        input,
        {
          onOpen: () => {
            reconnectAttemptRef.current = 0;
            setPanelStatus("connected");
          },
          onRaw: () => undefined,
          onParseError: (raw) => setEventState((current) => reduceParseError(current, raw)),
          onEvent: (event, raw) => {
            if (controller.signal.aborted) {
              return;
            }
            if (!acceptReplayEvent(raw.sseEventId)) {
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
      );
      if (!controller.signal.aborted && !stoppedRef.current) {
        connectionIdRef.current = null;
        if (resolvedTarget.source?.kind === "discovered") {
          scheduleReconnect("reconnecting");
        } else {
          setPanelStatus("disconnected");
        }
      }
    } catch (error) {
      if (controller.signal.aborted || stoppedRef.current) {
        return;
      }
      if (baseTarget.source?.kind === "discovered") {
        const status = retryStatusForError(error);
        if (!(error instanceof AgentAddressUnavailableError)) {
          setEventState((current) => reduceHttpError(current, requestErrorMessage(error)));
        }
        scheduleReconnect(status);
        return;
      }
      showRequestError(error);
    }
  };

  const scheduleReconnect = (status: PaneRunStatus) => {
    if (stoppedRef.current) {
      return;
    }
    reconnectAttemptRef.current += 1;
    setPanelStatus(status);
    const delayMs = Math.min(10000, 500 * 2 ** Math.min(reconnectAttemptRef.current, 5));
    clearReconnectTimer();
    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null;
      void connectAttempt();
    }, delayMs);
  };

  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current === null) {
      return;
    }
    window.clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = null;
  };

  const syncReplayThread = (threadId: string) => {
    if (threadRef.current === threadId) {
      return;
    }
    resetReplayCursor(threadId);
  };

  const resetReplayCursor = (threadId: string) => {
    threadRef.current = threadId;
    latestEventIdRef.current = null;
    seenEventIdsRef.current = new Set();
  };

  const acceptReplayEvent = (eventId: string | undefined) => {
    if (!eventId) {
      return true;
    }
    if (seenEventIdsRef.current.has(eventId)) {
      return false;
    }
    seenEventIdsRef.current.add(eventId);
    latestEventIdRef.current = eventId;
    return true;
  };

  const retryStatusForError = (error: unknown): PaneRunStatus => {
    if (error instanceof AgentAddressUnavailableError) {
      return error.address.status === "offline" ? "offline" : "waiting";
    }
    return "reconnecting";
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

      <AgUiDisplaySurface paneId={paneId} eventState={eventState} latestErrors={latestErrors} />
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
  if (error instanceof AgentAddressUnavailableError) {
    return error.address.detail || error.message;
  }
  if (error instanceof AgUiHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "AG-UI request failed.";
}

function sameTarget(left: TargetConfig, right: TargetConfig): boolean {
  return (
    left.label === right.label &&
    left.url === right.url &&
    left.threadId === right.threadId &&
    JSON.stringify(left.source ?? { kind: "manual" }) ===
      JSON.stringify(right.source ?? { kind: "manual" })
  );
}

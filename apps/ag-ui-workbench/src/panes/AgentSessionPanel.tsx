import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import { BadgeCheck, Eraser, Eye, EyeOff, PanelRightOpen, Play, RefreshCw, Trash2, X } from "lucide-react";

import {
  AgUiHttpError,
  bindLastAgUiThread,
  buildConnectInput,
  buildRunInput,
  clearLastAgUiThread,
  connectAgUi,
  detachAgUi,
  fetchCapabilities,
  runAgUi,
} from "../ag-ui/client";
import { AgentAddressUnavailableError, resolveTargetConfigForConnect } from "../ag-ui/discovery";
import { extractConnectionId, initialPaneEventState, reduceAgUiEvent, reduceHttpError, reduceParseError, type PaneEventState, type PaneRunStatus } from "../ag-ui/reducer";
import type { CapabilitiesResponse, TargetConfig } from "../ag-ui/types";
import { watchedTargetKey } from "../ag-ui/watchedTargets";
import { paneRecordOrDefault, useWorkbench } from "../workbenchContext";
import { AgUiDisplaySurface } from "./AgUiDisplaySurface";
import { CapabilityBadges } from "./CapabilityBadges";
import { TargetForm } from "./TargetForm";

interface PanelParams {
  paneId: string;
  kind: "agent";
}

export function AgentSessionPanel(props: IDockviewPanelProps<PanelParams>) {
  const {
    storage,
    watchedTargetRuntimes,
    updateTarget,
    removePaneRecord,
    setOperatorPaneId,
    watchTarget,
    unwatchTarget,
    clearWatchedTargetCache,
    openAgentPicker,
  } = useWorkbench();
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
  const displaySurfaceRef = useRef<HTMLElement | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(null);
  const [eventState, setEventState] = useState(initialPaneEventState);
  const [prompt, setPrompt] = useState("");
  const [panelStatus, setPanelStatus] = useState(eventState.status);
  const targetWatchKey = useMemo(
    () => watchedTargetKey(target),
    [target],
  );
  const watchedRecord = targetWatchKey ? storage.watchedTargets[targetWatchKey] : undefined;
  const watchedRuntime = targetWatchKey ? watchedTargetRuntimes[targetWatchKey] : undefined;
  const displayEventState = useMemo(
    () => (watchedRuntime ? mergeEventStates(watchedRuntime.eventState, eventState) : eventState),
    [eventState, watchedRuntime],
  );

  useEffect(() => {
    props.api.setTitle(target.label || paneId);
  }, [paneId, props.api, target]);

  useEffect(() => {
    if (!watchedRuntime || sameTarget(target, watchedRuntime.target)) {
      return;
    }
    updateTarget(paneId, watchedRuntime.target);
  }, [paneId, target, updateTarget, watchedRuntime]);

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

  const latestErrors = useMemo(() => displayEventState.errors.slice(-3), [displayEventState.errors]);

  const setTarget = (nextTarget: TargetConfig) => {
    if (target.source?.kind === "discovered" && !sameTarget(target, nextTarget)) {
      void clearLastAgUiThread(target).catch(() => undefined);
    }
    if (nextTarget.source?.kind === "discovered" && nextTarget.url && nextTarget.threadId) {
      void bindLastAgUiThread(nextTarget, nextTarget.threadId, "gui_view_change").catch(
        () => undefined,
      );
    }
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
    if (target.source?.kind === "discovered" && target.url && target.threadId) {
      void bindLastAgUiThread(target, target.threadId, "gui_connect").catch(() => undefined);
    }
    const key = watchTarget(target);
    setPanelStatus(watchedTargetRuntimes[key]?.status ?? "connecting");
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
    const input = buildRunInput({
      paneId,
      threadId: target.threadId,
      message: text,
      canvasSize: measureCanvasSize(displaySurfaceRef.current),
    });
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
    if (targetWatchKey && watchedRecord) {
      unwatchTarget(targetWatchKey);
      setPanelStatus("disconnected");
      return;
    }
    await stopActiveStream(true);
    setPanelStatus("disconnected");
  };

  const clearCanvas = async () => {
    setEventState(initialPaneEventState());
    if (!targetWatchKey || !watchedRecord) {
      return;
    }
    try {
      await clearWatchedTargetCache(targetWatchKey);
    } catch (error) {
      setEventState((current) =>
        reduceHttpError(current, `Clear canvas failed: ${requestErrorMessage(error)}`),
      );
    }
  };

  const closePane = async () => {
    if (target.source?.kind === "discovered" && target.url) {
      void clearLastAgUiThread(target).catch(() => undefined);
    }
    if (!watchedRecord) {
      await stopActiveStream(true);
    }
    removePaneRecord(paneId);
    props.api.close();
  };

  const moveRight = () => {
    const operator = props.containerApi.panels.find((panel) => panel.api.id !== paneId);
    props.api.moveTo({
      group: operator?.api.group ?? props.api.group,
      position: "right",
    });
  };

  const toggleOperatorMarker = () => {
    if (storage.operatorPaneId === paneId) {
      setOperatorPaneId(undefined);
      return;
    }
    setOperatorPaneId(paneId);
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
      if (!sameTarget(baseTarget, resolvedTarget)) {
        updateTarget(paneId, resolvedTarget);
      }
      const input = buildConnectInput({
        paneId,
        threadId: resolvedTarget.threadId,
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

  const retryStatusForError = (error: unknown): PaneRunStatus => {
    if (error instanceof AgentAddressUnavailableError) {
      return error.address.status === "offline" ? "offline" : "waiting";
    }
    return "reconnecting";
  };

  const visibleStatus =
    watchedRuntime?.status ?? (panelStatus === "empty" ? displayEventState.status : panelStatus);
  const isDiscoveredAgent = target.source?.kind === "discovered";
  const isOperatorPane = storage.operatorPaneId === paneId;

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
            <Eye size={15} />
          </button>
          <button title="Disconnect" data-testid={`disconnect-${paneId}`} onClick={() => void disconnect()}>
            <EyeOff size={15} />
          </button>
          <button title="Clear canvas" data-testid={`clear-canvas-${paneId}`} onClick={() => void clearCanvas()}>
            <Eraser size={15} />
          </button>
          <button
            title={isOperatorPane ? "Clear operator marker" : "Mark as operator pane"}
            data-testid={`mark-operator-${paneId}`}
            disabled={!isDiscoveredAgent}
            onClick={toggleOperatorMarker}
          >
            <BadgeCheck size={15} />
          </button>
          <button title="Move to right split" data-testid={`split-right-${paneId}`} onClick={moveRight}>
            <PanelRightOpen size={15} />
          </button>
          <button title="Close pane" data-testid={`close-${paneId}`} onClick={() => void closePane()}>
            <X size={15} />
          </button>
        </div>
      </header>

      {isOperatorPane ? (
        <div className="operator-marker" data-testid={`operator-marker-${paneId}`}>
          Operator
        </div>
      ) : null}

      <TargetForm
        paneId={paneId}
        target={target}
        onChange={setTarget}
        onChooseAgent={() => openAgentPicker({ mode: "retarget", paneId })}
      />
      <CapabilityBadges capabilities={capabilities} />
      {targetWatchKey && watchedRecord ? (
        <div className="watch-strip" data-testid={`watch-strip-${paneId}`}>
          <span>Watched</span>
          <span>{watchedRuntime?.status ?? "connecting"}</span>
        </div>
      ) : null}

      <div className="composer">
        <textarea
          data-testid={`prompt-${paneId}`}
          value={prompt}
          placeholder="Pane prompt"
          onChange={(event) => setPrompt(event.target.value)}
        />
        <button className="run-button" title="Submit AG-UI run" data-testid={`run-${paneId}`} onClick={() => void run()}>
          <Play size={16} />
          Run
        </button>
      </div>

      <AgUiDisplaySurface
        paneId={paneId}
        eventState={displayEventState}
        latestErrors={latestErrors}
        transcriptSurfaceRef={displaySurfaceRef}
      />
      <button className="danger-link" title="Remove pane" onClick={() => void closePane()}>
        <Trash2 size={13} />
        Remove
      </button>
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

function measureCanvasSize(element: HTMLElement | null): { w: number; h: number } | null {
  if (!element) {
    return null;
  }
  const rect = element.getBoundingClientRect();
  const w = Math.round(rect.width);
  const h = Math.round(rect.height);
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    return null;
  }
  return { w, h };
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

function mergeEventStates(watched: PaneEventState, local: PaneEventState): PaneEventState {
  return {
    status: local.status !== "empty" ? local.status : watched.status,
    transcript: [...watched.transcript, ...local.transcript],
    toolCalls: [...watched.toolCalls, ...local.toolCalls],
    stateSnapshot: local.stateSnapshot ?? watched.stateSnapshot,
    activity: [...watched.activity, ...local.activity].slice(-50),
    custom: [...watched.custom, ...local.custom].slice(-50),
    errors: [...watched.errors, ...local.errors],
    raw: [...watched.raw, ...local.raw].slice(-200),
  };
}

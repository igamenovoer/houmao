import { useEffect, useMemo, useRef, useState } from "react";
import type { IDockviewPanelProps } from "dockview-react";
import { BadgeCheck, Crosshair, Eraser, Eye, EyeOff, PanelRightOpen, Play, RefreshCw, Trash2, X } from "lucide-react";

import { initialPaneEventState, type PaneEventState } from "../ag-ui/reducer";
import type { TargetConfig } from "../ag-ui/types";
import { watchedTargetKey } from "../ag-ui/watchedTargets";
import type { WorkbenchRuntimeAction } from "../runtime/actions";
import { useRuntimeDispatch, useRuntimeSelector } from "../runtime/react";
import { gatewayKeyForTarget, selectPaneActiveThreadView, selectPaneAgUiRuntime } from "../runtime/selectors";
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
  const runtimeDispatch = useRuntimeDispatch();
  const resetTokenRef = useRef(record.resetToken ?? 0);
  const displaySurfaceRef = useRef<HTMLElement | null>(null);
  const [prompt, setPrompt] = useState("");
  const emptyPaneEventState = useMemo(() => initialPaneEventState(), []);
  const paneRuntime = useRuntimeSelector((state) => selectPaneAgUiRuntime(state, paneId));
  const paneEventState = paneRuntime?.eventState ?? emptyPaneEventState;
  const capabilities = paneRuntime?.capabilities ?? null;
  const targetWatchKey = useMemo(
    () => watchedTargetKey(target),
    [target],
  );
  const watchedRecord = targetWatchKey ? storage.watchedTargets[targetWatchKey] : undefined;
  const watchedRuntime = targetWatchKey ? watchedTargetRuntimes[targetWatchKey] : undefined;
  const activeThreadView = useRuntimeSelector((state) => selectPaneActiveThreadView(state, target));
  const activeGatewayKey = useMemo(() => gatewayKeyForTarget(target), [target]);
  const displayEventState = useMemo(
    () => (watchedRuntime ? mergeEventStates(watchedRuntime.eventState, paneEventState) : paneEventState),
    [paneEventState, watchedRuntime],
  );

  useEffect(() => {
    props.api.setTitle(target.label || paneId);
  }, [paneId, props.api, target]);

  useEffect(() => {
    runtimeDispatch({
      type: "pane/targetChanged",
      paneId,
      target,
    });
  }, [paneId, runtimeDispatch, target]);

  useEffect(() => {
    return () => {
      runtimeDispatch({
        type: "pane/disposed",
        paneId,
      });
    };
  }, [paneId, runtimeDispatch]);

  useEffect(() => {
    if (!activeThreadView.isEligible || !activeGatewayKey) {
      return;
    }
    runtimeDispatch({
      type: "activeThread/registerInterest",
      paneId,
      gatewayKey: activeGatewayKey,
      target,
    });
    return () => {
      runtimeDispatch({
        type: "activeThread/unregisterInterest",
        paneId,
        gatewayKey: activeGatewayKey,
      });
    };
  }, [activeGatewayKey, activeThreadView.isEligible, paneId, runtimeDispatch, target]);

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
    setPrompt("");
    runtimeDispatch({
      type: "agUi/cancelRequested",
      paneId,
      detach: true,
    });
    runtimeDispatch({
      type: "agUi/clearPaneStateRequested",
      paneId,
    });
  }, [paneId, record.resetToken, runtimeDispatch]);

  const latestErrors = useMemo(() => displayEventState.errors.slice(-3), [displayEventState.errors]);

  const setTarget = (nextTarget: TargetConfig) => {
    if (target.source?.kind === "discovered" && !sameTarget(target, nextTarget)) {
      clearActiveThreadSelection(runtimeDispatch, paneId, target);
    }
    updateTarget(paneId, nextTarget);
  };

  const refreshCapabilities = () => {
    runtimeDispatch({
      type: "agUi/capabilitiesRequested",
      paneId,
      target,
    });
  };

  const connect = async () => {
    if (activeThreadView.isEligible && activeGatewayKey && target.threadId) {
      runtimeDispatch({
        type: "activeThread/setRequested",
        paneId,
        gatewayKey: activeGatewayKey,
        target,
        threadId: target.threadId,
        source: "gui_connect",
      });
    }
    const key = watchTarget(target);
    runtimeDispatch({
      type: "pane/targetChanged",
      paneId,
      target: watchedTargetRuntimes[key]?.target ?? target,
    });
  };

  const run = () => {
    const text = prompt.trim();
    if (!text) {
      return;
    }
    setPrompt("");
    runtimeDispatch({
      type: "agUi/runRequested",
      paneId,
      message: text,
      target,
      canvasSize: measureCanvasSize(displaySurfaceRef.current),
    });
  };

  const disconnect = () => {
    if (targetWatchKey && watchedRecord) {
      unwatchTarget(targetWatchKey);
      return;
    }
    runtimeDispatch({
      type: "agUi/cancelRequested",
      paneId,
      detach: true,
    });
  };

  const clearCanvas = async () => {
    runtimeDispatch({
      type: "agUi/clearPaneStateRequested",
      paneId,
    });
    if (!targetWatchKey || !watchedRecord) {
      return;
    }
    try {
      await clearWatchedTargetCache(targetWatchKey);
    } catch (error) {
      runtimeDispatch({
        type: "agUi/requestFailed",
        paneId,
        target,
        error: `Clear canvas failed: ${requestErrorMessage(error)}`,
        receivedAt: new Date().toISOString(),
      });
    }
  };

  const closePane = () => {
    clearActiveThreadSelection(runtimeDispatch, paneId, target);
    if (!watchedRecord) {
      runtimeDispatch({
        type: "agUi/cancelRequested",
        paneId,
        detach: true,
      });
    }
    runtimeDispatch({
      type: "pane/disposed",
      paneId,
    });
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

  const markActiveThread = () => {
    if (!activeThreadView.isEligible || !activeGatewayKey || !target.threadId) {
      return;
    }
    runtimeDispatch({
      type: "activeThread/setRequested",
      paneId,
      gatewayKey: activeGatewayKey,
      target,
      threadId: target.threadId,
      source: "gui_button",
    });
  };

  const visibleStatus =
    watchedRuntime?.status ?? (paneRuntime?.status === "empty" ? displayEventState.status : paneRuntime?.status ?? "empty");
  const isDiscoveredAgent = target.source?.kind === "discovered";
  const isOperatorPane = storage.operatorPaneId === paneId;
  const activeThreadButtonClass = activeThreadView.isActive
    ? "active-thread-button active"
    : "active-thread-button";

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
            className={activeThreadButtonClass}
            title={
              activeThreadView.isActive
                ? "Active AG-UI default thread"
                : "Mark as active AG-UI default thread"
            }
            data-testid={`mark-active-thread-${paneId}`}
            disabled={!activeThreadView.isEligible}
            onClick={markActiveThread}
          >
            <Crosshair size={15} />
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
      {activeThreadView.isEligible ? (
        <div
          className={`active-thread-marker ${activeThreadView.isActive ? "active" : "idle"}`}
          data-testid={`active-thread-marker-${paneId}`}
          title={activeThreadView.error ?? undefined}
        >
          <span>{activeThreadView.isActive ? "Active thread" : "Inactive thread"}</span>
          <span>{activeThreadView.status}</span>
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

function clearActiveThreadSelection(
  dispatch: (action: WorkbenchRuntimeAction) => void,
  paneId: string,
  target: TargetConfig,
): void {
  const gatewayKey = gatewayKeyForTarget(target);
  if (!gatewayKey || !target.threadId) {
    return;
  }
  dispatch({
    type: "activeThread/clearRequested",
    paneId,
    gatewayKey,
    target,
    expectedThreadId: target.threadId,
  });
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

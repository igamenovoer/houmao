import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { DockviewReact } from "dockview-react";
import type { DockviewApi, DockviewReadyEvent, IDockviewPanel } from "dockview-react";
import { Boxes, Bug, PanelBottom, Server, TerminalSquare, Users } from "lucide-react";

import { AgentSessionPanel } from "./panes/AgentSessionPanel";
import { AgentPicker } from "./panes/AgentPicker";
import { DebugAgentPanel } from "./panes/DebugAgentPanel";
import { TmuxTabPanel } from "./panes/TmuxTabPanel";
import {
  clearActiveAgUiThread,
  connectAgUi,
  detachAgUi,
  fetchActiveAgUiThread,
  fetchCapabilities,
  runAgUi,
  setActiveAgUiThread,
} from "./ag-ui/client";
import { resolveTargetConfigForConnect, fetchDiscoveredAgents } from "./ag-ui/discovery";
import { appendCachedEvent, clearCachedEvents, loadCachedEvents } from "./ag-ui/eventCache";
import type { AgentPickerRequest, TargetConfig } from "./ag-ui/types";
import { createWatchedTargetRecord, updateWatchedTargetRecord } from "./ag-ui/watchedTargets";
import { WorkbenchRuntimeProvider } from "./runtime/react";
import { gatewayKeyForTarget, selectWatchedTargetRuntimes } from "./runtime/selectors";
import { WorkbenchRuntime, type WorkbenchRuntimeServices } from "./runtime/workbenchRuntime";
import type { WorkbenchRuntimeState } from "./runtime/state";
import { fetchTmuxSessions, fetchTmuxStatus, openTmuxAttachSocket } from "./tmux/client";
import {
  defaultDebugAgentConfig,
  defaultPanePresentationConfig,
  defaultTmuxTabConfig,
  defaultTarget,
  loadWorkbenchStorage,
  sanitizeDockviewLayout,
  saveWorkbenchStorage,
  storageSnapshotForTests,
  type DebugAgentConfig,
  type PanePresentationConfig,
  type PaneRecord,
  type TmuxTabConfig,
  type WorkbenchStorage,
} from "./storage";
import { WorkbenchProvider } from "./workbenchContext";

declare global {
  interface Window {
    __HMWB_TEST__?: {
      storage: () => WorkbenchStorage;
      closePane: (paneId: string) => boolean;
      panelIds: () => string[];
      watchedTargetKeys: () => string[];
    };
  }
}

const components = {
  session: AgentSessionPanel,
  debugAgent: DebugAgentPanel,
  tmux: TmuxTabPanel,
};

interface AgentPaneOpenOptions {
  autoConnect?: boolean;
}

export default function App() {
  const [storage, setStorage] = useState(loadWorkbenchStorage);
  const [proxyStatus, setProxyStatus] = useState("checking");
  const [pickerRequest, setPickerRequest] = useState<AgentPickerRequest | null>(null);
  const apiRef = useRef<DockviewApi | null>(null);
  const storageRef = useRef(storage);
  const watchedTargetResolvedRef = useRef<(key: string, target: TargetConfig) => void>(() => undefined);
  const runtimeRef = useRef<WorkbenchRuntime | null>(null);
  if (!runtimeRef.current) {
    const services: WorkbenchRuntimeServices = {
      fetchActiveThread: fetchActiveAgUiThread,
      setActiveThread: setActiveAgUiThread,
      clearActiveThread: clearActiveAgUiThread,
      activeThreadPollIntervalMs: 1000,
      fetchCapabilities,
      connectAgUi,
      runAgUi,
      detachAgUi,
      resolveTargetForConnect: resolveTargetConfigForConnect,
      loadCachedEvents,
      appendCachedEvent,
      clearCachedEvents,
      onWatchedTargetResolved: (key, target) => watchedTargetResolvedRef.current(key, target),
      fetchTmuxStatus,
      fetchTmuxSessions,
      fetchDiscoveredAgents,
      openTmuxAttachSocket,
      setTimeout: (handler, timeoutMs) => window.setTimeout(handler, timeoutMs),
      clearTimeout: (handle) => window.clearTimeout(handle),
    };
    runtimeRef.current = new WorkbenchRuntime(services);
  }
  const runtime = runtimeRef.current;
  const watchedTargetRuntimes = useRuntimeExternalSelector(runtime, selectWatchedTargetRuntimes);

  useEffect(() => {
    const disposeRuntime = () => {
      runtime.dispose();
    };
    window.addEventListener("beforeunload", disposeRuntime);
    return () => {
      window.removeEventListener("beforeunload", disposeRuntime);
    };
  }, [runtime]);

  window.__HMWB_TEST__ = {
    storage: storageSnapshotForTests,
    closePane: (paneId: string) => {
      const panel = apiRef.current?.getPanel(paneId);
      if (!panel) {
        return false;
      }
      panel.api.close();
      return true;
    },
    panelIds: () => apiRef.current?.panels.map((panel) => panel.api.id) ?? [],
    watchedTargetKeys: () => Object.keys(storageRef.current.watchedTargets).sort(),
  };

  const persist = useCallback((next: WorkbenchStorage) => {
    storageRef.current = next;
    saveWorkbenchStorage(next);
    setStorage(next);
  }, []);

  const updateWatchedTarget = useCallback(
    (key: string, target: TargetConfig) => {
      const current = storageRef.current;
      const existing = current.watchedTargets[key];
      if (!existing) {
        return;
      }
      persist({
        ...current,
        watchedTargets: {
          ...current.watchedTargets,
          [key]: updateWatchedTargetRecord(existing, target),
        },
      });
    },
    [persist],
  );

  useEffect(() => {
    watchedTargetResolvedRef.current = updateWatchedTarget;
  }, [updateWatchedTarget]);

  useEffect(() => {
    runtime.dispatch({
      type: "watchedTargets/snapshotReceived",
      watchedTargets: storage.watchedTargets,
    });
  }, [runtime, storage.watchedTargets]);

  const updateTarget = useCallback(
    (paneId: string, target: TargetConfig) => {
      const current = storageRef.current;
      const existing = current.panes[paneId];
      if (existing?.target.source?.kind === "discovered" && !sameTarget(existing.target, target)) {
        clearActiveForTarget(runtime, paneId, existing.target);
      }
      const nextOperatorPaneId =
        current.operatorPaneId === paneId && target.source?.kind !== "discovered"
          ? undefined
          : current.operatorPaneId;
      persist({
        ...current,
        operatorPaneId: nextOperatorPaneId,
        panes: {
          ...current.panes,
          [paneId]: {
            ...(existing ?? { paneId, kind: "agent" as const }),
            target,
          },
        },
      });
    },
    [persist, runtime],
  );

  const updateDebugAgent = useCallback(
    (paneId: string, debugAgent: DebugAgentConfig) => {
      const current = storageRef.current;
      const existing = current.panes[paneId];
      if (existing?.kind !== "debug-agent") {
        return;
      }
      persist({
        ...current,
        panes: {
          ...current.panes,
          [paneId]: {
            ...existing,
            debugAgent,
          },
        },
      });
    },
    [persist],
  );

  const updateTmuxTab = useCallback(
    (paneId: string, tmux: TmuxTabConfig) => {
      const current = storageRef.current;
      const existing = current.panes[paneId];
      if (existing?.kind !== "tmux") {
        return;
      }
      persist({
        ...current,
        panes: {
          ...current.panes,
          [paneId]: {
            ...existing,
            tmux,
          },
        },
      });
    },
    [persist],
  );

  const updatePanePresentation = useCallback(
    (paneId: string, presentation: PanePresentationConfig) => {
      const current = storageRef.current;
      const existing = current.panes[paneId];
      if (!existing) {
        return;
      }
      persist({
        ...current,
        panes: {
          ...current.panes,
          [paneId]: {
            ...existing,
            presentation,
          },
        },
      });
    },
    [persist],
  );

  const removePaneRecord = useCallback(
    (paneId: string) => {
      const current = storageRef.current;
      const nextPanes = { ...current.panes };
      delete nextPanes[paneId];
      persist({
        ...current,
        panes: nextPanes,
        operatorPaneId: current.operatorPaneId === paneId ? undefined : current.operatorPaneId,
      });
    },
    [persist],
  );

  const setOperatorPaneId = useCallback(
    (paneId: string | undefined) => {
      const current = storageRef.current;
      if (!paneId) {
        persist({ ...current, operatorPaneId: undefined });
        return;
      }
      const pane = current.panes[paneId];
      if (pane?.kind !== "agent" || pane.target.source?.kind !== "discovered") {
        return;
      }
      persist({ ...current, operatorPaneId: paneId });
    },
    [persist],
  );

  const updateDiscoveryUrl = useCallback(
    (passiveServerUrl: string) => {
      const current = storageRef.current;
      persist({
        ...current,
        discovery: {
          ...current.discovery,
          passiveServerUrl,
        },
      });
    },
    [persist],
  );

  const watchTarget = useCallback(
    (target: TargetConfig): string => {
      const record = createWatchedTargetRecord(target);
      const current = storageRef.current;
      const existing = current.watchedTargets[record.key];
      persist({
        ...current,
        watchedTargets: {
          ...current.watchedTargets,
          [record.key]: existing ? updateWatchedTargetRecord(existing, target) : record,
        },
      });
      return record.key;
    },
    [persist],
  );

  const connectPaneToTarget = useCallback(
    (paneId: string, target: TargetConfig) => {
      if (!isAutoConnectTarget(target)) {
        return;
      }
      const key = watchTarget(target);
      runtime.dispatch({
        type: "pane/targetChanged",
        paneId,
        target: watchedTargetRuntimes[key]?.target ?? target,
      });

      const gatewayKey = gatewayKeyForTarget(target);
      if (gatewayKey && target.threadId) {
        runtime.dispatch({
          type: "activeThread/setRequested",
          paneId,
          gatewayKey,
          target,
          threadId: target.threadId,
          source: "gui_connect",
        });
      }
    },
    [runtime, watchTarget, watchedTargetRuntimes],
  );

  const unwatchTarget = useCallback(
    (key: string) => {
      const current = storageRef.current;
      if (!current.watchedTargets[key]) {
        return;
      }
      const nextWatchedTargets = { ...current.watchedTargets };
      delete nextWatchedTargets[key];
      persist({
        ...current,
        watchedTargets: nextWatchedTargets,
      });
    },
    [persist],
  );

  const contextValue = useMemo(
    () => ({
      storage,
      watchedTargetRuntimes,
      updateTarget,
      updateDebugAgent,
      updateTmuxTab,
      updatePanePresentation,
      removePaneRecord,
      setOperatorPaneId,
      watchTarget,
      unwatchTarget,
      clearWatchedTargetCache: async (key: string) => {
        runtime.dispatch({ type: "watchedTarget/clearCacheRequested", key });
      },
      clearAllWatchedTargetCaches: async () => {
        runtime.dispatch({ type: "watchedTarget/clearAllCachesRequested" });
      },
      openAgentPicker: setPickerRequest,
    }),
    [
      removePaneRecord,
      runtime,
      setOperatorPaneId,
      storage,
      unwatchTarget,
      updateDebugAgent,
      updatePanePresentation,
      updateTarget,
      updateTmuxTab,
      watchTarget,
      watchedTargetRuntimes,
    ],
  );

  const saveLayout = useCallback(() => {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    const current = storageRef.current;
    persist({
      ...current,
      layout: sanitizeDockviewLayout(api.toJSON()),
    });
  }, [persist]);

  const onReady = useCallback(
    (event: DockviewReadyEvent) => {
      apiRef.current = event.api;
      event.api.onDidLayoutChange(saveLayout);
      event.api.onDidRemovePanel((panel) => {
        const existing = storageRef.current.panes[panel.api.id];
        if (existing?.kind === "agent" && existing.target.source?.kind === "discovered") {
          clearActiveForTarget(runtime, panel.api.id, existing.target);
        }
        removePaneRecord(panel.api.id);
      });
      if (storage.layout) {
        event.api.fromJSON(sanitizeDockviewLayout(storage.layout)!, { reuseExistingPanels: false });
      }
      void refreshProxyStatus();
    },
    [removePaneRecord, runtime, saveLayout, storage.layout],
  );

  const refreshProxyStatus = async () => {
    try {
      const response = await fetch("/__houmao_ag_ui_proxy/status");
      setProxyStatus(response.ok ? "loopback proxy ready" : "proxy error");
    } catch {
      setProxyStatus("proxy unavailable");
    }
  };

  const addAgentPane = (target?: TargetConfig, options: AgentPaneOpenOptions = {}) => {
    const api = apiRef.current;
    if (!api) {
      return null;
    }
    const current = storageRef.current;
    let index = current.nextAgentIndex;
    while (current.panes[`agent-${index}`] || api.getPanel(`agent-${index}`)) {
      index += 1;
    }
    const paneId = `agent-${index}`;
    const record: PaneRecord = {
      paneId,
      kind: "agent",
      target: target ?? defaultTarget(paneId, "agent"),
      presentation: defaultPanePresentationConfig(),
    };
    persist({
      ...current,
      panes: {
        ...current.panes,
        [paneId]: record,
      },
      nextAgentIndex: index + 1,
    });
    api.addPanel({
      id: paneId,
      component: "session",
      title: record.target.label,
      params: {
        paneId,
        kind: "agent",
      },
      position: dockRightPosition(api),
    });
    if (options.autoConnect && target) {
      connectPaneToTarget(paneId, record.target);
    }
    return paneId;
  };

  const addDebugAgentPane = () => {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    const current = storageRef.current;
    let index = current.nextDebugAgentIndex;
    while (current.panes[`debug-agent-${index}`] || api.getPanel(`debug-agent-${index}`)) {
      index += 1;
    }
    const paneId = `debug-agent-${index}`;
    const debugAgent = defaultDebugAgentConfig(paneId);
    const record: PaneRecord = {
      paneId,
      kind: "debug-agent",
      target: defaultTarget(paneId, "debug-agent"),
      debugAgent,
    };
    persist({
      ...current,
      panes: {
        ...current.panes,
        [paneId]: record,
      },
      nextDebugAgentIndex: index + 1,
    });
    api.addPanel({
      id: paneId,
      component: "debugAgent",
      title: record.target.label,
      params: {
        paneId,
      },
      position: dockRightPosition(api),
    });
  };

  const addTmuxPane = () => {
    const api = apiRef.current;
    if (!api) {
      return;
    }
    const current = storageRef.current;
    let index = current.nextTmuxIndex;
    while (current.panes[`tmux-${index}`] || api.getPanel(`tmux-${index}`)) {
      index += 1;
    }
    const paneId = `tmux-${index}`;
    const tmux = defaultTmuxTabConfig();
    const record: PaneRecord = {
      paneId,
      kind: "tmux",
      target: defaultTarget(paneId, "tmux"),
      tmux,
    };
    persist({
      ...current,
      panes: {
        ...current.panes,
        [paneId]: record,
      },
      nextTmuxIndex: index + 1,
    });
    api.addPanel({
      id: paneId,
      component: "tmux",
      title: `tmux ${index}`,
      params: {
        paneId,
      },
      position: dockRightPosition(api),
    });
  };

  const retargetPane = (paneId: string, target: TargetConfig, options: AgentPaneOpenOptions = {}) => {
    const current = storageRef.current;
    const existing = current.panes[paneId] ?? {
      paneId,
      kind: "agent" as const,
      target: defaultTarget(paneId, "agent"),
    };
    if (existing.target.source?.kind === "discovered" && !sameTarget(existing.target, target)) {
      clearActiveForTarget(runtime, paneId, existing.target);
    }
    const nextOperatorPaneId =
      current.operatorPaneId === paneId && target.source?.kind !== "discovered"
        ? undefined
        : current.operatorPaneId;
    persist({
      ...current,
      operatorPaneId: nextOperatorPaneId,
      panes: {
        ...current.panes,
        [paneId]: {
          ...existing,
          target,
          resetToken: (existing.resetToken ?? 0) + 1,
        },
      },
    });
    apiRef.current?.getPanel(paneId)?.api.setTitle(target.label || paneId);
    if (options.autoConnect) {
      connectPaneToTarget(paneId, target);
    }
  };

  const openPaneForWatchedTarget = (key: string) => {
    const record = storageRef.current.watchedTargets[key];
    if (!record) {
      return;
    }
    addAgentPane(record.target);
  };

  return (
    <WorkbenchRuntimeProvider runtime={runtime}>
      <WorkbenchProvider value={contextValue}>
      <main className="app-shell" data-testid="app-shell">
        <header className="topbar">
          <div className="brand">
            <Boxes size={19} />
            <div>
              <h1>Houmao AG-UI Workbench</h1>
              <span>direct protocol harness</span>
            </div>
          </div>
          <div className="toolbar">
            <span className="runtime-pill" data-testid="proxy-status">
              <Server size={14} />
              {proxyStatus}
            </span>
            <button title="Refresh proxy status" onClick={() => void refreshProxyStatus()}>
              <PanelBottom size={15} />
            </button>
            <button title="Show discovered Houmao agents" data-testid="open-agent-picker" onClick={() => setPickerRequest({ mode: "new-pane" })}>
              <Users size={15} />
              Agents
            </button>
            <button title="Open debug agent pane" data-testid="add-debug-agent-pane" onClick={addDebugAgentPane}>
              <Bug size={15} />
              Debug Agent
            </button>
            <button title="Open tmux tab" data-testid="add-tmux-pane" onClick={addTmuxPane}>
              <TerminalSquare size={15} />
              tmux
            </button>
          </div>
        </header>
        <section className="dockview-shell dockview-theme-dark" data-testid="dockview-shell">
          <DockviewReact
            components={components}
            onReady={onReady}
            disableFloatingGroups
            dndStrategy="pointer"
            getTabContextMenuItems={() => []}
            getTabGroupChipContextMenuItems={() => []}
            noPanelsOverlay="emptyGroup"
          />
        </section>
        <AgentPicker
          request={pickerRequest}
          passiveServerUrl={storage.discovery.passiveServerUrl}
          panes={storage.panes}
          watchedTargets={storage.watchedTargets}
          watchedTargetRuntimes={watchedTargetRuntimes}
          onPassiveServerUrlChange={updateDiscoveryUrl}
          onCreateBlankPane={() => addAgentPane()}
          onCreatePane={addAgentPane}
          onRetargetPane={retargetPane}
          onWatchTarget={watchTarget}
          onUnwatchTarget={unwatchTarget}
          onOpenWatchedTarget={openPaneForWatchedTarget}
          onClose={() => setPickerRequest(null)}
        />
      </main>
      </WorkbenchProvider>
    </WorkbenchRuntimeProvider>
  );
}

function clearActiveForTarget(runtime: WorkbenchRuntime, paneId: string, target: TargetConfig): void {
  const gatewayKey = gatewayKeyForTarget(target);
  if (!gatewayKey || !target.threadId) {
    return;
  }
  runtime.dispatch({
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

function isAutoConnectTarget(target: TargetConfig): boolean {
  return (
    target.source?.kind === "discovered" &&
    Boolean(target.threadId) &&
    target.url.trim().length > 0
  );
}

function dockRightPosition(api: DockviewApi):
  | {
      referencePanel: IDockviewPanel;
      direction: "right";
    }
  | undefined {
  const referencePanel = api.panels[api.panels.length - 1];
  return referencePanel
    ? {
        referencePanel,
      direction: "right",
    }
    : undefined;
}

function useRuntimeExternalSelector<T>(
  runtime: WorkbenchRuntime,
  selector: (state: WorkbenchRuntimeState) => T,
): T {
  const getSnapshot = useCallback(() => selector(runtime.snapshot()), [runtime, selector]);
  const subscribe = useCallback((listener: () => void) => runtime.subscribe(listener), [runtime]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

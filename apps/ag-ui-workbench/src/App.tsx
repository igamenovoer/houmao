import { useCallback, useMemo, useRef, useState } from "react";
import { DockviewReact } from "dockview-react";
import type { DockviewApi, DockviewReadyEvent, IDockviewPanel } from "dockview-react";
import { Boxes, Bug, PanelBottom, Plus, Server, Users } from "lucide-react";

import { AgentSessionPanel } from "./panes/AgentSessionPanel";
import { AgentPicker } from "./panes/AgentPicker";
import { DebugAgentPanel } from "./panes/DebugAgentPanel";
import type { AgentPickerRequest, TargetConfig } from "./ag-ui/types";
import { useWatchedTargets } from "./ag-ui/useWatchedTargets";
import { createWatchedTargetRecord, updateWatchedTargetRecord } from "./ag-ui/watchedTargets";
import {
  defaultDebugAgentConfig,
  defaultTarget,
  loadWorkbenchStorage,
  sanitizeDockviewLayout,
  saveWorkbenchStorage,
  storageSnapshotForTests,
  type DebugAgentConfig,
  type PaneRecord,
  type WorkbenchStorage,
} from "./storage";
import { WorkbenchProvider } from "./workbenchContext";

const OPERATOR_PANEL_ID = "operator";

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
};

export default function App() {
  const [storage, setStorage] = useState(loadWorkbenchStorage);
  const [proxyStatus, setProxyStatus] = useState("checking");
  const [pickerRequest, setPickerRequest] = useState<AgentPickerRequest | null>(null);
  const apiRef = useRef<DockviewApi | null>(null);
  const storageRef = useRef(storage);

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

  const watchedTargets = useWatchedTargets({
    watchedTargets: storage.watchedTargets,
    onResolvedTarget: updateWatchedTarget,
  });

  const updateTarget = useCallback(
    (paneId: string, target: TargetConfig) => {
      const current = storageRef.current;
      const existing = current.panes[paneId];
      persist({
        ...current,
        panes: {
          ...current.panes,
          [paneId]: {
            ...(existing ?? { paneId, kind: paneId === OPERATOR_PANEL_ID ? "operator" : "agent" }),
            target,
          },
        },
      });
    },
    [persist],
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

  const removePaneRecord = useCallback(
    (paneId: string) => {
      if (paneId === OPERATOR_PANEL_ID) {
        return;
      }
      const current = storageRef.current;
      const nextPanes = { ...current.panes };
      delete nextPanes[paneId];
      persist({ ...current, panes: nextPanes });
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
      watchedTargetRuntimes: watchedTargets.runtimes,
      updateTarget,
      updateDebugAgent,
      removePaneRecord,
      watchTarget,
      unwatchTarget,
      clearWatchedTargetCache: watchedTargets.clearTargetCache,
      clearAllWatchedTargetCaches: watchedTargets.clearAllCaches,
      openAgentPicker: setPickerRequest,
    }),
    [
      removePaneRecord,
      storage,
      unwatchTarget,
      updateDebugAgent,
      updateTarget,
      watchTarget,
      watchedTargets.clearAllCaches,
      watchedTargets.clearTargetCache,
      watchedTargets.runtimes,
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
        if (panel.api.id === OPERATOR_PANEL_ID) {
          queueMicrotask(() => ensureOperatorPanelIfEmpty(event.api));
          return;
        }
        removePaneRecord(panel.api.id);
        queueMicrotask(() => ensureOperatorPanelIfEmpty(event.api));
      });
      if (storage.layout) {
        event.api.fromJSON(sanitizeDockviewLayout(storage.layout)!, { reuseExistingPanels: false });
      }
      ensureOperatorPanelIfEmpty(event.api);
      void refreshProxyStatus();
    },
    [removePaneRecord, saveLayout, storage.layout],
  );

  const refreshProxyStatus = async () => {
    try {
      const response = await fetch("/__houmao_ag_ui_proxy/status");
      setProxyStatus(response.ok ? "loopback proxy ready" : "proxy error");
    } catch {
      setProxyStatus("proxy unavailable");
    }
  };

  const addAgentPane = (target?: TargetConfig) => {
    const api = apiRef.current;
    if (!api) {
      return;
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
      position: {
        referencePanel: OPERATOR_PANEL_ID,
        direction: "right",
      },
    });
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
      position: {
        referencePanel: OPERATOR_PANEL_ID,
        direction: "right",
      },
    });
  };

  const retargetPane = (paneId: string, target: TargetConfig) => {
    const current = storageRef.current;
    const existing = current.panes[paneId] ?? {
      paneId,
      kind: paneId === OPERATOR_PANEL_ID ? "operator" : "agent",
      target: defaultTarget(paneId, paneId === OPERATOR_PANEL_ID ? "operator" : "agent"),
    };
    persist({
      ...current,
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
  };

  const openPaneForWatchedTarget = (key: string) => {
    const record = storageRef.current.watchedTargets[key];
    if (!record) {
      return;
    }
    addAgentPane(record.target);
  };

  return (
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
            <button className="primary" title="Add agent pane" data-testid="add-agent-pane" onClick={() => addAgentPane()}>
              <Plus size={16} />
              Agent Pane
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
          watchedTargetRuntimes={watchedTargets.runtimes}
          onPassiveServerUrlChange={updateDiscoveryUrl}
          onCreatePane={addAgentPane}
          onRetargetPane={retargetPane}
          onWatchTarget={watchTarget}
          onUnwatchTarget={unwatchTarget}
          onOpenWatchedTarget={openPaneForWatchedTarget}
          onClose={() => setPickerRequest(null)}
        />
      </main>
    </WorkbenchProvider>
  );
}

function ensureOperatorPanel(api: DockviewApi): IDockviewPanel {
  const existing = api.getPanel(OPERATOR_PANEL_ID);
  if (existing) {
    return existing;
  }
  return api.addPanel({
    id: OPERATOR_PANEL_ID,
    component: "session",
    title: "Operator",
    params: {
      paneId: OPERATOR_PANEL_ID,
      kind: "operator",
    },
  });
}

function ensureOperatorPanelIfEmpty(api: DockviewApi): IDockviewPanel | undefined {
  if (api.totalPanels > 0) {
    return api.getPanel(OPERATOR_PANEL_ID);
  }
  return ensureOperatorPanel(api);
}

import { useCallback, useMemo, useRef, useState } from "react";
import { DockviewReact } from "dockview-react";
import type { DockviewApi, DockviewReadyEvent, IDockviewPanel } from "dockview-react";
import { Boxes, PanelBottom, Plus, Server, Users } from "lucide-react";

import { AgentSessionPanel } from "./panes/AgentSessionPanel";
import { AgentPicker } from "./panes/AgentPicker";
import type { AgentPickerRequest, TargetConfig } from "./ag-ui/types";
import {
  defaultTarget,
  loadWorkbenchStorage,
  sanitizeDockviewLayout,
  saveWorkbenchStorage,
  storageSnapshotForTests,
  type PaneRecord,
  type WorkbenchStorage,
} from "./storage";
import { WorkbenchProvider } from "./workbenchContext";

const OPERATOR_PANEL_ID = "operator";

declare global {
  interface Window {
    __HMWB_TEST__?: {
      storage: () => WorkbenchStorage;
    };
  }
}

const components = {
  session: AgentSessionPanel,
};

export default function App() {
  const [storage, setStorage] = useState(loadWorkbenchStorage);
  const [proxyStatus, setProxyStatus] = useState("checking");
  const [pickerRequest, setPickerRequest] = useState<AgentPickerRequest | null>(null);
  const apiRef = useRef<DockviewApi | null>(null);
  const storageRef = useRef(storage);

  window.__HMWB_TEST__ = {
    storage: storageSnapshotForTests,
  };

  const persist = useCallback((next: WorkbenchStorage) => {
    storageRef.current = next;
    saveWorkbenchStorage(next);
    setStorage(next);
  }, []);

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

  const contextValue = useMemo(
    () => ({
      storage,
      updateTarget,
      removePaneRecord,
      openAgentPicker: setPickerRequest,
    }),
    [removePaneRecord, storage, updateTarget],
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
          queueMicrotask(() => ensureOperatorPanel(event.api));
          return;
        }
        removePaneRecord(panel.api.id);
      });
      if (storage.layout) {
        event.api.fromJSON(sanitizeDockviewLayout(storage.layout)!, { reuseExistingPanels: false });
      }
      ensureOperatorPanel(event.api);
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
          onPassiveServerUrlChange={updateDiscoveryUrl}
          onCreatePane={addAgentPane}
          onRetargetPane={retargetPane}
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

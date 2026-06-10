import { createContext, useContext } from "react";

import { defaultDebugAgentConfig, defaultTarget, defaultTmuxTabConfig } from "./storage";
import type { DebugAgentConfig, PaneRecord, TmuxTabConfig, WorkbenchStorage } from "./storage";
import type { WatchedTargetRuntime } from "./ag-ui/useWatchedTargets";
import type { AgentPickerRequest, TargetConfig } from "./ag-ui/types";

export interface WorkbenchContextValue {
  storage: WorkbenchStorage;
  watchedTargetRuntimes: Record<string, WatchedTargetRuntime>;
  updateTarget: (paneId: string, target: TargetConfig) => void;
  updateDebugAgent: (paneId: string, debugAgent: DebugAgentConfig) => void;
  updateTmuxTab: (paneId: string, tmux: TmuxTabConfig) => void;
  removePaneRecord: (paneId: string) => void;
  setOperatorPaneId: (paneId: string | undefined) => void;
  watchTarget: (target: TargetConfig) => string;
  unwatchTarget: (key: string) => void;
  clearWatchedTargetCache: (key: string) => Promise<void>;
  clearAllWatchedTargetCaches: () => Promise<void>;
  openAgentPicker: (request: AgentPickerRequest) => void;
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

export const WorkbenchProvider = WorkbenchContext.Provider;

export function useWorkbench(): WorkbenchContextValue {
  const value = useContext(WorkbenchContext);
  if (!value) {
    throw new Error("Workbench context is unavailable.");
  }
  return value;
}

export function paneRecordOrDefault(storage: WorkbenchStorage, paneId: string, kind: PaneRecord["kind"]): PaneRecord {
  return (
    storage.panes[paneId] ?? {
      paneId,
      kind,
      target: defaultTarget(paneId, kind),
      debugAgent: kind === "debug-agent" ? defaultDebugAgentConfig(paneId) : undefined,
      tmux: kind === "tmux" ? defaultTmuxTabConfig() : undefined,
    }
  );
}

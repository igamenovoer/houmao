import { createContext, useContext } from "react";

import { defaultTarget } from "./storage";
import type { PaneRecord, WorkbenchStorage } from "./storage";
import type { AgentPickerRequest, TargetConfig } from "./ag-ui/types";

export interface WorkbenchContextValue {
  storage: WorkbenchStorage;
  updateTarget: (paneId: string, target: TargetConfig) => void;
  removePaneRecord: (paneId: string) => void;
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
    }
  );
}

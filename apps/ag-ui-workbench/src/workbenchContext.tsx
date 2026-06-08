import { createContext, useContext } from "react";

import type { PaneRecord, WorkbenchStorage } from "./storage";
import type { TargetConfig } from "./ag-ui/types";

export interface WorkbenchContextValue {
  storage: WorkbenchStorage;
  updateTarget: (paneId: string, target: TargetConfig) => void;
  removePaneRecord: (paneId: string) => void;
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
      target: {
        label: kind === "operator" ? "Operator" : paneId.replace(/-/g, " "),
        url: "",
        threadId: kind === "operator" ? "operator-thread" : `${paneId}-thread`,
      },
    }
  );
}

import type { TargetConfig } from "../ag-ui/types";
import type { GatewayKey } from "./actions";
import {
  gatewayKeyForTarget,
  type ActiveThreadRuntimeState,
  type TmuxInventoryRuntimeState,
  type PaneAgUiRuntimeState,
  type TmuxPaneRuntimeState,
  type WatchedTargetRuntimeState,
  type WorkbenchRuntimeState,
} from "./state";

export interface PaneActiveThreadView {
  gatewayKey: GatewayKey | null;
	  runtime: ActiveThreadRuntimeState | null;
	  isEligible: boolean;
	  isUnsupported: boolean;
	  isActive: boolean;
	  canMutate: boolean;
	  status: string;
	  label: string;
	  error?: string;
	}

export function selectGatewayActiveThread(
  state: WorkbenchRuntimeState,
  gatewayKey: GatewayKey | null,
): ActiveThreadRuntimeState | null {
  if (!gatewayKey) {
    return null;
  }
  return state.activeThreads[gatewayKey] ?? null;
}

export function selectPaneActiveThreadView(
  state: WorkbenchRuntimeState,
  target: TargetConfig,
): PaneActiveThreadView {
  const gatewayKey = gatewayKeyForTarget(target);
	  const runtime = selectGatewayActiveThread(state, gatewayKey);
	  const isEligible = target.source?.kind === "discovered" && Boolean(target.url && target.threadId);
	  const isUnsupported = runtime?.status === "unsupported";
	  const activeThreadId = runtime?.activeThread.threadId ?? null;
	  const isActive = isEligible && !isUnsupported && activeThreadId === target.threadId;
	  const canMutate = isEligible && !isUnsupported;
	  return {
	    gatewayKey,
	    runtime,
	    isEligible,
	    isUnsupported,
	    isActive,
	    canMutate,
	    status: runtime?.status ?? "idle",
	    label: isUnsupported ? "Active-thread unsupported" : isActive ? "Active thread" : "Inactive thread",
	    error: runtime?.error,
	  };
	}

export function selectPaneAgUiRuntime(
  state: WorkbenchRuntimeState,
  paneId: string,
): PaneAgUiRuntimeState | null {
  return state.paneAgUi[paneId] ?? null;
}

export function selectWatchedTargetRuntimes(
  state: WorkbenchRuntimeState,
): Record<string, WatchedTargetRuntimeState> {
  return state.watchedTargets;
}

export function selectWatchedTargetRuntime(
  state: WorkbenchRuntimeState,
  key: string | null,
): WatchedTargetRuntimeState | null {
  if (!key) {
    return null;
  }
  return state.watchedTargets[key] ?? null;
}

export function selectTmuxPaneRuntime(
  state: WorkbenchRuntimeState,
  paneId: string,
): TmuxPaneRuntimeState | null {
  const pane = state.tmuxPanes[paneId];
  if (!pane) {
    return null;
  }
  const inventory = state.tmuxInventory;
  return {
    ...pane,
    bridgeStatus: inventory.bridgeStatus,
    sessions: inventory.sessions,
    agents: inventory.agents,
    loading: inventory.loading,
    tmuxError: inventory.tmuxError,
    discoveryError: inventory.discoveryError,
    lastReceivedAt: inventory.lastReceivedAt ?? pane.lastReceivedAt,
  };
}

export function selectTmuxInventory(state: WorkbenchRuntimeState): TmuxInventoryRuntimeState {
  return state.tmuxInventory;
}

export function selectRuntimeErrors(state: WorkbenchRuntimeState) {
  return state.errors;
}

export { gatewayKeyForTarget };

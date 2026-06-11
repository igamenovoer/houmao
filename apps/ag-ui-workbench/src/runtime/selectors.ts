import type { TargetConfig } from "../ag-ui/types";
import type { GatewayKey } from "./actions";
import {
  gatewayKeyForTarget,
  type ActiveThreadRuntimeState,
  type PaneAgUiRuntimeState,
  type TmuxPaneRuntimeState,
  type WatchedTargetRuntimeState,
  type WorkbenchRuntimeState,
} from "./state";

export interface PaneActiveThreadView {
  gatewayKey: GatewayKey | null;
  runtime: ActiveThreadRuntimeState | null;
  isEligible: boolean;
  isActive: boolean;
  status: string;
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
  const activeThreadId = runtime?.activeThread.threadId ?? null;
  const isActive = isEligible && activeThreadId === target.threadId;
  return {
    gatewayKey,
    runtime,
    isEligible,
    isActive,
    status: runtime?.status ?? "idle",
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
  return state.tmuxPanes[paneId] ?? null;
}

export function selectRuntimeErrors(state: WorkbenchRuntimeState) {
  return state.errors;
}

export { gatewayKeyForTarget };

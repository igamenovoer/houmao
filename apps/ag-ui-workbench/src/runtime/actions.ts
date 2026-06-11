import type {
  ActiveThreadSource,
  AgUiThreadDestination,
} from "../ag-ui/client";
import type {
  AgUiEvent,
  CapabilitiesResponse,
  DiscoveredAgentSummary,
  RawTimelineEntry,
  TargetConfig,
} from "../ag-ui/types";
import type { PaneRunStatus } from "../ag-ui/reducer";
import type { WatchedTargetRecord } from "../ag-ui/watchedTargets";
import type { PresentationSessionView } from "../shared/workbenchProtocol";
import type { TmuxAttachMode, TmuxBridgeStatus, TmuxSessionRow } from "../tmux/client";

export type GatewayKey = string;

export type RuntimeStreamKind = "connect" | "run";
export type RuntimeTerminalOutputSink = (data: string) => void;

export type WorkbenchRuntimeAction =
  | {
      type: "pane/targetChanged";
      paneId: string;
      target: TargetConfig;
    }
  | {
      type: "pane/disposed";
      paneId: string;
    }
  | {
      type: "presentationSessions/snapshotReceived";
      sessions: PresentationSessionView[];
      receivedAt: string;
    }
  | {
      type: "presentationSession/created";
      session: PresentationSessionView;
      receivedAt: string;
    }
  | {
      type: "presentationSession/disposed";
      sessionId: string;
      paneId?: string | null;
      receivedAt: string;
    }
  | {
      type: "agUi/capabilitiesRequested";
      paneId: string;
      target: TargetConfig;
    }
  | {
      type: "agUi/capabilitiesSucceeded";
      paneId: string;
      target: TargetConfig;
      capabilities: CapabilitiesResponse;
      receivedAt: string;
    }
  | {
      type: "agUi/capabilitiesFailed";
      paneId: string;
      target: TargetConfig;
      error: string;
      receivedAt: string;
    }
  | {
      type: "agUi/connectRequested";
      paneId: string;
      target: TargetConfig;
    }
  | {
      type: "agUi/runRequested";
      paneId: string;
      target: TargetConfig;
      message: string;
    }
  | {
      type: "agUi/cancelRequested";
      paneId: string;
      detach: boolean;
    }
  | {
      type: "agUi/streamOpened";
      paneId: string;
      target: TargetConfig;
      streamKind: RuntimeStreamKind;
      receivedAt: string;
    }
  | {
      type: "agUi/streamFinished";
      paneId: string;
      target: TargetConfig;
      streamKind: RuntimeStreamKind;
      status: PaneRunStatus;
      receivedAt: string;
    }
  | {
      type: "agUi/eventReceived";
      paneId: string;
      target: TargetConfig;
      streamKind: RuntimeStreamKind;
      event: AgUiEvent;
      raw: RawTimelineEntry;
      connectionId?: string | null;
    }
  | {
      type: "agUi/parseError";
      paneId: string;
      target: TargetConfig;
      streamKind: RuntimeStreamKind;
      raw: RawTimelineEntry;
      error?: string;
    }
  | {
      type: "agUi/requestFailed";
      paneId: string;
      target: TargetConfig;
      streamKind?: RuntimeStreamKind;
      error: string;
      receivedAt: string;
    }
  | {
      type: "agUi/clearPaneStateRequested";
      paneId: string;
    }
  | {
      type: "watchedTargets/snapshotReceived";
      watchedTargets: Record<string, WatchedTargetRecord>;
    }
  | {
      type: "watchedTarget/statusChanged";
      key: string;
      target: TargetConfig;
      status: PaneRunStatus;
      error?: string;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/targetResolved";
      key: string;
      target: TargetConfig;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/cacheLoaded";
      key: string;
      target: TargetConfig;
      records: Array<{ event: AgUiEvent; raw: RawTimelineEntry; sequence: number }>;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/eventReceived";
      key: string;
      target: TargetConfig;
      event: AgUiEvent;
      raw: RawTimelineEntry;
      connectionId?: string | null;
    }
  | {
      type: "watchedTarget/parseError";
      key: string;
      target: TargetConfig;
      raw: RawTimelineEntry;
      error?: string;
    }
  | {
      type: "watchedTarget/requestFailed";
      key: string;
      target: TargetConfig;
      error: string;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/removed";
      key: string;
    }
  | {
      type: "watchedTarget/clearCacheRequested";
      key: string;
    }
  | {
      type: "watchedTarget/clearCacheSucceeded";
      key: string;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/clearCacheFailed";
      key: string;
      error: string;
      receivedAt: string;
    }
  | {
      type: "watchedTarget/clearAllCachesRequested";
    }
  | {
      type: "watchedTarget/clearAllCachesSucceeded";
      receivedAt: string;
    }
  | {
      type: "watchedTarget/clearAllCachesFailed";
      error: string;
      receivedAt: string;
    }
  | {
      type: "tmux/registerInventoryInterest";
      paneId: string;
      passiveServerUrl: string;
    }
  | {
      type: "tmux/unregisterInventoryInterest";
      paneId: string;
    }
  | {
      type: "tmux/refreshRequested";
      paneId: string;
      passiveServerUrl: string;
    }
  | {
      type: "tmux/refreshSucceeded";
      paneId: string;
      bridgeStatus: TmuxBridgeStatus;
      sessions: TmuxSessionRow[];
      agents: DiscoveredAgentSummary[];
      receivedAt: string;
    }
  | {
      type: "tmux/refreshFailed";
      paneId: string;
      tmuxError?: string;
      discoveryError?: string;
      bridgeStatus?: TmuxBridgeStatus | null;
      sessions?: TmuxSessionRow[];
      agents?: DiscoveredAgentSummary[];
      receivedAt: string;
    }
  | {
      type: "tmux/registerOutputSink";
      paneId: string;
      sink: RuntimeTerminalOutputSink;
    }
  | {
      type: "tmux/unregisterOutputSink";
      paneId: string;
    }
  | {
      type: "tmux/attachRequested";
      paneId: string;
      sessionName: string;
      mode: TmuxAttachMode;
      cols: number;
      rows: number;
    }
  | {
      type: "tmux/attachStarted";
      paneId: string;
      sessionName: string;
      mode: TmuxAttachMode;
      receivedAt: string;
    }
  | {
      type: "tmux/attachSucceeded";
      paneId: string;
      sessionName: string;
      mode: TmuxAttachMode;
      receivedAt: string;
    }
  | {
      type: "tmux/attachFailed";
      paneId: string;
      error: string;
      receivedAt: string;
    }
  | {
      type: "tmux/attachDisconnected";
      paneId: string;
      receivedAt: string;
    }
  | {
      type: "tmux/detachRequested";
      paneId: string;
    }
  | {
      type: "tmux/inputRequested";
      paneId: string;
      data: string;
    }
  | {
      type: "tmux/resizeRequested";
      paneId: string;
      cols: number;
      rows: number;
    }
  | {
      type: "activeThread/registerInterest";
      paneId: string;
      gatewayKey: GatewayKey;
      target: TargetConfig;
    }
  | {
      type: "activeThread/unregisterInterest";
      paneId: string;
      gatewayKey: GatewayKey;
    }
  | {
      type: "activeThread/pollStarted";
      gatewayKey: GatewayKey;
    }
  | {
      type: "activeThread/pollSucceeded";
      gatewayKey: GatewayKey;
      target: TargetConfig;
      activeThread: AgUiThreadDestination;
      receivedAt: string;
    }
	  | {
	      type: "activeThread/pollFailed";
	      gatewayKey: GatewayKey;
	      error: string;
	      receivedAt: string;
	    }
	  | {
	      type: "activeThread/unsupported";
	      gatewayKey: GatewayKey;
	      target: TargetConfig;
	      error: string;
	      receivedAt: string;
	    }
	  | {
	      type: "activeThread/setRequested";
      paneId: string;
      gatewayKey: GatewayKey;
      target: TargetConfig;
      threadId: string;
      source: ActiveThreadSource;
    }
  | {
      type: "activeThread/setSucceeded";
      paneId: string;
      gatewayKey: GatewayKey;
      target: TargetConfig;
      activeThread: AgUiThreadDestination;
      receivedAt: string;
    }
  | {
      type: "activeThread/clearRequested";
      paneId: string;
      gatewayKey: GatewayKey;
      target: TargetConfig;
      expectedThreadId?: string;
    }
  | {
      type: "activeThread/clearSucceeded";
      paneId: string;
      gatewayKey: GatewayKey;
      target: TargetConfig;
      activeThread: AgUiThreadDestination | null;
      receivedAt: string;
    }
  | {
      type: "activeThread/mutationFailed";
      paneId: string;
      gatewayKey: GatewayKey;
      error: string;
      receivedAt: string;
    }
  | {
      type: "runtime/error";
      error: string;
      receivedAt: string;
    }
  | {
      type: "runtime/noop";
    };

export type ActiveThreadRegisterInterestAction = Extract<
  WorkbenchRuntimeAction,
  { type: "activeThread/registerInterest" }
>;
export type ActiveThreadSetRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "activeThread/setRequested" }
>;
export type ActiveThreadClearRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "activeThread/clearRequested" }
>;

export type WatchedTargetsSnapshotReceivedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "watchedTargets/snapshotReceived" }
>;
export type WatchedTargetClearCacheRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "watchedTarget/clearCacheRequested" }
>;
export type AgUiRunRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "agUi/runRequested" }
>;
export type AgUiConnectRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "agUi/connectRequested" }
>;
export type AgUiCapabilitiesRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "agUi/capabilitiesRequested" }
>;
export type AgUiCancelRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "agUi/cancelRequested" }
>;
export type TmuxRefreshRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "tmux/refreshRequested" }
>;
export type TmuxRegisterInventoryInterestAction = Extract<
  WorkbenchRuntimeAction,
  { type: "tmux/registerInventoryInterest" }
>;
export type TmuxAttachRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "tmux/attachRequested" }
>;
export type TmuxInputRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "tmux/inputRequested" }
>;
export type TmuxResizeRequestedAction = Extract<
  WorkbenchRuntimeAction,
  { type: "tmux/resizeRequested" }
>;

export function isActiveThreadSetRequested(
  action: WorkbenchRuntimeAction,
): action is ActiveThreadSetRequestedAction {
  return action.type === "activeThread/setRequested";
}

export function isActiveThreadClearRequested(
  action: WorkbenchRuntimeAction,
): action is ActiveThreadClearRequestedAction {
  return action.type === "activeThread/clearRequested";
}

export function isWatchedTargetsSnapshotReceived(
  action: WorkbenchRuntimeAction,
): action is WatchedTargetsSnapshotReceivedAction {
  return action.type === "watchedTargets/snapshotReceived";
}

export function isAgUiCapabilitiesRequested(
  action: WorkbenchRuntimeAction,
): action is AgUiCapabilitiesRequestedAction {
  return action.type === "agUi/capabilitiesRequested";
}

export function isAgUiConnectRequested(
  action: WorkbenchRuntimeAction,
): action is AgUiConnectRequestedAction {
  return action.type === "agUi/connectRequested";
}

export function isAgUiRunRequested(
  action: WorkbenchRuntimeAction,
): action is AgUiRunRequestedAction {
  return action.type === "agUi/runRequested";
}

export function isAgUiCancelRequested(
  action: WorkbenchRuntimeAction,
): action is AgUiCancelRequestedAction {
  return action.type === "agUi/cancelRequested";
}

export function isTmuxRefreshRequested(
  action: WorkbenchRuntimeAction,
): action is TmuxRefreshRequestedAction {
  return action.type === "tmux/refreshRequested";
}

export function isTmuxRegisterInventoryInterest(
  action: WorkbenchRuntimeAction,
): action is TmuxRegisterInventoryInterestAction {
  return action.type === "tmux/registerInventoryInterest";
}

export function isTmuxAttachRequested(
  action: WorkbenchRuntimeAction,
): action is TmuxAttachRequestedAction {
  return action.type === "tmux/attachRequested";
}

export function isTmuxInputRequested(
  action: WorkbenchRuntimeAction,
): action is TmuxInputRequestedAction {
  return action.type === "tmux/inputRequested";
}

export function isTmuxResizeRequested(
  action: WorkbenchRuntimeAction,
): action is TmuxResizeRequestedAction {
  return action.type === "tmux/resizeRequested";
}

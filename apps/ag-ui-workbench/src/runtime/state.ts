import type { AgUiThreadDestination } from "../ag-ui/client";
import {
  initialPaneEventState,
  reduceAgUiEvent,
  reduceHttpError,
  reduceParseError,
  type PaneEventState,
  type PaneRunStatus,
} from "../ag-ui/reducer";
import { normalizeAgUiTarget } from "../ag-ui/target";
import type { CapabilitiesResponse, DiscoveredAgentSummary, TargetConfig } from "../ag-ui/types";
import type { WatchedTargetRecord } from "../ag-ui/watchedTargets";
import type { PresentationSessionView } from "../shared/workbenchProtocol";
import type { TmuxAttachMode, TmuxBridgeStatus, TmuxSessionRow } from "../tmux/client";
import type { GatewayKey, RuntimeStreamKind, WorkbenchRuntimeAction } from "./actions";

export type ActiveThreadRuntimeStatus =
  | "idle"
	  | "polling"
	  | "ready"
	  | "setting"
	  | "clearing"
	  | "unsupported"
	  | "error";

export interface ActiveThreadRuntimeState {
  gatewayKey: GatewayKey;
  target: TargetConfig;
  interestedPaneIds: string[];
  status: ActiveThreadRuntimeStatus;
  activeThread: AgUiThreadDestination;
  lastReceivedAt?: string;
  error?: string;
}

export interface PaneAgUiRuntimeState {
  paneId: string;
  target?: TargetConfig;
  status: PaneRunStatus;
  eventState: PaneEventState;
  capabilities: CapabilitiesResponse | null;
  connectionId: string | null;
  activeStream?: RuntimeStreamKind;
  lastReceivedAt?: string;
  error?: string;
}

export interface WatchedTargetRuntimeState {
  key: string;
  target: TargetConfig;
  status: PaneRunStatus;
  eventState: PaneEventState;
  cacheLoaded: boolean;
  connectionId: string | null;
  lastReceivedAt?: string;
  error?: string;
}

export type TmuxAttachState =
  | "unattached"
  | "attaching"
  | "attached"
  | "disconnected"
  | "error";

export interface TmuxPaneRuntimeState {
  paneId: string;
  bridgeStatus: TmuxBridgeStatus | null;
  sessions: TmuxSessionRow[];
  agents: DiscoveredAgentSummary[];
  loading: boolean;
  tmuxError?: string;
  discoveryError?: string;
  attachState: TmuxAttachState;
  activeSession: string | null;
  mode: TmuxAttachMode;
  lastReceivedAt?: string;
}

export interface TmuxInventoryRuntimeState {
  bridgeStatus: TmuxBridgeStatus | null;
  sessions: TmuxSessionRow[];
  agents: DiscoveredAgentSummary[];
  loading: boolean;
  tmuxError?: string;
  discoveryError?: string;
  lastReceivedAt?: string;
  passiveServerUrl: string;
  interestedPaneIds: string[];
}

export interface RuntimeErrorEntry {
  message: string;
  receivedAt: string;
}

export interface PresentationSessionRuntimeState {
  sessions: Record<string, PresentationSessionView>;
  lastReceivedAt?: string;
}

export interface WorkbenchRuntimeState {
  activeThreads: Record<GatewayKey, ActiveThreadRuntimeState>;
  paneAgUi: Record<string, PaneAgUiRuntimeState>;
  watchedTargets: Record<string, WatchedTargetRuntimeState>;
  tmuxInventory: TmuxInventoryRuntimeState;
  tmuxPanes: Record<string, TmuxPaneRuntimeState>;
  presentationSessions: PresentationSessionRuntimeState;
  errors: RuntimeErrorEntry[];
}

const EMPTY_THREAD: AgUiThreadDestination = { status: "empty" };

export const initialRuntimeState: WorkbenchRuntimeState = {
  activeThreads: {},
  paneAgUi: {},
  watchedTargets: {},
  tmuxInventory: {
    bridgeStatus: null,
    sessions: [],
    agents: [],
    loading: false,
    passiveServerUrl: "",
    interestedPaneIds: [],
  },
  tmuxPanes: {},
  presentationSessions: {
    sessions: {},
  },
  errors: [],
};

export function reduceRuntimeState(
  state: WorkbenchRuntimeState,
  action: WorkbenchRuntimeAction,
): WorkbenchRuntimeState {
  switch (action.type) {
    case "pane/targetChanged":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
      }));
    case "pane/disposed": {
      const nextPaneAgUi = { ...state.paneAgUi };
      const nextTmuxPanes = { ...state.tmuxPanes };
      delete nextPaneAgUi[action.paneId];
      delete nextTmuxPanes[action.paneId];
      return {
        ...state,
        paneAgUi: nextPaneAgUi,
        tmuxPanes: nextTmuxPanes,
        tmuxInventory: {
          ...state.tmuxInventory,
          interestedPaneIds: removeValue(state.tmuxInventory.interestedPaneIds, action.paneId),
        },
        presentationSessions: removePresentationSessionsForPane(
          state.presentationSessions,
          action.paneId,
        ),
      };
    }
    case "presentationSessions/snapshotReceived":
      return {
        ...state,
        presentationSessions: {
          sessions: Object.fromEntries(
            action.sessions.map((session) => [session.sessionId, session]),
          ),
          lastReceivedAt: action.receivedAt,
        },
      };
    case "presentationSession/created":
      return {
        ...state,
        presentationSessions: {
          sessions: {
            ...state.presentationSessions.sessions,
            [action.session.sessionId]: action.session,
          },
          lastReceivedAt: action.receivedAt,
        },
      };
    case "presentationSession/disposed": {
      const nextSessions = { ...state.presentationSessions.sessions };
      if (action.sessionId) {
        delete nextSessions[action.sessionId];
      }
      if (action.paneId) {
        for (const [sessionId, session] of Object.entries(nextSessions)) {
          if (session.paneId === action.paneId) {
            delete nextSessions[sessionId];
          }
        }
      }
      return {
        ...state,
        presentationSessions: {
          sessions: nextSessions,
          lastReceivedAt: action.receivedAt,
        },
      };
    }
    case "agUi/capabilitiesRequested":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "connecting",
        error: undefined,
      }));
    case "agUi/capabilitiesSucceeded":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: current.status === "connecting" ? "connected" : current.status,
        capabilities: action.capabilities,
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
    case "agUi/capabilitiesFailed":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "error",
        eventState: reduceHttpError(current.eventState, action.error),
        error: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "agUi/connectRequested":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "connecting",
        activeStream: "connect",
        error: undefined,
      }));
    case "agUi/runRequested":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "running",
        activeStream: "run",
        error: undefined,
      }));
    case "agUi/cancelRequested":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        status: action.detach ? "disconnected" : current.status,
        activeStream: undefined,
        connectionId: action.detach ? null : current.connectionId,
      }));
    case "agUi/streamOpened":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: action.streamKind === "run" ? "running" : "connected",
        activeStream: action.streamKind,
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
    case "agUi/streamFinished":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: action.status,
        activeStream: undefined,
        connectionId: action.streamKind === "connect" ? null : current.connectionId,
        lastReceivedAt: action.receivedAt,
      }));
    case "agUi/eventReceived":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: current.status === "empty" ? "connected" : current.status,
        activeStream: action.streamKind,
        connectionId: action.connectionId ?? current.connectionId,
        eventState: reduceAgUiEvent(current.eventState, action.event, action.raw),
        lastReceivedAt: action.raw.receivedAt,
      }));
    case "agUi/parseError":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "error",
        eventState: reduceParseError(current.eventState, action.raw),
        error: action.error ?? action.raw.parseError,
        lastReceivedAt: action.raw.receivedAt,
      }));
    case "agUi/requestFailed":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        target: action.target,
        status: "error",
        activeStream: undefined,
        eventState: reduceHttpError(current.eventState, action.error),
        error: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "agUi/clearPaneStateRequested":
      return updatePaneAgUiState(state, action.paneId, (current) => ({
        ...current,
        eventState: initialPaneEventState(),
        error: undefined,
      }));
    case "watchedTargets/snapshotReceived":
      return reconcileWatchedTargets(state, action.watchedTargets);
    case "watchedTarget/statusChanged":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        status: action.status,
        error: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "watchedTarget/targetResolved":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
    case "watchedTarget/cacheLoaded":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        cacheLoaded: true,
        eventState: action.records.reduce(
          (eventState, record) => reduceAgUiEvent(eventState, record.event, record.raw),
          initialPaneEventState(),
        ),
        lastReceivedAt: action.receivedAt,
      }));
    case "watchedTarget/eventReceived":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        status: current.status === "empty" ? "connected" : current.status,
        connectionId: action.connectionId ?? current.connectionId,
        eventState: reduceAgUiEvent(current.eventState, action.event, action.raw),
        lastReceivedAt: action.raw.receivedAt,
      }));
    case "watchedTarget/parseError":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        status: "error",
        eventState: reduceParseError(current.eventState, action.raw),
        error: action.error ?? action.raw.parseError,
        lastReceivedAt: action.raw.receivedAt,
      }));
    case "watchedTarget/requestFailed":
      return updateWatchedTargetState(state, action.key, action.target, (current) => ({
        ...current,
        target: action.target,
        status: "error",
        eventState: reduceHttpError(current.eventState, action.error),
        error: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "watchedTarget/removed": {
      const nextWatchedTargets = { ...state.watchedTargets };
      delete nextWatchedTargets[action.key];
      return { ...state, watchedTargets: nextWatchedTargets };
    }
    case "watchedTarget/clearCacheRequested":
      return updateExistingWatchedTargetState(state, action.key, (current) => ({
        ...current,
        eventState: initialPaneEventState(),
        error: undefined,
      }));
    case "watchedTarget/clearCacheSucceeded":
      return updateExistingWatchedTargetState(state, action.key, (current) => ({
        ...current,
        eventState: initialPaneEventState(),
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
    case "watchedTarget/clearCacheFailed":
      return updateExistingWatchedTargetState(state, action.key, (current) => ({
        ...current,
        status: "error",
        error: action.error,
        eventState: reduceHttpError(current.eventState, action.error),
        lastReceivedAt: action.receivedAt,
      }));
    case "watchedTarget/clearAllCachesRequested":
      return {
        ...state,
        watchedTargets: Object.fromEntries(
          Object.entries(state.watchedTargets).map(([key, runtime]) => [
            key,
            {
              ...runtime,
              eventState: initialPaneEventState(),
              error: undefined,
            },
          ]),
        ),
      };
    case "watchedTarget/clearAllCachesSucceeded":
      return {
        ...state,
        watchedTargets: Object.fromEntries(
          Object.entries(state.watchedTargets).map(([key, runtime]) => [
            key,
            {
              ...runtime,
              eventState: initialPaneEventState(),
              lastReceivedAt: action.receivedAt,
              error: undefined,
            },
          ]),
        ),
      };
    case "watchedTarget/clearAllCachesFailed":
      return {
        ...state,
        errors: [...state.errors, { message: action.error, receivedAt: action.receivedAt }].slice(-20),
      };
    case "tmux/registerInventoryInterest":
      return updateTmuxPaneState(
        {
          ...state,
          tmuxInventory: {
            ...state.tmuxInventory,
            passiveServerUrl: action.passiveServerUrl,
            interestedPaneIds: addUnique(state.tmuxInventory.interestedPaneIds, action.paneId),
          },
        },
        action.paneId,
        (current) => current,
      );
    case "tmux/unregisterInventoryInterest":
      return {
        ...state,
        tmuxInventory: {
          ...state.tmuxInventory,
          interestedPaneIds: removeValue(state.tmuxInventory.interestedPaneIds, action.paneId),
        },
      };
    case "tmux/refreshRequested":
      return updateTmuxPaneState(
        {
          ...state,
          tmuxInventory: {
            ...state.tmuxInventory,
            passiveServerUrl: action.passiveServerUrl,
            loading: true,
            tmuxError: undefined,
            discoveryError: undefined,
          },
        },
        action.paneId,
        (current) => ({
          ...current,
          loading: true,
          tmuxError: undefined,
          discoveryError: undefined,
        }),
      );
    case "tmux/refreshSucceeded":
      return updateTmuxPaneState(
        {
          ...state,
          tmuxInventory: {
            ...state.tmuxInventory,
            loading: false,
            bridgeStatus: action.bridgeStatus,
            sessions: action.sessions,
            agents: action.agents,
            tmuxError:
              action.bridgeStatus.status === "unavailable" ? action.bridgeStatus.detail : undefined,
            discoveryError: undefined,
            lastReceivedAt: action.receivedAt,
          },
        },
        action.paneId,
        (current) => ({
          ...current,
          loading: false,
          bridgeStatus: action.bridgeStatus,
          sessions: action.sessions,
          agents: action.agents,
          tmuxError:
            action.bridgeStatus.status === "unavailable" ? action.bridgeStatus.detail : undefined,
          discoveryError: undefined,
          lastReceivedAt: action.receivedAt,
        }),
      );
    case "tmux/refreshFailed": {
      const bridgeStatus = action.bridgeStatus ?? state.tmuxInventory.bridgeStatus;
      const sessions = action.sessions ?? state.tmuxInventory.sessions;
      const agents = action.agents ?? state.tmuxInventory.agents;
      return updateTmuxPaneState(
        {
          ...state,
          tmuxInventory: {
            ...state.tmuxInventory,
            loading: false,
            bridgeStatus,
            sessions,
            agents,
            tmuxError: action.tmuxError,
            discoveryError: action.discoveryError,
            lastReceivedAt: action.receivedAt,
          },
        },
        action.paneId,
        (current) => ({
          ...current,
          loading: false,
          bridgeStatus,
          sessions,
          agents,
          tmuxError: action.tmuxError,
          discoveryError: action.discoveryError,
          lastReceivedAt: action.receivedAt,
        }),
      );
    }
    case "tmux/registerOutputSink":
    case "tmux/unregisterOutputSink":
      return state;
    case "tmux/attachRequested":
    case "tmux/attachStarted":
      return updateTmuxPaneState(state, action.paneId, (current) => ({
        ...current,
        attachState: "attaching",
        activeSession: action.sessionName,
        mode: action.mode,
        tmuxError: undefined,
        lastReceivedAt: "receivedAt" in action ? action.receivedAt : current.lastReceivedAt,
      }));
    case "tmux/attachSucceeded":
      return updateTmuxPaneState(state, action.paneId, (current) => ({
        ...current,
        attachState: "attached",
        activeSession: action.sessionName,
        mode: action.mode,
        tmuxError: undefined,
        lastReceivedAt: action.receivedAt,
      }));
    case "tmux/attachFailed":
      return updateTmuxPaneState(state, action.paneId, (current) => ({
        ...current,
        attachState: "error",
        tmuxError: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "tmux/attachDisconnected":
    case "tmux/detachRequested":
      return updateTmuxPaneState(state, action.paneId, (current) => ({
        ...current,
        attachState:
          current.attachState === "attached" || current.attachState === "attaching"
            ? "disconnected"
            : current.attachState,
        lastReceivedAt: "receivedAt" in action ? action.receivedAt : current.lastReceivedAt,
      }));
    case "tmux/inputRequested":
    case "tmux/resizeRequested":
      return state;
	    case "activeThread/registerInterest": {
	      const existing = state.activeThreads[action.gatewayKey];
	      const targetChanged = existing ? !sameActiveThreadTarget(existing.target, action.target) : false;
	      const interestedPaneIds = addUnique(existing?.interestedPaneIds ?? [], action.paneId);
	      return {
	        ...state,
        activeThreads: {
          ...state.activeThreads,
	          [action.gatewayKey]: {
	            gatewayKey: action.gatewayKey,
	            target: action.target,
	            activeThread: targetChanged ? EMPTY_THREAD : existing?.activeThread ?? EMPTY_THREAD,
	            status: targetChanged ? "idle" : existing?.status ?? "idle",
	            interestedPaneIds,
	            lastReceivedAt: targetChanged ? undefined : existing?.lastReceivedAt,
	            error: targetChanged ? undefined : existing?.error,
	          },
	        },
	      };
    }
    case "activeThread/unregisterInterest": {
      const existing = state.activeThreads[action.gatewayKey];
      if (!existing) {
        return state;
      }
      return {
        ...state,
        activeThreads: {
          ...state.activeThreads,
          [action.gatewayKey]: {
            ...existing,
            interestedPaneIds: existing.interestedPaneIds.filter((paneId) => paneId !== action.paneId),
          },
        },
      };
    }
	    case "activeThread/pollStarted":
	      return updateActiveThreadState(state, action.gatewayKey, (current) => ({
	        ...current,
	        status:
	          current.status === "setting" ||
	          current.status === "clearing" ||
	          current.status === "unsupported" ||
	          current.status === "ready"
	            ? current.status
	            : "polling",
	      }));
    case "activeThread/pollSucceeded":
      return updateActiveThreadState(state, action.gatewayKey, (current) => ({
        ...current,
        target: action.target,
        activeThread: action.activeThread,
        status: "ready",
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
	    case "activeThread/pollFailed":
	      return updateActiveThreadState(state, action.gatewayKey, (current) => ({
	        ...current,
	        status: current.status === "unsupported" ? current.status : "error",
	        lastReceivedAt: action.receivedAt,
	        error: current.status === "unsupported" ? current.error : action.error,
	      }));
	    case "activeThread/unsupported":
	      return updateActiveThreadState(state, action.gatewayKey, (current) => ({
	        ...current,
	        target: action.target,
	        activeThread: EMPTY_THREAD,
	        status: "unsupported",
	        lastReceivedAt: action.receivedAt,
	        error: action.error,
	      }));
	    case "activeThread/setRequested":
	      return updateOrCreateActiveThreadState(state, action.gatewayKey, action.target, (current) =>
	        current.status === "unsupported"
	          ? current
	          : {
	              ...current,
	              target: action.target,
	              status: "setting",
	              error: undefined,
	            },
	      );
    case "activeThread/setSucceeded":
      return updateOrCreateActiveThreadState(state, action.gatewayKey, action.target, (current) => ({
        ...current,
        target: action.target,
        activeThread: action.activeThread,
        status: "ready",
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
	    case "activeThread/clearRequested":
	      return updateOrCreateActiveThreadState(state, action.gatewayKey, action.target, (current) =>
	        current.status === "unsupported"
	          ? current
	          : {
	              ...current,
	              target: action.target,
	              status: "clearing",
	              error: undefined,
	            },
	      );
    case "activeThread/clearSucceeded":
      return updateOrCreateActiveThreadState(state, action.gatewayKey, action.target, (current) => ({
        ...current,
        target: action.target,
        activeThread: action.activeThread ?? current.activeThread,
        status: "ready",
        lastReceivedAt: action.receivedAt,
        error: undefined,
      }));
    case "activeThread/mutationFailed":
      return updateActiveThreadState(state, action.gatewayKey, (current) => ({
        ...current,
        status: "error",
        error: action.error,
        lastReceivedAt: action.receivedAt,
      }));
    case "runtime/error":
      return {
        ...state,
        errors: [...state.errors, { message: action.error, receivedAt: action.receivedAt }].slice(-20),
      };
    case "runtime/noop":
      return state;
    default:
      return exhaustive(action);
  }
}

export function gatewayKeyForTarget(target: TargetConfig): GatewayKey | null {
  try {
    return normalizeAgUiTarget(target).baseUrl;
  } catch {
    return null;
  }
}

function reconcileWatchedTargets(
  state: WorkbenchRuntimeState,
  records: Record<string, WatchedTargetRecord>,
): WorkbenchRuntimeState {
  const nextWatchedTargets: Record<string, WatchedTargetRuntimeState> = {};
  for (const [key, record] of Object.entries(records)) {
    const existing = state.watchedTargets[key];
    nextWatchedTargets[key] = {
      key,
      target: record.target,
      status: existing?.status ?? "connecting",
      eventState: existing?.eventState ?? initialPaneEventState(),
      cacheLoaded: existing?.cacheLoaded ?? false,
      connectionId: existing?.connectionId ?? null,
      lastReceivedAt: existing?.lastReceivedAt,
      error: existing?.error,
    };
  }
  return {
    ...state,
    watchedTargets: nextWatchedTargets,
  };
}

function updatePaneAgUiState(
  state: WorkbenchRuntimeState,
  paneId: string,
  update: (current: PaneAgUiRuntimeState) => PaneAgUiRuntimeState,
): WorkbenchRuntimeState {
  const current =
    state.paneAgUi[paneId] ??
    ({
      paneId,
      status: "empty",
      eventState: initialPaneEventState(),
      capabilities: null,
      connectionId: null,
    } satisfies PaneAgUiRuntimeState);
  return {
    ...state,
    paneAgUi: {
      ...state.paneAgUi,
      [paneId]: update(current),
    },
  };
}

function updateWatchedTargetState(
  state: WorkbenchRuntimeState,
  key: string,
  target: TargetConfig,
  update: (current: WatchedTargetRuntimeState) => WatchedTargetRuntimeState,
): WorkbenchRuntimeState {
  const current =
    state.watchedTargets[key] ??
    ({
      key,
      target,
      status: "connecting",
      eventState: initialPaneEventState(),
      cacheLoaded: false,
      connectionId: null,
    } satisfies WatchedTargetRuntimeState);
  return {
    ...state,
    watchedTargets: {
      ...state.watchedTargets,
      [key]: update(current),
    },
  };
}

function updateExistingWatchedTargetState(
  state: WorkbenchRuntimeState,
  key: string,
  update: (current: WatchedTargetRuntimeState) => WatchedTargetRuntimeState,
): WorkbenchRuntimeState {
  const current = state.watchedTargets[key];
  if (!current) {
    return state;
  }
  return {
    ...state,
    watchedTargets: {
      ...state.watchedTargets,
      [key]: update(current),
    },
  };
}

function updateTmuxPaneState(
  state: WorkbenchRuntimeState,
  paneId: string,
  update: (current: TmuxPaneRuntimeState) => TmuxPaneRuntimeState,
): WorkbenchRuntimeState {
  const current =
    state.tmuxPanes[paneId] ??
    ({
      paneId,
      bridgeStatus: null,
      sessions: [],
      agents: [],
      loading: false,
      attachState: "unattached",
      activeSession: null,
      mode: "read-write",
    } satisfies TmuxPaneRuntimeState);
  return {
    ...state,
    tmuxPanes: {
      ...state.tmuxPanes,
      [paneId]: update(current),
    },
  };
}

function updateActiveThreadState(
  state: WorkbenchRuntimeState,
  gatewayKey: GatewayKey,
  update: (current: ActiveThreadRuntimeState) => ActiveThreadRuntimeState,
): WorkbenchRuntimeState {
  const existing = state.activeThreads[gatewayKey];
  if (!existing) {
    return state;
  }
  return {
    ...state,
    activeThreads: {
      ...state.activeThreads,
      [gatewayKey]: update(existing),
    },
  };
}

function updateOrCreateActiveThreadState(
  state: WorkbenchRuntimeState,
  gatewayKey: GatewayKey,
  target: TargetConfig,
  update: (current: ActiveThreadRuntimeState) => ActiveThreadRuntimeState,
): WorkbenchRuntimeState {
  const current =
    state.activeThreads[gatewayKey] ??
    ({
      gatewayKey,
      target,
      interestedPaneIds: [],
      status: "idle",
      activeThread: EMPTY_THREAD,
    } satisfies ActiveThreadRuntimeState);
  return {
    ...state,
    activeThreads: {
      ...state.activeThreads,
      [gatewayKey]: update(current),
    },
  };
}

function sameActiveThreadTarget(left: TargetConfig, right: TargetConfig): boolean {
  return (
    left.label === right.label &&
    left.url === right.url &&
    left.threadId === right.threadId &&
    JSON.stringify(left.source ?? { kind: "manual" }) ===
      JSON.stringify(right.source ?? { kind: "manual" })
  );
}

function addUnique(values: string[], value: string): string[] {
  if (values.includes(value)) {
    return values;
  }
  return [...values, value];
}

function removeValue(values: string[], value: string): string[] {
  return values.filter((candidate) => candidate !== value);
}

function removePresentationSessionsForPane(
  state: PresentationSessionRuntimeState,
  paneId: string,
): PresentationSessionRuntimeState {
  const sessions = { ...state.sessions };
  for (const [sessionId, session] of Object.entries(sessions)) {
    if (session.paneId === paneId) {
      delete sessions[sessionId];
    }
  }
  return {
    ...state,
    sessions,
  };
}

function exhaustive(value: never): WorkbenchRuntimeState {
  throw new Error(`Unhandled workbench runtime action: ${JSON.stringify(value)}`);
}

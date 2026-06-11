import { BehaviorSubject, Subject, Subscription, scan } from "rxjs";

import type {
  ActiveThreadSource,
  AgUiThreadDestination,
  StreamHandlers,
} from "../ag-ui/client";
import type { CachedAgUiEventRecord } from "../ag-ui/eventCache";
import type {
  CapabilitiesResponse,
  DiscoveredAgentSummary,
  RunAgentInput,
  TargetConfig,
} from "../ag-ui/types";
import type {
  TmuxBridgeStatus,
  TmuxSessionsResponse,
} from "../tmux/client";
import type { WorkbenchRuntimeAction } from "./actions";
import { initialRuntimeState, reduceRuntimeState, type WorkbenchRuntimeState } from "./state";
import { installActiveThreadEffects } from "./effects/activeThreadEffects";
import { installAgUiEffects } from "./effects/agUiEffects";
import { installDiscoveryEffects } from "./effects/discoveryEffects";
import { installStorageEffects } from "./effects/storageEffects";
import { installTmuxEffects } from "./effects/tmuxEffects";
import { installWatchedTargetEffects } from "./effects/watchedTargetEffects";

export interface WorkbenchRuntimeServices {
  fetchActiveThread: (
    target: TargetConfig,
    signal?: AbortSignal,
  ) => Promise<AgUiThreadDestination>;
  setActiveThread: (
    target: TargetConfig,
    threadId: string,
    source: ActiveThreadSource,
  ) => Promise<AgUiThreadDestination>;
  clearActiveThread: (
    target: TargetConfig,
    expectedThreadId?: string,
  ) => Promise<AgUiThreadDestination | null>;
  activeThreadPollIntervalMs?: number;
  fetchCapabilities?: (target: TargetConfig, signal?: AbortSignal) => Promise<CapabilitiesResponse>;
  connectAgUi?: (
    target: TargetConfig,
    input: RunAgentInput,
    handlers: StreamHandlers,
    signal?: AbortSignal,
  ) => Promise<void>;
  runAgUi?: (
    target: TargetConfig,
    input: RunAgentInput,
    handlers: StreamHandlers,
    signal?: AbortSignal,
  ) => Promise<void>;
  detachAgUi?: (target: TargetConfig, connectionId: string | null | undefined) => Promise<void>;
  resolveTargetForConnect?: (target: TargetConfig, signal?: AbortSignal) => Promise<TargetConfig>;
  loadCachedEvents?: (targetKey: string) => Promise<CachedAgUiEventRecord[]>;
  appendCachedEvent?: (record: CachedAgUiEventRecord) => Promise<void>;
  clearCachedEvents?: (targetKey?: string) => Promise<void>;
  onWatchedTargetResolved?: (key: string, target: TargetConfig) => void;
  fetchTmuxStatus?: (signal?: AbortSignal) => Promise<TmuxBridgeStatus>;
  fetchTmuxSessions?: (signal?: AbortSignal) => Promise<TmuxSessionsResponse>;
  fetchDiscoveredAgents?: (
    passiveServerUrl: string,
    signal?: AbortSignal,
  ) => Promise<DiscoveredAgentSummary[]>;
  openTmuxAttachSocket?: () => WebSocket;
  setTimeout?: (handler: () => void, timeoutMs: number) => number;
  clearTimeout?: (handle: number) => void;
}

export class WorkbenchRuntime {
  private readonly m_actions = new Subject<WorkbenchRuntimeAction>();
  private readonly m_state = new BehaviorSubject<WorkbenchRuntimeState>(initialRuntimeState);
  private readonly m_subscriptions = new Subscription();
  private m_disposed = false;

  readonly actions$ = this.m_actions.asObservable();
  readonly state$ = this.m_state.asObservable();

  constructor(private readonly m_services: WorkbenchRuntimeServices) {
    this.m_subscriptions.add(
      this.m_actions
        .pipe(scan(reduceRuntimeState, initialRuntimeState))
        .subscribe((state) => this.m_state.next(state)),
    );
    this.m_subscriptions.add(installActiveThreadEffects(this, this.m_services));
    this.m_subscriptions.add(installDiscoveryEffects(this));
    this.m_subscriptions.add(installAgUiEffects(this, this.m_services));
    this.m_subscriptions.add(installWatchedTargetEffects(this, this.m_services));
    this.m_subscriptions.add(installTmuxEffects(this, this.m_services));
    this.m_subscriptions.add(installStorageEffects(this));
  }

  dispatch(action: WorkbenchRuntimeAction): void {
    if (this.m_disposed) {
      return;
    }
    this.m_actions.next(action);
  }

  snapshot(): WorkbenchRuntimeState {
    return this.m_state.getValue();
  }

  subscribe(listener: () => void): () => void {
    let initialEmission = true;
    const subscription = this.m_state.subscribe(() => {
      if (initialEmission) {
        initialEmission = false;
        return;
      }
      listener();
    });
    return () => subscription.unsubscribe();
  }

  dispose(): void {
    if (this.m_disposed) {
      return;
    }
    this.m_disposed = true;
    this.m_subscriptions.unsubscribe();
    this.m_actions.complete();
    this.m_state.complete();
  }
}

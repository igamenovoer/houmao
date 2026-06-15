import { Subscription } from "rxjs";

import { buildConnectInput, AgUiHttpError } from "../../ag-ui/client";
import { AgentAddressUnavailableError } from "../../ag-ui/discovery";
import { cachedRecordId, type CachedAgUiEventRecord } from "../../ag-ui/eventCache";
import { extractConnectionId, type PaneRunStatus } from "../../ag-ui/reducer";
import type { TargetConfig } from "../../ag-ui/types";
import type { WatchedTargetRecord } from "../../ag-ui/watchedTargets";
import type { WorkbenchRuntimeAction } from "../actions";
import type { WorkbenchRuntime, WorkbenchRuntimeServices } from "../workbenchRuntime";

interface WatchController {
  target: TargetConfig;
  stopped: boolean;
  abort: AbortController | null;
  connectionId: string | null;
  reconnectTimer: number | null;
  reconnectAttempt: number;
  nextSequence: number;
}

export function installWatchedTargetEffects(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
): Subscription {
  const subscriptions = new Subscription();
  const controllers = new Map<string, WatchController>();
  const setTimer = services.setTimeout ?? ((handler, timeoutMs) => window.setTimeout(handler, timeoutMs));
  const clearTimer = services.clearTimeout ?? ((handle) => window.clearTimeout(handle));

  subscriptions.add(
    runtime.actions$.subscribe((action) => {
      switch (action.type) {
        case "watchedTargets/snapshotReceived":
          reconcileWatchers(action.watchedTargets);
          break;
        case "watchedTarget/clearCacheRequested":
          void clearTargetCache(action.key);
          break;
        case "watchedTarget/clearAllCachesRequested":
          void clearAllCaches();
          break;
        default:
          break;
      }
    }),
  );

  subscriptions.add(() => {
    for (const key of [...controllers.keys()]) {
      stopWatcher(key, true);
    }
  });

  return subscriptions;

  function reconcileWatchers(records: Record<string, WatchedTargetRecord>): void {
    const activeKeys = new Set(Object.keys(records));
    for (const record of Object.values(records)) {
      startOrUpdateWatcher(record);
    }
    for (const key of [...controllers.keys()]) {
      if (!activeKeys.has(key)) {
        stopWatcher(key, true);
      }
    }
  }

  function startOrUpdateWatcher(record: WatchedTargetRecord): void {
    const existing = controllers.get(record.key);
    if (existing) {
      existing.target = record.target;
      runtime.dispatch({
        type: "watchedTarget/statusChanged",
        key: record.key,
        target: record.target,
        status: runtime.snapshot().watchedTargets[record.key]?.status ?? "connecting",
        receivedAt: nowUtc(),
      });
      return;
    }
    const controller: WatchController = {
      target: record.target,
      stopped: false,
      abort: null,
      connectionId: null,
      reconnectTimer: null,
      reconnectAttempt: 0,
      nextSequence: 1,
    };
    controllers.set(record.key, controller);
    void initializeWatcher(record.key, controller);
  }

  async function initializeWatcher(key: string, controller: WatchController): Promise<void> {
    try {
      const cached = await loadCachedEvents(key);
      if (controller.stopped) {
        return;
      }
      controller.nextSequence = Math.max(0, ...cached.map((record) => record.sequence)) + 1;
      runtime.dispatch({
        type: "watchedTarget/cacheLoaded",
        key,
        target: controller.target,
        records: cached.map((record) => ({
          event: record.event,
          raw: record.raw,
          sequence: record.sequence,
        })),
        receivedAt: nowUtc(),
      });
    } catch (error) {
      runtime.dispatch({
        type: "watchedTarget/requestFailed",
        key,
        target: controller.target,
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
    void connectAttempt(key);
  }

  async function connectAttempt(key: string): Promise<void> {
    const controller = controllers.get(key);
    if (!controller || controller.stopped) {
      return;
    }
    if (!services.connectAgUi) {
      runtime.dispatch({
        type: "watchedTarget/requestFailed",
        key,
        target: controller.target,
        error: "AG-UI connect service is unavailable.",
        receivedAt: nowUtc(),
      });
      return;
    }
    const abort = new AbortController();
    controller.abort = abort;
    const baseTarget = controller.target;
    runtime.dispatch({
      type: "watchedTarget/statusChanged",
      key,
      target: baseTarget,
      status: controller.reconnectAttempt > 0 ? "reconnecting" : "connecting",
      receivedAt: nowUtc(),
    });
    try {
      const resolvedTarget = await resolveTargetForConnect(baseTarget, abort.signal);
      if (abort.signal.aborted || controller.stopped) {
        return;
      }
      controller.target = resolvedTarget;
      if (!sameTarget(baseTarget, resolvedTarget)) {
        services.onWatchedTargetResolved?.(key, resolvedTarget);
        runtime.dispatch({
          type: "watchedTarget/targetResolved",
          key,
          target: resolvedTarget,
          receivedAt: nowUtc(),
        });
      }
      void services.fetchCapabilities?.(resolvedTarget, abort.signal).catch(() => undefined);
      const input = buildConnectInput({
        paneId: key,
        threadId: resolvedTarget.threadId,
      });
      await services.connectAgUi(
        resolvedTarget,
        input,
        {
          onOpen: () => {
            controller.reconnectAttempt = 0;
            runtime.dispatch({
              type: "watchedTarget/statusChanged",
              key,
              target: resolvedTarget,
              status: "connected",
              receivedAt: nowUtc(),
            });
          },
          onRaw: () => undefined,
          onParseError: (raw) => {
            runtime.dispatch({
              type: "watchedTarget/parseError",
              key,
              target: resolvedTarget,
              raw,
              error: raw.parseError,
            });
          },
          onEvent: (event, raw) => {
            if (abort.signal.aborted || controller.stopped) {
              return;
            }
            const connectionId = extractConnectionId(event);
            if (connectionId) {
              controller.connectionId = connectionId;
            }
            const sequence = controller.nextSequence;
            controller.nextSequence += 1;
            const cachedRecord: CachedAgUiEventRecord = {
              id: cachedRecordId(key, sequence),
              targetKey: key,
              threadId: resolvedTarget.threadId,
              sequence,
              receivedAt: raw.receivedAt,
              sseEventId: raw.sseEventId,
              event,
              raw,
            };
            void services.appendCachedEvent?.(cachedRecord).catch(() => undefined);
            runtime.dispatch({
              type: "watchedTarget/eventReceived",
              key,
              target: resolvedTarget,
              event,
              raw,
              connectionId: controller.connectionId,
            });
          },
        },
        abort.signal,
      );
      if (!abort.signal.aborted && !controller.stopped) {
        controller.connectionId = null;
        if (resolvedTarget.source?.kind === "discovered") {
          scheduleReconnect(key, "reconnecting");
        } else {
          runtime.dispatch({
            type: "watchedTarget/statusChanged",
            key,
            target: resolvedTarget,
            status: "disconnected",
            receivedAt: nowUtc(),
          });
        }
      }
    } catch (error) {
      if (abort.signal.aborted || controller.stopped) {
        return;
      }
      if (baseTarget.source?.kind === "discovered") {
        const status = retryStatusForError(error);
        if (!(error instanceof AgentAddressUnavailableError)) {
          runtime.dispatch({
            type: "watchedTarget/requestFailed",
            key,
            target: baseTarget,
            error: requestErrorMessage(error),
            receivedAt: nowUtc(),
          });
        }
        scheduleReconnect(key, status);
        return;
      }
      runtime.dispatch({
        type: "watchedTarget/requestFailed",
        key,
        target: baseTarget,
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
  }

  function scheduleReconnect(key: string, status: PaneRunStatus): void {
    const controller = controllers.get(key);
    if (!controller || controller.stopped) {
      return;
    }
    controller.reconnectAttempt += 1;
    runtime.dispatch({
      type: "watchedTarget/statusChanged",
      key,
      target: controller.target,
      status,
      receivedAt: nowUtc(),
    });
    const delayMs = Math.min(10000, 500 * 2 ** Math.min(controller.reconnectAttempt, 5));
    if (controller.reconnectTimer !== null) {
      clearTimer(controller.reconnectTimer);
    }
    controller.reconnectTimer = setTimer(() => {
      controller.reconnectTimer = null;
      void connectAttempt(key);
    }, delayMs);
  }

  function stopWatcher(key: string, detach: boolean): void {
    const controller = controllers.get(key);
    if (!controller) {
      return;
    }
    controller.stopped = true;
    if (controller.reconnectTimer !== null) {
      clearTimer(controller.reconnectTimer);
      controller.reconnectTimer = null;
    }
    controller.abort?.abort();
    controller.abort = null;
    controllers.delete(key);
    if (detach) {
      void services.detachAgUi?.(controller.target, controller.connectionId).catch(() => undefined);
    }
    runtime.dispatch({ type: "watchedTarget/removed", key });
  }

  async function clearTargetCache(key: string): Promise<void> {
    try {
      await services.clearCachedEvents?.(key);
      const controller = controllers.get(key);
      if (controller) {
        controller.nextSequence = 1;
      }
      runtime.dispatch({
        type: "watchedTarget/clearCacheSucceeded",
        key,
        receivedAt: nowUtc(),
      });
    } catch (error) {
      runtime.dispatch({
        type: "watchedTarget/clearCacheFailed",
        key,
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
  }

  async function clearAllCaches(): Promise<void> {
    try {
      await services.clearCachedEvents?.();
      for (const controller of controllers.values()) {
        controller.nextSequence = 1;
      }
      runtime.dispatch({
        type: "watchedTarget/clearAllCachesSucceeded",
        receivedAt: nowUtc(),
      });
    } catch (error) {
      runtime.dispatch({
        type: "watchedTarget/clearAllCachesFailed",
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
  }

  async function loadCachedEvents(key: string): Promise<CachedAgUiEventRecord[]> {
    return services.loadCachedEvents ? services.loadCachedEvents(key) : [];
  }

  async function resolveTargetForConnect(target: TargetConfig, signal: AbortSignal): Promise<TargetConfig> {
    return services.resolveTargetForConnect ? services.resolveTargetForConnect(target, signal) : target;
  }
}

function retryStatusForError(error: unknown): PaneRunStatus {
  if (error instanceof AgentAddressUnavailableError) {
    return error.address.status === "offline" ? "offline" : "waiting";
  }
  return "reconnecting";
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof AgentAddressUnavailableError) {
    return error.address.detail || error.message;
  }
  if (error instanceof AgUiHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "AG-UI request failed.";
}

function sameTarget(left: TargetConfig, right: TargetConfig): boolean {
  return (
    left.label === right.label &&
    left.url === right.url &&
    left.threadId === right.threadId &&
    JSON.stringify(left.source ?? { kind: "manual" }) ===
      JSON.stringify(right.source ?? { kind: "manual" })
  );
}

function nowUtc(): string {
  return new Date().toISOString();
}

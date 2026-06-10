import { useCallback, useEffect, useRef, useState } from "react";

import { buildConnectInput, connectAgUi, detachAgUi, fetchCapabilities, AgUiHttpError } from "./client";
import { AgentAddressUnavailableError, resolveTargetConfigForConnect } from "./discovery";
import {
  cachedRecordId,
  appendCachedEvent,
  clearCachedEvents,
  loadCachedEvents,
  type CachedAgUiEventRecord,
} from "./eventCache";
import {
  extractConnectionId,
  initialPaneEventState,
  reduceAgUiEvent,
  reduceHttpError,
  reduceParseError,
  type PaneEventState,
  type PaneRunStatus,
} from "./reducer";
import type { RawTimelineEntry, TargetConfig } from "./types";
import type { WatchedTargetRecord } from "./watchedTargets";

export interface WatchedTargetRuntime {
  target: TargetConfig;
  status: PaneRunStatus;
  eventState: PaneEventState;
  cacheLoaded: boolean;
  connectionId: string | null;
  error?: string;
}

interface WatchController {
  target: TargetConfig;
  stopped: boolean;
  abort: AbortController | null;
  connectionId: string | null;
  reconnectTimer: number | null;
  reconnectAttempt: number;
  nextSequence: number;
}

interface UseWatchedTargetsArgs {
  watchedTargets: Record<string, WatchedTargetRecord>;
  onResolvedTarget: (key: string, target: TargetConfig) => void;
}

export function useWatchedTargets({
  watchedTargets,
  onResolvedTarget,
}: UseWatchedTargetsArgs): {
  runtimes: Record<string, WatchedTargetRuntime>;
  clearTargetCache: (key: string) => Promise<void>;
  clearAllCaches: () => Promise<void>;
} {
  const controllersRef = useRef<Map<string, WatchController>>(new Map());
  const [runtimes, setRuntimes] = useState<Record<string, WatchedTargetRuntime>>({});

  const updateRuntime = useCallback(
    (key: string, update: (current: WatchedTargetRuntime) => WatchedTargetRuntime) => {
      setRuntimes((current) => {
        const existing = current[key];
        if (!existing) {
          return current;
        }
        return {
          ...current,
          [key]: update(existing),
        };
      });
    },
    [],
  );

  const setRuntimeStatus = useCallback(
    (key: string, status: PaneRunStatus, error?: string) => {
      updateRuntime(key, (current) => ({
        ...current,
        status,
        error,
      }));
    },
    [updateRuntime],
  );

  const stopWatcher = useCallback((key: string, detach: boolean) => {
    const controller = controllersRef.current.get(key);
    if (!controller) {
      return;
    }
    controller.stopped = true;
    if (controller.reconnectTimer !== null) {
      window.clearTimeout(controller.reconnectTimer);
      controller.reconnectTimer = null;
    }
    controller.abort?.abort();
    controller.abort = null;
    controllersRef.current.delete(key);
    if (detach) {
      void detachAgUi(controller.target, controller.connectionId).catch(() => undefined);
    }
    setRuntimes((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
  }, []);

  const scheduleReconnect = useCallback(
    (key: string, status: PaneRunStatus) => {
      const controller = controllersRef.current.get(key);
      if (!controller || controller.stopped) {
        return;
      }
      controller.reconnectAttempt += 1;
      setRuntimeStatus(key, status);
      const delayMs = Math.min(10000, 500 * 2 ** Math.min(controller.reconnectAttempt, 5));
      if (controller.reconnectTimer !== null) {
        window.clearTimeout(controller.reconnectTimer);
      }
      controller.reconnectTimer = window.setTimeout(() => {
        controller.reconnectTimer = null;
        void connectAttempt(key);
      }, delayMs);
    },
    [setRuntimeStatus],
  );

  const connectAttempt = useCallback(
    async (key: string): Promise<void> => {
      const controller = controllersRef.current.get(key);
      if (!controller || controller.stopped) {
        return;
      }
      const abort = new AbortController();
      controller.abort = abort;
      const baseTarget = controller.target;
      setRuntimeStatus(key, controller.reconnectAttempt > 0 ? "reconnecting" : "connecting");
      try {
        const resolvedTarget = await resolveTargetConfigForConnect(baseTarget, abort.signal);
        if (abort.signal.aborted || controller.stopped) {
          return;
        }
        controller.target = resolvedTarget;
        if (!sameTarget(baseTarget, resolvedTarget)) {
          onResolvedTarget(key, resolvedTarget);
        }
        void fetchCapabilities(resolvedTarget, abort.signal).catch(() => undefined);
        const input = buildConnectInput({
          paneId: key,
          threadId: resolvedTarget.threadId,
          paneKind: "agent",
        });
        await connectAgUi(
          resolvedTarget,
          input,
          {
            onOpen: () => {
              controller.reconnectAttempt = 0;
              setRuntimeStatus(key, "connected");
            },
            onRaw: () => undefined,
            onParseError: (raw) => {
              updateRuntime(key, (current) => ({
                ...current,
                status: "error",
                eventState: reduceParseError(current.eventState, raw),
                error: raw.parseError,
              }));
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
              void appendCachedEvent(cachedRecord).catch(() => undefined);
              updateRuntime(key, (current) => ({
                ...current,
                status: current.status === "empty" ? "connected" : current.status,
                connectionId: controller.connectionId,
                eventState: reduceAgUiEvent(current.eventState, event, raw),
              }));
            },
          },
          abort.signal,
        );
        if (!abort.signal.aborted && !controller.stopped) {
          controller.connectionId = null;
          if (resolvedTarget.source?.kind === "discovered") {
            scheduleReconnect(key, "reconnecting");
          } else {
            setRuntimeStatus(key, "disconnected");
          }
        }
      } catch (error) {
        if (abort.signal.aborted || controller.stopped) {
          return;
        }
        if (baseTarget.source?.kind === "discovered") {
          scheduleReconnect(key, retryStatusForError(error));
          return;
        }
        setRuntimeStatus(key, "error", requestErrorMessage(error));
        updateRuntime(key, (current) => ({
          ...current,
          eventState: reduceHttpError(current.eventState, requestErrorMessage(error)),
        }));
      }
    },
    [onResolvedTarget, scheduleReconnect, setRuntimeStatus, updateRuntime],
  );

  const startWatcher = useCallback(
    (record: WatchedTargetRecord) => {
      if (controllersRef.current.has(record.key)) {
        const controller = controllersRef.current.get(record.key)!;
        controller.target = record.target;
        updateRuntime(record.key, (current) => ({ ...current, target: record.target }));
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
      controllersRef.current.set(record.key, controller);
      setRuntimes((current) => ({
        ...current,
        [record.key]: {
          target: record.target,
          status: "connecting",
          eventState: initialPaneEventState(),
          cacheLoaded: false,
          connectionId: null,
        },
      }));
      void initializeWatcher(record.key, controller);
    },
    [updateRuntime],
  );

  const initializeWatcher = useCallback(
    async (key: string, controller: WatchController) => {
      try {
        const cached = await loadCachedEvents(key);
        if (controller.stopped) {
          return;
        }
        controller.nextSequence = Math.max(0, ...cached.map((record) => record.sequence)) + 1;
        const eventState = reduceCachedEvents(cached);
        updateRuntime(key, (current) => ({
          ...current,
          eventState,
          cacheLoaded: true,
        }));
      } catch (error) {
        updateRuntime(key, (current) => ({
          ...current,
          cacheLoaded: true,
          eventState: reduceHttpError(current.eventState, requestErrorMessage(error)),
          error: requestErrorMessage(error),
        }));
      }
      void connectAttempt(key);
    },
    [connectAttempt, updateRuntime],
  );

  useEffect(() => {
    const activeKeys = new Set(Object.keys(watchedTargets));
    for (const record of Object.values(watchedTargets)) {
      startWatcher(record);
    }
    for (const key of Array.from(controllersRef.current.keys())) {
      if (!activeKeys.has(key)) {
        stopWatcher(key, true);
      }
    }
  }, [startWatcher, stopWatcher, watchedTargets]);

  useEffect(() => {
    return () => {
      for (const key of Array.from(controllersRef.current.keys())) {
        stopWatcher(key, true);
      }
    };
  }, [stopWatcher]);

  const clearTargetCache = useCallback(
    async (key: string) => {
      await clearCachedEvents(key);
      const controller = controllersRef.current.get(key);
      if (controller) {
        controller.nextSequence = 1;
      }
      updateRuntime(key, (current) => ({
        ...current,
        eventState: initialPaneEventState(),
      }));
    },
    [updateRuntime],
  );

  const clearAllCaches = useCallback(async () => {
    await clearCachedEvents();
    for (const controller of controllersRef.current.values()) {
      controller.nextSequence = 1;
    }
    setRuntimes((current) =>
      Object.fromEntries(
        Object.entries(current).map(([key, runtime]) => [
          key,
          { ...runtime, eventState: initialPaneEventState() },
        ]),
      ),
    );
  }, []);

  return { runtimes, clearTargetCache, clearAllCaches };
}

function reduceCachedEvents(records: CachedAgUiEventRecord[]): PaneEventState {
  return records.reduce(
    (state, record) => reduceAgUiEvent(state, record.event, record.raw),
    initialPaneEventState(),
  );
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

import { expect, test } from "@playwright/test";

import type { CachedAgUiEventRecord } from "../src/ag-ui/eventCache";
import type { RawTimelineEntry, TargetConfig } from "../src/ag-ui/types";
import type { WatchedTargetRecord } from "../src/ag-ui/watchedTargets";
import { WorkbenchRuntime, type WorkbenchRuntimeServices } from "../src/runtime/workbenchRuntime";
import { gatewayKeyForTarget, initialRuntimeState, reduceRuntimeState } from "../src/runtime/state";

const target: TargetConfig = {
  label: "Alpha",
  url: "http://127.0.0.1:18080/v1/ag-ui",
  threadId: "alpha-thread",
  source: {
    kind: "discovered",
    passiveServerUrl: "http://127.0.0.1:17070",
    agentId: "alpha",
    agentName: "HOUMAO-alpha",
  },
};

test("runtime reducer tracks active-thread interest and mutation status", () => {
  const gatewayKey = gatewayKeyForTarget(target);
  expect(gatewayKey).toBeTruthy();
  const registered = reduceRuntimeState(
    initialRuntimeState,
    {
      type: "activeThread/registerInterest",
      paneId: "agent-1",
      gatewayKey: gatewayKey!,
      target,
    },
  );

  expect(registered.activeThreads[gatewayKey!].interestedPaneIds).toEqual(["agent-1"]);

  const active = reduceRuntimeState(registered, {
    type: "activeThread/setSucceeded",
    paneId: "agent-1",
    gatewayKey: gatewayKey!,
    target,
    activeThread: {
      status: "active",
      threadId: "alpha-thread",
      source: "gui_button",
      updatedAtUtc: "2026-06-10T00:00:00Z",
    },
    receivedAt: "2026-06-10T00:00:01Z",
  });

  expect(active.activeThreads[gatewayKey!].status).toBe("ready");
  expect(active.activeThreads[gatewayKey!].activeThread.threadId).toBe("alpha-thread");
});

test("runtime shares one active-thread poller per gateway and tears it down", async () => {
  const gatewayKey = gatewayKeyForTarget(target)!;
  let fetchCalls = 0;
  const runtime = new WorkbenchRuntime({
    activeThreadPollIntervalMs: 25,
    fetchActiveThread: async () => {
      fetchCalls += 1;
      return { status: "empty" };
    },
    setActiveThread: async (_target, threadId, source) => ({
      status: "active",
      threadId,
      source,
      updatedAtUtc: "2026-06-10T00:00:00Z",
    }),
    clearActiveThread: async () => ({ status: "empty" }),
  });

  runtime.dispatch({
    type: "activeThread/registerInterest",
    paneId: "agent-1",
    gatewayKey,
    target,
  });
  runtime.dispatch({
    type: "activeThread/registerInterest",
    paneId: "agent-2",
    gatewayKey,
    target: { ...target, label: "Alpha copy" },
  });

  await expect.poll(() => fetchCalls).toBeGreaterThan(0);
  const callsAfterStart = fetchCalls;
  await new Promise((resolve) => setTimeout(resolve, 80));
  expect(fetchCalls - callsAfterStart).toBeLessThanOrEqual(4);

  runtime.dispose();
  const callsAtDispose = fetchCalls;
  await new Promise((resolve) => setTimeout(resolve, 80));
  expect(fetchCalls).toBe(callsAtDispose);
});

test("watched target runtime caches live events and does not set active thread", async () => {
  const cached: CachedAgUiEventRecord[] = [];
  const activeThreadUpdates: Array<{ threadId: string; source: string }> = [];
  const runtime = new WorkbenchRuntime(
    runtimeServices({
      setActiveThread: async (_target, threadId, source) => {
        activeThreadUpdates.push({ threadId, source });
        return { status: "active", threadId, source };
      },
      loadCachedEvents: async () => [],
      appendCachedEvent: async (record) => {
        cached.push(record);
      },
      connectAgUi: async (_target, _input, handlers, signal) => {
        handlers.onOpen?.();
        handlers.onEvent(
          {
            type: "ACTIVITY_SNAPSHOT",
            messageId: "watch-activity",
            activityType: "watch",
            content: { marker: "watched-runtime-event" },
          },
          rawEntry("watched-runtime-event"),
        );
        await untilAborted(signal);
      },
    }),
  );

  runtime.dispatch({
    type: "watchedTargets/snapshotReceived",
    watchedTargets: {
      "watched-alpha": watchedRecord("watched-alpha", target),
    },
  });

  await expect.poll(() => cached.length).toBe(1);
  expect(activeThreadUpdates).toEqual([]);
  expect(runtime.snapshot().watchedTargets["watched-alpha"].eventState.activity[0].content).toMatchObject({
    marker: "watched-runtime-event",
  });

  runtime.dispatch({ type: "watchedTarget/clearCacheRequested", key: "watched-alpha" });
  await expect.poll(() => runtime.snapshot().watchedTargets["watched-alpha"].eventState.raw.length).toBe(0);
  expect(runtime.snapshot().watchedTargets["watched-alpha"].status).toBe("connected");

  runtime.dispose();
});

test("pane run stream reduces events, cancels, and does not retain prompt text", async () => {
  let aborted = false;
  const runtime = new WorkbenchRuntime(
    runtimeServices({
      runAgUi: async (_target, _input, handlers, signal) => {
        signal?.addEventListener("abort", () => {
          aborted = true;
        });
        handlers.onOpen?.();
        handlers.onEvent({ type: "RUN_STARTED", runId: "run-1", threadId: "alpha-thread" }, rawEntry("run-start"));
        handlers.onEvent(
          { type: "TEXT_MESSAGE_START", messageId: "assistant-1", role: "assistant" },
          rawEntry("message-start"),
        );
        handlers.onEvent(
          { type: "TEXT_MESSAGE_CONTENT", messageId: "assistant-1", delta: "runtime-run-evidence" },
          rawEntry("message-content"),
        );
        handlers.onEvent({ type: "TEXT_MESSAGE_END", messageId: "assistant-1" }, rawEntry("message-end"));
        await untilAborted(signal);
      },
    }),
  );

  runtime.dispatch({
    type: "agUi/runRequested",
    paneId: "agent-1",
    target,
    message: "secret prompt text",
    canvasSize: { w: 640, h: 420 },
  });

  await expect.poll(() => runtime.snapshot().paneAgUi["agent-1"]?.eventState.transcript[0]?.content).toBe(
    "runtime-run-evidence",
  );
  expect(JSON.stringify(runtime.snapshot())).not.toContain("secret prompt text");

  runtime.dispatch({ type: "pane/disposed", paneId: "agent-1" });
  await expect.poll(() => aborted).toBeTruthy();
  expect(runtime.snapshot().paneAgUi["agent-1"]).toBeUndefined();

  runtime.dispose();
});

test("tmux runtime routes output to sinks, suppresses read-only input, and cleans up", async () => {
  const socket = new FakeSocket();
  const output: string[] = [];
  const runtime = new WorkbenchRuntime(
    runtimeServices({
      openTmuxAttachSocket: () => socket.asWebSocket(),
    }),
  );

  runtime.dispatch({
    type: "tmux/registerOutputSink",
    paneId: "tmux-1",
    sink: (data) => output.push(data),
  });
  runtime.dispatch({
    type: "tmux/attachRequested",
    paneId: "tmux-1",
    sessionName: "houmao-alpha",
    mode: "read-only",
    cols: 80,
    rows: 24,
  });
  socket.open();
  socket.message({ type: "attached" });
  socket.message({ type: "output", data: "fixture attached houmao-alpha" });

  await expect.poll(() => runtime.snapshot().tmuxPanes["tmux-1"]?.attachState).toBe("attached");
  expect(output.join("")).toContain("fixture attached houmao-alpha");
  runtime.dispatch({ type: "tmux/inputRequested", paneId: "tmux-1", data: "blocked-input" });
  expect(socket.sent.some((value) => value.includes("blocked-input"))).toBeFalsy();

  runtime.dispatch({ type: "pane/disposed", paneId: "tmux-1" });
  expect(socket.closed).toBeTruthy();
  socket.message({ type: "output", data: "late-output" });
  expect(output.join("")).not.toContain("late-output");

  runtime.dispose();
});

test("runtime disposal aborts watched streams and closes tmux sockets", async () => {
  let watcherAborted = false;
  const socket = new FakeSocket();
  const runtime = new WorkbenchRuntime(
    runtimeServices({
      connectAgUi: async (_target, _input, handlers, signal) => {
        signal?.addEventListener("abort", () => {
          watcherAborted = true;
        });
        handlers.onOpen?.();
        await untilAborted(signal);
      },
      openTmuxAttachSocket: () => socket.asWebSocket(),
    }),
  );

  runtime.dispatch({
    type: "watchedTargets/snapshotReceived",
    watchedTargets: {
      "watched-alpha": watchedRecord("watched-alpha", target),
    },
  });
  runtime.dispatch({
    type: "tmux/attachRequested",
    paneId: "tmux-1",
    sessionName: "houmao-alpha",
    mode: "read-write",
    cols: 80,
    rows: 24,
  });
  await expect.poll(() => runtime.snapshot().watchedTargets["watched-alpha"]?.status).toBe("connected");

  runtime.dispose();
  expect(watcherAborted).toBeTruthy();
  expect(socket.closed).toBeTruthy();
});

function runtimeServices(overrides: Partial<WorkbenchRuntimeServices> = {}): WorkbenchRuntimeServices {
  return {
    fetchActiveThread: async () => ({ status: "empty" }),
    setActiveThread: async (_target, threadId, source) => ({
      status: "active",
      threadId,
      source,
    }),
    clearActiveThread: async () => ({ status: "empty" }),
    resolveTargetForConnect: async (nextTarget) => nextTarget,
    fetchCapabilities: async () => ({}),
    connectAgUi: async (_target, _input, handlers) => {
      handlers.onOpen?.();
    },
    runAgUi: async (_target, _input, handlers) => {
      handlers.onOpen?.();
    },
    detachAgUi: async () => undefined,
    loadCachedEvents: async () => [],
    appendCachedEvent: async () => undefined,
    clearCachedEvents: async () => undefined,
    fetchTmuxStatus: async () => ({
      status: "ready",
      tmuxAvailable: true,
    }),
    fetchTmuxSessions: async () => ({
      status: "ready",
      tmuxAvailable: true,
      sessions: [],
    }),
    fetchDiscoveredAgents: async () => [],
    setTimeout: (handler, timeoutMs) => setTimeout(handler, timeoutMs) as unknown as number,
    clearTimeout: (handle) => clearTimeout(handle as unknown as ReturnType<typeof setTimeout>),
    ...overrides,
  };
}

function watchedRecord(key: string, nextTarget: TargetConfig): WatchedTargetRecord {
  return {
    key,
    target: nextTarget,
    createdAt: "2026-06-10T00:00:00Z",
    updatedAt: "2026-06-10T00:00:00Z",
  };
}

function rawEntry(marker: string): RawTimelineEntry {
  return {
    id: marker,
    receivedAt: "2026-06-10T00:00:00Z",
    raw: marker,
  };
}

function untilAborted(signal: AbortSignal | undefined): Promise<void> {
  if (!signal) {
    return new Promise(() => undefined);
  }
  if (signal.aborted) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    signal.addEventListener("abort", () => resolve(), { once: true });
  });
}

class FakeSocket {
  readonly sent: string[] = [];
  closed = false;
  private m_readyState = 0;
  private readonly m_listeners = new Map<string, Array<(event: { data?: unknown }) => void>>();

  asWebSocket(): WebSocket {
    return this as unknown as WebSocket;
  }

  get readyState(): number {
    return this.m_readyState;
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    const callback =
      typeof listener === "function"
        ? (event: { data?: unknown }) => listener(event as Event)
        : (event: { data?: unknown }) => listener.handleEvent(event as Event);
    this.m_listeners.set(type, [...(this.m_listeners.get(type) ?? []), callback]);
  }

  send(value: string): void {
    this.sent.push(value);
  }

  close(): void {
    this.closed = true;
    this.m_readyState = 3;
    this.emit("close", {});
  }

  open(): void {
    this.m_readyState = WebSocket.OPEN;
    this.emit("open", {});
  }

  message(data: unknown): void {
    this.emit("message", { data: JSON.stringify(data) });
  }

  private emit(type: string, event: { data?: unknown }): void {
    for (const listener of this.m_listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

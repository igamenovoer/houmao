import { Subscription } from "rxjs";

import type { TmuxAttachMode } from "../../tmux/client";
import type { RuntimeTerminalOutputSink } from "../actions";
import type { WorkbenchRuntime, WorkbenchRuntimeServices } from "../workbenchRuntime";

interface TmuxAttachment {
  socket: WebSocket;
  sessionName: string;
  mode: TmuxAttachMode;
}

export function installTmuxEffects(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
): Subscription {
  const subscriptions = new Subscription();
  const sockets = new Map<string, TmuxAttachment>();
  const sinks = new Map<string, RuntimeTerminalOutputSink>();
  const refreshControllers = new Map<string, AbortController>();

  subscriptions.add(
    runtime.actions$.subscribe((action) => {
      switch (action.type) {
        case "tmux/refreshRequested":
          void refreshTmux(action.paneId, action.passiveServerUrl);
          break;
        case "tmux/registerOutputSink":
          sinks.set(action.paneId, action.sink);
          break;
        case "tmux/unregisterOutputSink":
          sinks.delete(action.paneId);
          break;
        case "tmux/attachRequested":
          attach(action.paneId, action.sessionName, action.mode, action.cols, action.rows);
          break;
        case "tmux/detachRequested":
        case "pane/disposed":
          detach(action.paneId);
          sinks.delete(action.paneId);
          break;
        case "tmux/inputRequested":
          sendInput(action.paneId, action.data);
          break;
        case "tmux/resizeRequested":
          sendResize(action.paneId, action.cols, action.rows);
          break;
        default:
          break;
      }
    }),
  );

  subscriptions.add(() => {
    for (const controller of refreshControllers.values()) {
      controller.abort();
    }
    refreshControllers.clear();
    for (const paneId of [...sockets.keys()]) {
      detach(paneId);
    }
    sinks.clear();
  });

  return subscriptions;

  async function refreshTmux(paneId: string, passiveServerUrl: string): Promise<void> {
    refreshControllers.get(paneId)?.abort();
    const controller = new AbortController();
    refreshControllers.set(paneId, controller);
    let tmuxError: string | undefined;
    let discoveryError: string | undefined;
    let bridgeStatus = runtime.snapshot().tmuxPanes[paneId]?.bridgeStatus ?? null;
    let sessions = runtime.snapshot().tmuxPanes[paneId]?.sessions ?? [];
    let agents = runtime.snapshot().tmuxPanes[paneId]?.agents ?? [];

    try {
      if (!services.fetchTmuxStatus || !services.fetchTmuxSessions) {
        throw new Error("tmux service is unavailable.");
      }
      const [nextBridgeStatus, tmuxSessions] = await Promise.all([
        services.fetchTmuxStatus(controller.signal),
        services.fetchTmuxSessions(controller.signal),
      ]);
      bridgeStatus = nextBridgeStatus;
      sessions = tmuxSessions.sessions;
      if (tmuxSessions.status === "error" || tmuxSessions.status === "unavailable") {
        tmuxError = tmuxSessions.detail ?? "tmux sessions are unavailable.";
      }
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      tmuxError = errorMessage(error);
      bridgeStatus = null;
      sessions = [];
    }

    try {
      if (!services.fetchDiscoveredAgents) {
        throw new Error("Houmao discovery service is unavailable.");
      }
      agents = await services.fetchDiscoveredAgents(passiveServerUrl, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      discoveryError = errorMessage(error);
      agents = [];
    } finally {
      refreshControllers.delete(paneId);
    }

    if (tmuxError || discoveryError || !bridgeStatus) {
      runtime.dispatch({
        type: "tmux/refreshFailed",
        paneId,
        bridgeStatus,
        sessions,
        agents,
        tmuxError,
        discoveryError,
        receivedAt: nowUtc(),
      });
      return;
    }
    runtime.dispatch({
      type: "tmux/refreshSucceeded",
      paneId,
      bridgeStatus,
      sessions,
      agents,
      receivedAt: nowUtc(),
    });
  }

  function attach(
    paneId: string,
    sessionName: string,
    mode: TmuxAttachMode,
    cols: number,
    rows: number,
  ): void {
    detach(paneId);
    if (!services.openTmuxAttachSocket) {
      runtime.dispatch({
        type: "tmux/attachFailed",
        paneId,
        error: "tmux attach WebSocket service is unavailable.",
        receivedAt: nowUtc(),
      });
      return;
    }
    runtime.dispatch({
      type: "tmux/attachStarted",
      paneId,
      sessionName,
      mode,
      receivedAt: nowUtc(),
    });
    const socket = services.openTmuxAttachSocket();
    sockets.set(paneId, { socket, sessionName, mode });
    socket.addEventListener("open", () => {
      sendSocketJson(socket, {
        type: "attach",
        sessionName,
        mode,
        cols,
        rows,
      });
    });
    socket.addEventListener("message", (event) => {
      const message = parseSocketMessage(event.data);
      if (message.type === "attached") {
        runtime.dispatch({
          type: "tmux/attachSucceeded",
          paneId,
          sessionName,
          mode,
          receivedAt: nowUtc(),
        });
        return;
      }
      if (message.type === "output" && typeof message.data === "string") {
        sinks.get(paneId)?.(message.data);
        return;
      }
      if (message.type === "error") {
        const detail = String(message.detail ?? message.code ?? "error");
        sinks.get(paneId)?.(`\r\n[tmux] ${detail}`);
        runtime.dispatch({
          type: "tmux/attachFailed",
          paneId,
          error: detail,
          receivedAt: nowUtc(),
        });
        return;
      }
      if (message.type === "exit") {
        sinks.get(paneId)?.("\r\n[tmux] attachment ended");
        runtime.dispatch({
          type: "tmux/attachDisconnected",
          paneId,
          receivedAt: nowUtc(),
        });
      }
    });
    socket.addEventListener("close", () => {
      sockets.delete(paneId);
      runtime.dispatch({
        type: "tmux/attachDisconnected",
        paneId,
        receivedAt: nowUtc(),
      });
    });
    socket.addEventListener("error", () => {
      sinks.get(paneId)?.("\r\n[tmux] WebSocket error");
      runtime.dispatch({
        type: "tmux/attachFailed",
        paneId,
        error: "tmux WebSocket error",
        receivedAt: nowUtc(),
      });
    });
  }

  function detach(paneId: string): void {
    const attachment = sockets.get(paneId);
    if (!attachment) {
      return;
    }
    sockets.delete(paneId);
    if (attachment.socket.readyState === WebSocket.OPEN) {
      sendSocketJson(attachment.socket, { type: "close" });
      attachment.socket.close(1000, "client detach");
    } else {
      attachment.socket.close();
    }
  }

  function sendInput(paneId: string, data: string): void {
    const attachment = sockets.get(paneId);
    if (!attachment || attachment.mode === "read-only" || attachment.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    sendSocketJson(attachment.socket, { type: "input", data });
  }

  function sendResize(paneId: string, cols: number, rows: number): void {
    const attachment = sockets.get(paneId);
    if (!attachment || attachment.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    sendSocketJson(attachment.socket, { type: "resize", cols, rows });
  }
}

function sendSocketJson(socket: WebSocket, value: unknown): void {
  socket.send(JSON.stringify(value));
}

function parseSocketMessage(value: unknown): Record<string, unknown> {
  if (typeof value !== "string") {
    return {};
  }
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "tmux request failed.";
}

function nowUtc(): string {
  return new Date().toISOString();
}

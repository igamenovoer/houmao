import { Subscription } from "rxjs";

import type { TmuxAttachMode } from "../../tmux/client";
import type { RuntimeTerminalOutputSink } from "../actions";
import type { WorkbenchRuntime, WorkbenchRuntimeServices } from "../workbenchRuntime";

interface TmuxAttachment {
  socket: WebSocket;
  sessionName: string;
  mode: TmuxAttachMode;
  socketId: number;
}

export function installTmuxEffects(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
): Subscription {
  const subscriptions = new Subscription();
  const sockets = new Map<string, TmuxAttachment>();
  const sinks = new Map<string, RuntimeTerminalOutputSink>();
  const interestedPaneIds = new Set<string>();
  let activePassiveServerUrl = "";
  let refreshController: AbortController | null = null;
  let refreshSequence = 0;
  let socketSequence = 0;
  let disposed = false;

  subscriptions.add(
    runtime.actions$.subscribe((action) => {
      switch (action.type) {
        case "tmux/registerInventoryInterest":
          registerInventoryInterest(action.paneId, action.passiveServerUrl);
          break;
        case "tmux/unregisterInventoryInterest":
          unregisterInventoryInterest(action.paneId);
          break;
        case "tmux/refreshRequested":
          activePassiveServerUrl = action.passiveServerUrl;
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
          detach(action.paneId);
          break;
        case "pane/disposed":
          unregisterInventoryInterest(action.paneId);
          detach(action.paneId);
          sinks.delete(action.paneId);
          break;
        case "tmux/inputRequested":
          sendInput(action.paneId, action.data);
          break;
        case "tmux/resizeRequested":
          sendResize(action.paneId, action.cols, action.rows);
          break;
        case "tmux/scrollRequested":
          sendScroll(action.paneId, action.direction, action.lines);
          break;
        default:
          break;
      }
    }),
  );

  subscriptions.add(() => {
    disposed = true;
    refreshController?.abort();
    refreshController = null;
    for (const paneId of [...sockets.keys()]) {
      detach(paneId);
    }
    interestedPaneIds.clear();
    sinks.clear();
  });

  return subscriptions;

  function registerInventoryInterest(paneId: string, passiveServerUrl: string): void {
    interestedPaneIds.add(paneId);
    activePassiveServerUrl = passiveServerUrl;
  }

  function unregisterInventoryInterest(paneId: string): void {
    interestedPaneIds.delete(paneId);
    if (interestedPaneIds.size === 0) {
      refreshController?.abort();
      refreshController = null;
    }
  }

  function requestInventoryRefresh(paneId?: string, passiveServerUrl?: string): void {
    if (disposed) {
      return;
    }
    const requestPaneId = paneId ?? firstInterestedPaneId();
    if (!requestPaneId) {
      return;
    }
    const nextPassiveServerUrl =
      passiveServerUrl ?? activePassiveServerUrl ?? runtime.snapshot().tmuxInventory.passiveServerUrl;
    runtime.dispatch({
      type: "tmux/refreshRequested",
      paneId: requestPaneId,
      passiveServerUrl: nextPassiveServerUrl,
    });
  }

  function firstInterestedPaneId(): string | undefined {
    return interestedPaneIds.values().next().value;
  }

  async function refreshTmux(paneId: string, passiveServerUrl: string): Promise<void> {
    refreshController?.abort();
    const controller = new AbortController();
    const sequence = refreshSequence + 1;
    refreshSequence = sequence;
    refreshController = controller;

    let tmuxError: string | undefined;
    let discoveryError: string | undefined;
    let bridgeStatus = runtime.snapshot().tmuxInventory.bridgeStatus;
    let sessions = runtime.snapshot().tmuxInventory.sessions;
    let agents = runtime.snapshot().tmuxInventory.agents;

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
      if (controller.signal.aborted || sequence !== refreshSequence) {
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
      if (controller.signal.aborted || sequence !== refreshSequence) {
        return;
      }
      discoveryError = errorMessage(error);
      agents = [];
    } finally {
      if (refreshController === controller) {
        refreshController = null;
      }
    }

    if (disposed || controller.signal.aborted || sequence !== refreshSequence) {
      return;
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
    const socketId = socketSequence + 1;
    socketSequence = socketId;
    sockets.set(paneId, { socket, sessionName, mode, socketId });
    debugTmux("socket-opened", { paneId, sessionName, socketId });
    socket.addEventListener("open", () => {
      if (!isCurrentSocket(paneId, socket)) {
        debugTmux("socket-open-ignored", { paneId, sessionName, socketId });
        return;
      }
      sendSocketJson(socket, {
        type: "attach",
        sessionName,
        mode,
        cols,
        rows,
      });
    });
    socket.addEventListener("message", (event) => {
      if (!isCurrentSocket(paneId, socket)) {
        debugTmux("socket-message-ignored", { paneId, sessionName, socketId });
        return;
      }
      const message = parseSocketMessage(event.data);
      if (message.type === "attached") {
        debugTmux("socket-attached", { paneId, sessionName, socketId });
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
        requestInventoryRefresh(paneId);
        return;
      }
      if (message.type === "exit") {
        debugTmux("socket-exit", { paneId, sessionName, socketId });
        sinks.get(paneId)?.("\r\n[tmux] attachment ended");
        sockets.delete(paneId);
        runtime.dispatch({
          type: "tmux/attachDisconnected",
          paneId,
          receivedAt: nowUtc(),
        });
        requestInventoryRefresh(paneId);
      }
    });
    socket.addEventListener("close", () => {
      if (!isCurrentSocket(paneId, socket)) {
        debugTmux("socket-close-ignored", { paneId, sessionName, socketId });
        return;
      }
      debugTmux("socket-close", { paneId, sessionName, socketId });
      sockets.delete(paneId);
      runtime.dispatch({
        type: "tmux/attachDisconnected",
        paneId,
        receivedAt: nowUtc(),
      });
      requestInventoryRefresh(paneId);
    });
    socket.addEventListener("error", () => {
      if (!isCurrentSocket(paneId, socket)) {
        debugTmux("socket-error-ignored", { paneId, sessionName, socketId });
        return;
      }
      debugTmux("socket-error", { paneId, sessionName, socketId });
      sinks.get(paneId)?.("\r\n[tmux] WebSocket error");
      runtime.dispatch({
        type: "tmux/attachFailed",
        paneId,
        error: "tmux WebSocket error",
        receivedAt: nowUtc(),
      });
      requestInventoryRefresh(paneId);
    });
  }

  function detach(paneId: string): void {
    const attachment = sockets.get(paneId);
    if (!attachment) {
      return;
    }
    debugTmux("socket-detach", {
      paneId,
      sessionName: attachment.sessionName,
      socketId: attachment.socketId,
    });
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

  function sendScroll(paneId: string, direction: "up" | "down", lines: number): void {
    const attachment = sockets.get(paneId);
    if (!attachment || attachment.socket.readyState !== WebSocket.OPEN) {
      debugTmux("socket-scroll-dropped", { paneId, direction, lines });
      return;
    }
    debugTmux("socket-scroll", {
      paneId,
      sessionName: attachment.sessionName,
      socketId: attachment.socketId,
      direction,
      lines,
    });
    sendSocketJson(attachment.socket, { type: "scroll", direction, lines });
  }

  function isCurrentSocket(paneId: string, socket: WebSocket): boolean {
    return sockets.get(paneId)?.socket === socket;
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

function debugTmux(event: string, detail: Record<string, unknown>): void {
  if (
    typeof window === "undefined" ||
    window.localStorage.getItem("hmwb.tmuxDebug") !== "1"
  ) {
    return;
  }
  console.debug("[tmux]", event, detail);
}

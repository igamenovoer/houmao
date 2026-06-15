import { Subscription } from "rxjs";

import { AgUiHttpError, buildConnectInput, buildRunInput } from "../../ag-ui/client";
import { extractConnectionId } from "../../ag-ui/reducer";
import type { RunAgentInput, TargetConfig } from "../../ag-ui/types";
import type { RuntimeStreamKind, WorkbenchRuntimeAction } from "../actions";
import type { WorkbenchRuntime, WorkbenchRuntimeServices } from "../workbenchRuntime";

interface PaneStreamController {
  target: TargetConfig;
  abort: AbortController;
  connectionId: string | null;
  streamKind: RuntimeStreamKind;
}

export function installAgUiEffects(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
): Subscription {
  const subscriptions = new Subscription();
  const controllers = new Map<string, PaneStreamController>();
  const capabilityControllers = new Map<string, AbortController>();

  subscriptions.add(
    runtime.actions$.subscribe((action) => {
      switch (action.type) {
        case "agUi/capabilitiesRequested":
          void fetchCapabilities(action);
          break;
        case "agUi/connectRequested":
          void startConnect(action.paneId, action.target);
          break;
        case "agUi/runRequested":
          void startRun(action.paneId, action.target, action.message);
          break;
        case "agUi/cancelRequested":
          stopPaneStream(action.paneId, action.detach);
          break;
        case "pane/disposed":
          stopPaneStream(action.paneId, true);
          stopCapabilityFetch(action.paneId);
          break;
        default:
          break;
      }
    }),
  );

  subscriptions.add(() => {
    for (const paneId of [...controllers.keys()]) {
      stopPaneStream(paneId, true);
    }
    for (const paneId of [...capabilityControllers.keys()]) {
      stopCapabilityFetch(paneId);
    }
  });

  return subscriptions;

  async function fetchCapabilities(
    action: Extract<WorkbenchRuntimeAction, { type: "agUi/capabilitiesRequested" }>,
  ): Promise<void> {
    if (!services.fetchCapabilities) {
      runtime.dispatch({
        type: "agUi/capabilitiesFailed",
        paneId: action.paneId,
        target: action.target,
        error: "AG-UI capabilities service is unavailable.",
        receivedAt: nowUtc(),
      });
      return;
    }
    stopCapabilityFetch(action.paneId);
    const abort = new AbortController();
    capabilityControllers.set(action.paneId, abort);
    try {
      const capabilities = await services.fetchCapabilities(action.target, abort.signal);
      capabilityControllers.delete(action.paneId);
      runtime.dispatch({
        type: "agUi/capabilitiesSucceeded",
        paneId: action.paneId,
        target: action.target,
        capabilities,
        receivedAt: nowUtc(),
      });
    } catch (error) {
      capabilityControllers.delete(action.paneId);
      if (abort.signal.aborted) {
        return;
      }
      runtime.dispatch({
        type: "agUi/capabilitiesFailed",
        paneId: action.paneId,
        target: action.target,
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
  }

  async function startConnect(paneId: string, target: TargetConfig): Promise<void> {
    const input = buildConnectInput({
      paneId,
      threadId: target.threadId,
    });
    await startStream(paneId, target, "connect", input);
  }

  async function startRun(
    paneId: string,
    target: TargetConfig,
    message: string,
  ): Promise<void> {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }
    const input = buildRunInput({
      paneId,
      threadId: target.threadId,
      message: trimmed,
    });
    await startStream(paneId, target, "run", input);
  }

  async function startStream(
    paneId: string,
    target: TargetConfig,
    streamKind: RuntimeStreamKind,
    input: RunAgentInput,
  ): Promise<void> {
    const streamService = streamKind === "run" ? services.runAgUi : services.connectAgUi;
    if (!streamService) {
      runtime.dispatch({
        type: "agUi/requestFailed",
        paneId,
        target,
        streamKind,
        error: `AG-UI ${streamKind} service is unavailable.`,
        receivedAt: nowUtc(),
      });
      return;
    }
    stopPaneStream(paneId, streamKind === "connect");
    const abort = new AbortController();
    const controller: PaneStreamController = {
      target,
      abort,
      connectionId: null,
      streamKind,
    };
    controllers.set(paneId, controller);
    try {
      await streamService(
        target,
        input,
        {
          onOpen: () => {
            runtime.dispatch({
              type: "agUi/streamOpened",
              paneId,
              target,
              streamKind,
              receivedAt: nowUtc(),
            });
          },
          onRaw: () => undefined,
          onParseError: (raw) => {
            runtime.dispatch({
              type: "agUi/parseError",
              paneId,
              target,
              streamKind,
              raw,
              error: raw.parseError,
            });
          },
          onEvent: (event, raw) => {
            if (abort.signal.aborted) {
              return;
            }
            const connectionId = extractConnectionId(event);
            if (connectionId) {
              controller.connectionId = connectionId;
            }
            runtime.dispatch({
              type: "agUi/eventReceived",
              paneId,
              target,
              streamKind,
              event,
              raw,
              connectionId: controller.connectionId,
            });
          },
        },
        abort.signal,
      );
      if (!abort.signal.aborted) {
        controllers.delete(paneId);
        runtime.dispatch({
          type: "agUi/streamFinished",
          paneId,
          target,
          streamKind,
          status: streamKind === "run" ? "finished" : "disconnected",
          receivedAt: nowUtc(),
        });
      }
    } catch (error) {
      if (abort.signal.aborted) {
        return;
      }
      controllers.delete(paneId);
      runtime.dispatch({
        type: "agUi/requestFailed",
        paneId,
        target,
        streamKind,
        error: requestErrorMessage(error),
        receivedAt: nowUtc(),
      });
    }
  }

  function stopPaneStream(paneId: string, detach: boolean): void {
    const controller = controllers.get(paneId);
    if (!controller) {
      return;
    }
    controllers.delete(paneId);
    controller.abort.abort();
    if (detach && controller.streamKind === "connect") {
      void services.detachAgUi?.(controller.target, controller.connectionId).catch(() => undefined);
    }
  }

  function stopCapabilityFetch(paneId: string): void {
    const controller = capabilityControllers.get(paneId);
    if (!controller) {
      return;
    }
    capabilityControllers.delete(paneId);
    controller.abort();
  }
}

function requestErrorMessage(error: unknown): string {
  if (error instanceof AgUiHttpError) {
    return error.body || error.message;
  }
  return error instanceof Error ? error.message : "AG-UI request failed.";
}

function nowUtc(): string {
  return new Date().toISOString();
}

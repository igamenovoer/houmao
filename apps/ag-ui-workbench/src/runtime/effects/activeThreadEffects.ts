import { EMPTY, Observable, Subscription, catchError, exhaustMap, filter, from, map, mergeMap, of, timer } from "rxjs";

import { AgUiHttpError } from "../../ag-ui/client";
import type { WorkbenchRuntime } from "../workbenchRuntime";
import type { WorkbenchRuntimeServices } from "../workbenchRuntime";
import {
  isActiveThreadClearRequested,
  isActiveThreadSetRequested,
  type GatewayKey,
  type WorkbenchRuntimeAction,
} from "../actions";

const DEFAULT_POLL_INTERVAL_MS = 1000;

export function installActiveThreadEffects(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
): Subscription {
  const subscriptions = new Subscription();
  const pollers = new Map<GatewayKey, Subscription>();
  const pollIntervalMs = services.activeThreadPollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;

  subscriptions.add(
    runtime.state$.subscribe((state) => {
      const interestedKeys = new Set(
	        Object.entries(state.activeThreads)
	          .filter(([, gateway]) => gateway.interestedPaneIds.length > 0 && gateway.status !== "unsupported")
	          .map(([gatewayKey]) => gatewayKey),
      );
      for (const gatewayKey of interestedKeys) {
        if (!pollers.has(gatewayKey)) {
          pollers.set(gatewayKey, startActiveThreadPoller(runtime, services, gatewayKey, pollIntervalMs));
        }
      }
      for (const [gatewayKey, poller] of [...pollers.entries()]) {
        if (!interestedKeys.has(gatewayKey)) {
          poller.unsubscribe();
          pollers.delete(gatewayKey);
        }
      }
    }),
  );

  subscriptions.add(
    runtime.actions$
      .pipe(
        filter(isActiveThreadSetRequested),
	        mergeMap((action) => {
	          if (runtime.snapshot().activeThreads[action.gatewayKey]?.status === "unsupported") {
	            return EMPTY;
	          }
	          return from(services.setActiveThread(action.target, action.threadId, action.source)).pipe(
	            map((activeThread) => ({
	              type: "activeThread/setSucceeded" as const,
              paneId: action.paneId,
              gatewayKey: action.gatewayKey,
              target: action.target,
              activeThread,
              receivedAt: nowUtc(),
            })),
	            catchError((error: unknown) => {
	              if (isUnsupportedActiveThreadError(error)) {
	                return of({
	                  type: "activeThread/unsupported" as const,
	                  gatewayKey: action.gatewayKey,
	                  target: action.target,
	                  error: errorMessage(error),
	                  receivedAt: nowUtc(),
	                });
	              }
	              return of({
	                type: "activeThread/mutationFailed" as const,
	                paneId: action.paneId,
	                gatewayKey: action.gatewayKey,
	                error: errorMessage(error),
	                receivedAt: nowUtc(),
	              });
	            }),
	          );
	        }),
      )
      .subscribe((action) => runtime.dispatch(action)),
  );

  subscriptions.add(
    runtime.actions$
      .pipe(
        filter(isActiveThreadClearRequested),
	        mergeMap((action) => {
	          if (runtime.snapshot().activeThreads[action.gatewayKey]?.status === "unsupported") {
	            return EMPTY;
	          }
	          return from(services.clearActiveThread(action.target, action.expectedThreadId)).pipe(
	            map((activeThread) => ({
	              type: "activeThread/clearSucceeded" as const,
              paneId: action.paneId,
              gatewayKey: action.gatewayKey,
              target: action.target,
              activeThread,
              receivedAt: nowUtc(),
            })),
	            catchError((error: unknown) => {
	              if (isUnsupportedActiveThreadError(error)) {
	                return of({
	                  type: "activeThread/unsupported" as const,
	                  gatewayKey: action.gatewayKey,
	                  target: action.target,
	                  error: errorMessage(error),
	                  receivedAt: nowUtc(),
	                });
	              }
	              return of({
	                type: "activeThread/mutationFailed" as const,
	                paneId: action.paneId,
	                gatewayKey: action.gatewayKey,
	                error: errorMessage(error),
	                receivedAt: nowUtc(),
	              });
	            }),
	          );
	        }),
      )
      .subscribe((action) => runtime.dispatch(action)),
  );

  subscriptions.add(() => {
    for (const poller of pollers.values()) {
      poller.unsubscribe();
    }
    pollers.clear();
  });

  return subscriptions;
}

function startActiveThreadPoller(
  runtime: WorkbenchRuntime,
  services: WorkbenchRuntimeServices,
  gatewayKey: GatewayKey,
  pollIntervalMs: number,
): Subscription {
  const controllers = new Set<AbortController>();
  const subscription = new Subscription();
  subscription.add(
	    timer(0, pollIntervalMs)
	    .pipe(
	      exhaustMap(() => {
	        const gateway = runtime.snapshot().activeThreads[gatewayKey];
	        if (!gateway || gateway.interestedPaneIds.length === 0 || gateway.status === "unsupported") {
	          return EMPTY;
	        }
        runtime.dispatch({ type: "activeThread/pollStarted", gatewayKey });
        return new Observable<WorkbenchRuntimeAction>((subscriber) => {
          const controller = new AbortController();
          controllers.add(controller);
          services
            .fetchActiveThread(gateway.target, controller.signal)
            .then((activeThread) => {
              if (!subscriber.closed) {
                subscriber.next({
                  type: "activeThread/pollSucceeded",
                  gatewayKey,
                  target: gateway.target,
                  activeThread,
                  receivedAt: nowUtc(),
                });
                subscriber.complete();
              }
            })
	            .catch((error: unknown) => {
	              if (!subscriber.closed) {
	                if (isUnsupportedActiveThreadError(error)) {
	                  subscriber.next({
	                    type: "activeThread/unsupported",
	                    gatewayKey,
	                    target: gateway.target,
	                    error: errorMessage(error),
	                    receivedAt: nowUtc(),
	                  });
	                } else {
	                  subscriber.next({
	                    type: "activeThread/pollFailed",
	                    gatewayKey,
	                    error: errorMessage(error),
	                    receivedAt: nowUtc(),
	                  });
	                }
	                subscriber.complete();
	              }
            })
            .finally(() => {
              controllers.delete(controller);
            });
          return () => {
            controller.abort();
            controllers.delete(controller);
          };
        });
      }),
    )
    .subscribe((action) => runtime.dispatch(action)),
  );
  subscription.add(() => {
    for (const controller of controllers) {
      controller.abort();
    }
    controllers.clear();
  });
  return subscription;
}

function nowUtc(): string {
  return new Date().toISOString();
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isUnsupportedActiveThreadError(error: unknown): boolean {
  const status = httpStatus(error);
  return status === 404 || status === 405;
}

function httpStatus(error: unknown): number | null {
  if (error instanceof AgUiHttpError) {
    return error.status;
  }
  if (isRecord(error) && typeof error.status === "number") {
    return error.status;
  }
  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import type { WorkbenchRuntime } from "./workbenchRuntime";
import type { WorkbenchRuntimeState } from "./state";

const WorkbenchRuntimeContext = createContext<WorkbenchRuntime | null>(null);

export function WorkbenchRuntimeProvider({
  runtime,
  children,
}: {
  runtime: WorkbenchRuntime;
  children: ReactNode;
}) {
  return (
    <WorkbenchRuntimeContext.Provider value={runtime}>{children}</WorkbenchRuntimeContext.Provider>
  );
}

export function useWorkbenchRuntime(): WorkbenchRuntime {
  const runtime = useContext(WorkbenchRuntimeContext);
  if (!runtime) {
    throw new Error("Workbench runtime context is unavailable.");
  }
  return runtime;
}

export function useRuntimeDispatch(): WorkbenchRuntime["dispatch"] {
  const runtime = useWorkbenchRuntime();
  return useMemo(() => runtime.dispatch.bind(runtime), [runtime]);
}

export function useRuntimeSelector<T>(selector: (state: WorkbenchRuntimeState) => T): T {
  const runtime = useWorkbenchRuntime();
  const cacheRef = useRef<{ state: WorkbenchRuntimeState; value: T } | null>(null);
  const getSnapshot = useCallback(() => {
    const state = runtime.snapshot();
    const cache = cacheRef.current;
    if (cache?.state === state) {
      return cache.value;
    }
    const value = selector(state);
    cacheRef.current = { state, value };
    return value;
  }, [runtime, selector]);
  const subscribe = useCallback((listener: () => void) => runtime.subscribe(listener), [runtime]);
  return useSyncExternalStore(
    subscribe,
    getSnapshot,
    getSnapshot,
  );
}

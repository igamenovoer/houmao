import { Subscription } from "rxjs";

import type { WorkbenchRuntime } from "../workbenchRuntime";

export function installDiscoveryEffects(_runtime: WorkbenchRuntime): Subscription {
  return new Subscription();
}

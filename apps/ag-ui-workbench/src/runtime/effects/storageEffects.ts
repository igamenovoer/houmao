import { Subscription } from "rxjs";

import type { WorkbenchRuntime } from "../workbenchRuntime";

export function installStorageEffects(_runtime: WorkbenchRuntime): Subscription {
  return new Subscription();
}

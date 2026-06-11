import type { Plugin } from "vite";

import { DEBUG_PREFIX, handleDebugRequest } from "../src/server/debugAgent";

export function houmaoAgUiDebugAgentPlugin(): Plugin {
  return {
    name: "houmao-ag-ui-debug-agent",
    configureServer(server) {
      server.middlewares.use(DEBUG_PREFIX, (req, res) => {
        void handleDebugRequest(req, res);
      });
    },
  };
}

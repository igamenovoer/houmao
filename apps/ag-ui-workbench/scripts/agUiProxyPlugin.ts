import type { Plugin } from "vite";

import { handleProxyRequest, PROXY_PREFIX } from "../src/server/agUiProxy";

export function houmaoAgUiProxyPlugin(): Plugin {
  return {
    name: "houmao-ag-ui-proxy",
    configureServer(server) {
      server.middlewares.use(PROXY_PREFIX, (req, res) => {
        void handleProxyRequest(req, res);
      });
    },
  };
}

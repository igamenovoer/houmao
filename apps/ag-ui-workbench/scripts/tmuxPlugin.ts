import type { Plugin, ViteDevServer } from "vite";
import { WebSocketServer } from "ws";

import {
  handleTmuxAttachSocket,
  handleTmuxHttpRequest,
  TMUX_PREFIX,
} from "../src/server/tmuxBridge";

export function houmaoTmuxPlugin(): Plugin {
  const wss = new WebSocketServer({ noServer: true });

  return {
    name: "houmao-tmux-bridge",
    configureServer(server) {
      server.middlewares.use(TMUX_PREFIX, (req, res) => {
        void handleTmuxHttpRequest(req, res);
      });
      configureTmuxWebSocket(server, wss);
    },
  };
}

function configureTmuxWebSocket(server: ViteDevServer, wss: WebSocketServer): void {
  server.httpServer?.on("upgrade", (req, socket, head) => {
    const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
    if (requestUrl.pathname !== `${TMUX_PREFIX}/attach`) {
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req);
    });
  });
  wss.on("connection", (ws) => {
    handleTmuxAttachSocket(ws);
  });
}

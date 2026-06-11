import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { houmaoAgUiDebugAgentPlugin } from "./scripts/agUiDebugAgentPlugin";
import { houmaoAgUiProxyPlugin } from "./scripts/agUiProxyPlugin";
import { houmaoTmuxPlugin } from "./scripts/tmuxPlugin";

const useFastifyFrontendOnly = process.env.HOUMAO_AG_UI_WORKBENCH_FASTIFY_FRONTEND === "1";
const hostIntegrationPlugins = useFastifyFrontendOnly
  ? []
  : [houmaoAgUiProxyPlugin(), houmaoAgUiDebugAgentPlugin(), houmaoTmuxPlugin()];

export default defineConfig({
  plugins: [react(), ...hostIntegrationPlugins],
  server: {
    host: "127.0.0.1",
    port: 5177,
    strictPort: false,
  },
});

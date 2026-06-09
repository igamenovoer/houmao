import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { houmaoAgUiDebugAgentPlugin } from "./scripts/agUiDebugAgentPlugin";
import { houmaoAgUiProxyPlugin } from "./scripts/agUiProxyPlugin";

export default defineConfig({
  plugins: [react(), houmaoAgUiProxyPlugin(), houmaoAgUiDebugAgentPlugin()],
  server: {
    host: "127.0.0.1",
    port: 5177,
    strictPort: false,
  },
});

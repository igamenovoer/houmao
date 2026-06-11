## Why

The AG-UI workbench is moving from a browser-only development harness into a single-user local web application where a bundled backend owns host-side integration, presentation state, and large-data workflows. This is needed before dynamic Plotly and future rich presentation capabilities can work safely, because large datasets and local host integrations should not be owned by browser memory or Vite development plugins.

## What Changes

- Introduce a real TypeScript backend server for `apps/ag-ui-workbench` using Fastify, bound to loopback by default and treated as part of the GUI application.
- Split the workbench into a browser frontend and local backend while preserving a single-user same-host usage model: the user starts the GUI server, then opens the browser at that server port.
- Move existing development-only backend behaviors, including the AG-UI loopback proxy, Debug Agent fixture server, and tmux bridge, behind production-capable server modules rather than Vite-only plugins.
- Make the GUI backend the AG-UI client peer for Houmao gateways. The browser talks to the GUI backend through a private workbench protocol; it should not be the direct owner of AG-UI gateway networking.
- Establish a presentation-session boundary owned by the GUI backend so future graphing work can attach datasource metadata, query/materialization state, and bounded browser render payloads without sending large datasets through AG-UI or storing them in browser state.
- Preserve the current React, Dockview, RxJS runtime, Playwright testing, and local loopback security posture while changing the process and ownership boundary.
- **BREAKING**: `apps/ag-ui-workbench` no longer treats `vite --host 127.0.0.1` and Vite middleware plugins as the primary application server model. Development may still use Vite, but the authoritative local GUI server is Fastify.

## Capabilities

### New Capabilities

- `ag-ui-workbench-local-server`: Defines the local single-user Fastify server, frontend serving model, private browser/backend protocol boundary, loopback policy, and server-owned presentation-session responsibilities.

### Modified Capabilities

- `ag-ui-workbench-app`: Updates the workbench app contract from a standalone browser/Vite harness to a local server-backed single-user web application while preserving the existing docked pane UX and AG-UI workbench purpose.
- `ag-ui-workbench-runtime-lifecycles`: Moves long-lived network and host integration ownership toward the local GUI backend where appropriate while keeping browser runtime state serializable and view-oriented.
- `ag-ui-workbench-rxjs-runtime`: Clarifies that RxJS remains the browser runtime/event layer, while server-side Fastify modules own host-side AG-UI, tmux, proxy, and future presentation-session workflows.

## Impact

- Affected application code: `apps/ag-ui-workbench/package.json`, `vite.config.ts`, `scripts/*Plugin.ts`, `src/ag-ui/*`, `src/runtime/*`, `src/tmux/*`, `src/panes/*`, and new `src/server`, `src/shared`, or equivalent server/frontend module boundaries.
- New or promoted dependencies: Fastify and likely `@fastify/websocket`; schema validation should use TypeScript-friendly validators such as Zod or JSON Schema where appropriate.
- Existing dependencies retained: React, Vite, Dockview, RxJS, Playwright, `ws`, xterm, and AG-UI core.
- Testing impact: browser E2E must start the Fastify-backed local GUI server rather than assuming Vite middleware plugins are the only backend surface.
- Documentation impact: workbench README and developer commands must describe the local GUI server, loopback binding, development mode, and production-like run mode.
- Security impact: loopback-only defaults, target URL allowlisting, no credential persistence, no browser ownership of large datasets, and deterministic teardown remain required.

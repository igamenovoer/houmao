## Context

`apps/ag-ui-workbench` is currently a Vite React application whose host-side behavior is implemented through Vite plugins. Those plugins provide the AG-UI loopback proxy, Debug Agent fixture, and tmux bridge during development. That model was useful for an experimental harness, but it makes the browser too central: the browser directly owns AG-UI networking, Vite owns host integration, and there is no durable backend boundary for large presentation state.

The target product shape is a single-user local web application. The user runs the GUI server on the same host as Houmao, the server binds to a local port, and the browser opens that port. The GUI server is part of the GUI product, not part of Houmao. Houmao continues to expose AG-UI through per-agent gateways; the GUI server becomes the AG-UI client peer and the browser talks to the GUI server through a private workbench protocol.

This change is a structural refactor. It should not implement the full future dynamic datasource or analytics engine yet, but it must create the server-owned presentation-session boundary needed by that work.

## Goals / Non-Goals

**Goals:**

- Introduce a Fastify-based TypeScript local server as the authoritative AG-UI workbench application entrypoint.
- Keep the workbench as a single-user same-host web application with loopback binding by default.
- Serve the existing React/Dockview frontend through the local server in production-like mode.
- Keep Vite for frontend development and builds without making Vite plugins the primary host-integration architecture.
- Move AG-UI gateway access, target URL allowlisting, Debug Agent fixture behavior, and tmux host access behind Fastify server modules.
- Define a private browser/backend protocol boundary for pane state, AG-UI event delivery, tmux attachment, and future presentation sessions.
- Preserve browser runtime strengths: React rendering, Dockview panes, RxJS browser event layer, pure reducers, and Playwright coverage.
- Add a server-owned presentation-session shell that can later own datasource metadata, query/materialization jobs, and bounded browser render payloads.

**Non-Goals:**

- Do not move Houmao's per-agent AG-UI gateway into the GUI server.
- Do not make the GUI server a managed-agent lifecycle controller.
- Do not implement full Plotly dynamic datasource materialization, DuckDB query execution, Arrow transport, or D3 sandboxing in this change.
- Do not introduce multi-user authentication, tenancy, remote deployment, or public network serving.
- Do not replace React, Dockview, RxJS, Playwright, xterm, or the AG-UI event reducer model.
- Do not require Electron or Tauri for this refactor.

## Decisions

### Decision: Fastify is the application server

Use Fastify for the local GUI server. The server owns API routes, WebSocket upgrades, static asset serving, target policy checks, and host-side integrations.

Alternatives considered:

- Vite plugins only: keeps the current model but leaves production behavior tied to development middleware and does not create a clean host-side application boundary.
- Express: workable, but weaker fit than Fastify for typed route schemas, plugin structure, and route-level validation.
- Electron/Tauri: useful later for native packaging, but unnecessary for a local browser application.

### Decision: The GUI backend is the AG-UI client peer

The browser should no longer be the primary component that opens AG-UI streams to Houmao gateways. The Fastify server should own gateway URL normalization, loopback allowlisting, AG-UI capabilities, connect, run, detach, and event-stream forwarding or reduction. The browser receives reduced events or streamed private protocol messages from the GUI backend.

Alternatives considered:

- Keep browser-to-gateway proxying: simpler short term, but leaves browser state and Vite proxy behavior on the critical path for presentation data and host integrations.
- Put this in Houmao passive server: wrong product boundary for third-party GUI software. The presentation server belongs to the GUI.

### Decision: Keep a private browser/backend protocol separate from AG-UI

AG-UI remains the control and intent protocol between the GUI backend and Houmao gateways. Browser/backend messages are a private workbench protocol for UI sessions, pane state, tmux attach messages, bounded chart materializations, and local server diagnostics.

This prevents AG-UI from becoming a bulk data transport and keeps future rich GUI implementations free to choose their own browser protocol.

### Decision: Preserve RxJS in the browser, but move host-side effects to server modules

The browser still uses the existing RxJS runtime for UI actions, view models, pane lifecycle, rendering state, and browser-owned teardown. Server modules own host-side effects: AG-UI HTTP/SSE clients, tmux process/WebSocket bridge, Debug Agent fixture handling, target policy, and future presentation-session jobs.

The browser runtime should call typed client services that target the local Fastify server instead of directly opening Houmao gateway streams.

### Decision: Development still uses Vite, but Fastify remains the public entrypoint

In production-like mode, Fastify serves the built frontend assets. In development, Fastify should remain the URL the user opens. It can proxy frontend asset and HMR traffic to a Vite dev server or use an equivalent integration, but host-side APIs must be served by Fastify.

This preserves the "one local GUI port" mental model while keeping Vite's frontend development loop.

### Decision: Introduce a presentation-session shell now

Add server-side presentation-session concepts as an interface and state owner, but keep implementation minimal in this change. The shell should support session ids, pane bindings, safe metadata, and teardown. It should explicitly not move large datasets into browser state.

Future graphing changes can add datasource registries, query engines, materialization modes, and Plotly-specific bounded render payloads to this boundary.

### Decision: Keep loopback security strict

The local server binds to `127.0.0.1` by default. It should reject non-loopback target URLs unless an explicit developer allowlist is configured. It should not persist credentials, authorization headers, raw AG-UI request bodies, raw terminal bytes, or large datasource rows in browser storage.

## Risks / Trade-offs

- **Risk: The refactor is large and can break existing E2E tests.** → Migrate one backend surface at a time behind stable browser service interfaces, and keep deterministic fixtures for AG-UI, tmux, and Debug Agent behavior.
- **Risk: Running Fastify and Vite together can complicate development ports and HMR.** → Make Fastify the user-facing port, document the internal Vite port, and test HMR/proxy behavior separately from production static serving.
- **Risk: Browser runtime and server runtime responsibilities can blur.** → Keep a written ownership table and prohibit non-serializable host handles in browser reduced state.
- **Risk: Private browser/backend protocol could grow without validation.** → Define shared schemas for private messages and validate server route inputs and WebSocket messages.
- **Risk: Server-owned AG-UI streams may lose the current raw event diagnostics.** → Preserve raw event inspection as bounded, reduced diagnostic state, with clear limits and no credential-bearing headers or request bodies.
- **Risk: Future datasource work may overfit to Plotly too early.** → Keep the presentation-session shell renderer-neutral and only define session/data ownership in this change.

## Migration Plan

1. Add the Fastify server skeleton and production static serving path.
2. Add a browser client service layer for private workbench backend APIs.
3. Move the AG-UI loopback proxy into a Fastify route while preserving current target-policy behavior and SSE streaming semantics.
4. Move the Debug Agent fixture server behavior from Vite plugin code into server modules.
5. Move the tmux bridge from Vite plugin code into server modules and keep the browser WebSocket API stable where practical.
6. Repoint browser runtime services from Vite plugin endpoints and direct proxy calls to the Fastify backend.
7. Add the minimal presentation-session registry and expose safe session metadata through server APIs.
8. Update workbench scripts, README, and Playwright config so tests start the Fastify-backed GUI server.
9. Remove or demote Vite plugin implementations once equivalent Fastify-backed paths pass tests.

Rollback is local to the workbench app during development: keep the existing Vite-plugin path available until the Fastify path covers AG-UI proxy, Debug Agent, tmux bridge, and E2E fixtures.

## Open Questions

- Should the private browser/backend protocol use plain REST plus WebSocket, or should it adopt tRPC for typed request/response calls?
- Should the server route schemas use Zod, JSON Schema with Fastify type providers, or generated schemas from shared TypeScript types?
- Should the first Fastify server command replace `bun run dev`, or should it start as a new `dev:server` command until the refactor is complete?
- How much raw AG-UI event history should the server retain for diagnostics before handing state to the browser?
- Should presentation sessions be per browser tab, per Dockview pane, or both with an explicit parent/child relationship?

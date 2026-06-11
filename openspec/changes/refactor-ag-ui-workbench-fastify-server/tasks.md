## 1. Server Foundation

- [x] 1.1 Add Fastify server dependencies and any required type packages to `apps/ag-ui-workbench/package.json`
- [x] 1.2 Add server-oriented TypeScript build/dev scripts without removing the existing frontend build path until migration is complete
- [x] 1.3 Create the `src/server` module boundary with a Fastify app factory, lifecycle startup/shutdown helpers, and loopback host/port configuration
- [x] 1.4 Add a server health/status route that proves the Fastify server is the local GUI backend
- [x] 1.5 Add deterministic server tests or lightweight smoke coverage for app creation, loopback defaults, and shutdown cleanup

## 2. Frontend Serving and Development Mode

- [x] 2.1 Add production-like static frontend serving from the Fastify server after `vite build`
- [x] 2.2 Add development mode that keeps Fastify as the user-facing origin while preserving Vite frontend development and HMR
- [x] 2.3 Update workbench package scripts so the documented local GUI command starts the Fastify-backed application
- [x] 2.4 Preserve a temporary legacy Vite-plugin path only as a migration fallback until equivalent Fastify routes pass tests
- [x] 2.5 Update README or workbench docs with the same-host single-user server model

## 3. Shared Protocol and Browser Services

- [x] 3.1 Create a `src/shared` or equivalent boundary for browser/server message types and validation schemas
- [x] 3.2 Define private workbench request/response schemas for capabilities, connect, run, detach, target policy errors, and stream diagnostics
- [x] 3.3 Define private workbench WebSocket message schemas for tmux and future session stream traffic
- [x] 3.4 Add browser client services that call the Fastify local server instead of constructing direct Vite-plugin or arbitrary gateway requests
- [x] 3.5 Add validation tests for malformed private protocol messages and deterministic error payloads

## 4. Server-Owned AG-UI Bridge

- [x] 4.1 Move target URL normalization and loopback allowlist policy from the Vite proxy plugin into a server module
- [x] 4.2 Implement Fastify routes for AG-UI capabilities, connect, run, detach, and proxy-compatible streaming behavior
- [x] 4.3 Preserve SSE streaming semantics, upstream abort behavior, content type forwarding, and deterministic HTTP errors
- [x] 4.4 Route browser runtime AG-UI services through the local server bridge
- [x] 4.5 Preserve pure AG-UI event reduction in the browser after events are received through the local server boundary
- [x] 4.6 Add tests for allowed target requests, rejected target requests, stream abort, `RUN_ERROR`, and visible reduced state

## 5. Debug Agent and Tmux Server Modules

- [x] 5.1 Move Debug Agent fixture behavior from the Vite plugin into a Fastify server module
- [x] 5.2 Move tmux inventory lookup from the Vite plugin into a Fastify server module
- [x] 5.3 Move tmux attach WebSocket handling from the Vite plugin into a Fastify WebSocket route
- [x] 5.4 Preserve read-only enforcement in both browser UI and server-side tmux bridge handling
- [x] 5.5 Repoint browser Debug Agent and tmux runtime services to the local server routes
- [x] 5.6 Add tests for Debug Agent fixture publishing, tmux inventory, read-write attach, read-only input rejection, and detach cleanup

## 6. Presentation Session Shell

- [x] 6.1 Add a server-owned presentation-session registry with session ids, pane association, safe metadata, and deterministic teardown
- [x] 6.2 Add private API routes or messages for creating, reading, and disposing presentation sessions
- [x] 6.3 Add browser-side service and runtime state for session handles without storing large datasource contents in browser state
- [x] 6.4 Add diagnostics that distinguish presentation-session metadata from AG-UI gateway state
- [x] 6.5 Add tests proving session cleanup does not control Houmao agent lifecycle

## 7. Browser Runtime Migration

- [x] 7.1 Update runtime service interfaces to separate browser-owned workflows from server-owned host workflows
- [x] 7.2 Route capabilities, connect, run, detach, active-thread, watched-target, and reconnect effects through local server services where server equivalents exist
- [x] 7.3 Keep reducer state serializable and exclude server resource handles, request bodies, credentials, raw terminal bytes, and unbounded replay buffers
- [x] 7.4 Preserve message diagnostics, raw event inspection limits, watched-target cache behavior, and clear-canvas behavior after routing through the local server
- [x] 7.5 Add unit tests for runtime cancellation and reducer behavior with server-forwarded AG-UI events

## 8. E2E, Cleanup, and Documentation

- [x] 8.1 Update Playwright configs so deterministic workbench E2E starts the Fastify-backed local server
- [x] 8.2 Add E2E coverage for multi-pane AG-UI flow through the local server
- [x] 8.3 Add E2E coverage for AG-UI proxy policy, Debug Agent fixture behavior, tmux bridge behavior, and server-owned teardown
- [x] 8.4 Remove or demote Vite plugin implementations once their Fastify replacements are covered
- [x] 8.5 Run `bun run typecheck`, the workbench build, and relevant Playwright suites
- [x] 8.6 Update plan docs if this change supersedes browser-owned datasource language in `context/plans/ag-ui-advanced-cap`

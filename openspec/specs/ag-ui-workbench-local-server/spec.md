# ag-ui-workbench-local-server Specification

## Purpose
TBD - created by archiving change refactor-ag-ui-workbench-fastify-server. Update Purpose after archive.
## Requirements
### Requirement: Workbench runs as a single-user local Fastify web application
The AG-UI workbench SHALL provide a TypeScript Fastify backend server as the authoritative local GUI application entrypoint.

The server SHALL be intended for a single user running the GUI on the same host as Houmao.

The server SHALL bind to loopback by default.

The user SHALL access the GUI by opening a browser to the local server port.

The server SHALL be treated as part of the GUI product rather than as part of the Houmao Python runtime or managed-agent lifecycle.

#### Scenario: User opens browser to Fastify server
- **WHEN** the user starts the AG-UI workbench local server
- **THEN** the server binds to a loopback host and a local port
- **AND THEN** the browser frontend is reachable from that local server origin

#### Scenario: Server is not a Houmao lifecycle owner
- **WHEN** the workbench server starts, stops, reloads, connects to an agent, or closes a browser session
- **THEN** it does not start, stop, restart, shut down, or interrupt any Houmao managed agent unless a future explicit user-facing lifecycle feature requires that behavior

### Requirement: Workbench server serves the frontend in production-like mode
The Fastify server SHALL serve the built React frontend assets in production-like mode.

The repository SHALL keep Vite for frontend development and asset builds.

In development mode, the Fastify server SHALL remain the user-facing origin for workbench APIs and MAY proxy frontend asset and HMR traffic to a Vite dev server.

Vite middleware plugins SHALL NOT be the authoritative host-integration implementation after their Fastify equivalents exist.

#### Scenario: Built frontend is served by Fastify
- **WHEN** a developer builds and starts the workbench in production-like mode
- **THEN** the Fastify server serves the browser application assets
- **AND THEN** workbench backend APIs are available on the same local server origin

#### Scenario: Development keeps one user-facing GUI origin
- **WHEN** a developer starts the workbench in development mode
- **THEN** the user opens the Fastify server origin
- **AND THEN** frontend development assets and workbench backend APIs remain reachable without requiring the user to manually navigate to multiple ports

### Requirement: Workbench server owns host-side integrations
The Fastify server SHALL own host-side integrations that require local process access, loopback network access, or long-lived host resources.

Server-owned integrations SHALL include the AG-UI gateway client/proxy, Debug Agent fixture backend, tmux bridge, and future presentation-session data services.

The browser frontend SHALL communicate with these integrations through private workbench server APIs or WebSocket streams.

#### Scenario: Browser does not call tmux directly
- **WHEN** the browser attaches to a tmux session through a workbench tmux tab
- **THEN** the browser uses the workbench server protocol
- **AND THEN** host tmux process access is owned by the Fastify server

#### Scenario: Browser does not own AG-UI target policy
- **WHEN** the browser requests capabilities, connect, run, or detach behavior for a Houmao AG-UI target
- **THEN** the Fastify server performs target normalization and policy checks
- **AND THEN** the browser does not bypass the server to contact arbitrary AG-UI targets directly

### Requirement: Workbench server provides a private browser protocol
The workbench SHALL define a private browser/backend protocol separate from AG-UI.

The private protocol SHALL carry browser session messages, pane commands, reduced AG-UI event updates, tmux attachment messages, diagnostics, and future bounded presentation render payloads.

The private protocol SHALL validate client inputs and SHALL NOT be documented as a stable public Houmao protocol.

AG-UI SHALL remain the protocol between the workbench server and Houmao gateways.

#### Scenario: AG-UI and browser protocol are distinct
- **WHEN** a browser pane submits a prompt through the workbench frontend
- **THEN** the browser sends a private workbench command to the Fastify server
- **AND THEN** the server constructs and sends the AG-UI request to the Houmao gateway

#### Scenario: Private protocol input is validated
- **WHEN** the browser sends a malformed private workbench message
- **THEN** the Fastify server rejects or ignores the message deterministically
- **AND THEN** the server does not forward malformed content to a Houmao gateway

### Requirement: Workbench server owns presentation sessions
The Fastify server SHALL define a presentation-session boundary for GUI-owned presentation state.

Presentation sessions SHALL be owned by the GUI backend, not by Houmao and not by browser-only state.

The first implementation SHALL establish session identity, pane association, lifecycle cleanup, and safe metadata plumbing.

The first implementation SHALL NOT need to implement full large-dataset querying, DuckDB execution, Arrow transport, or Plotly materialization.

Future graphing capabilities MAY add datasource registries, query execution, materialization, and bounded browser render payloads under this presentation-session boundary.

#### Scenario: Presentation session is server-owned
- **WHEN** the browser opens a pane that needs presentation state
- **THEN** the Fastify server can create or associate a presentation session for that pane
- **AND THEN** the browser receives only session identifiers and safe metadata needed for display

#### Scenario: Large datasource contents are not browser-owned
- **WHEN** a future chart references a large presentation datasource
- **THEN** the datasource contents remain owned by the presentation session on the Fastify server
- **AND THEN** the browser receives only bounded materialized data or display updates

### Requirement: Workbench server enforces local security boundaries
The Fastify server SHALL bind to loopback by default and SHALL reject non-loopback AG-UI targets unless an explicit allowlist permits them.

The server SHALL NOT persist credentials, authorization headers, cookies, bearer tokens, raw terminal bytes, raw AG-UI request bodies, or large datasource rows in browser storage.

The server SHALL strip hop-by-hop and unsafe proxy headers when forwarding requests.

The server SHALL release stream, WebSocket, process, and session resources during deterministic teardown.

#### Scenario: Non-loopback AG-UI target is rejected
- **WHEN** the browser asks the workbench server to reach a disallowed non-loopback AG-UI target
- **THEN** the server rejects the request before contacting that target
- **AND THEN** the browser receives a deterministic target-policy error

#### Scenario: Browser close releases server resources
- **WHEN** a browser session, pane, stream, or WebSocket closes
- **THEN** the server releases associated private protocol subscriptions and host-side resource handles
- **AND THEN** the server does not stop the underlying Houmao agent solely because the GUI resource closed


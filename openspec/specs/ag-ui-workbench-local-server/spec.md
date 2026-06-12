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

### Requirement: Tmux attach bridge applies attachment resize messages
The workbench local server tmux bridge SHALL apply valid browser resize messages to the active tmux attachment.

Resize messages SHALL be scoped to the WebSocket attachment that received them.

The bridge SHALL reject or ignore resize messages that arrive before a tmux session is attached, after the attachment closes, or with invalid column or row values.

The bridge SHALL continue to report deterministic attachment errors instead of silently ending the WebSocket when resize handling fails.

#### Scenario: Resize after attach updates tmux pane size
- **WHEN** the browser attaches to a real tmux session through the workbench tmux WebSocket
- **AND WHEN** the browser sends a resize message with valid terminal columns and rows after the attachment succeeds
- **THEN** the server applies those columns and rows to the active tmux attachment
- **AND THEN** a host tmux pane-size query reports the requested size or the nearest size tmux can represent

#### Scenario: Resize before attach is rejected deterministically
- **WHEN** the browser opens a tmux attach WebSocket but has not attached to a session
- **AND WHEN** the browser sends a resize message
- **THEN** the server rejects or ignores the message deterministically as not attached
- **AND THEN** the server does not crash or mark an unrelated tmux session resized

### Requirement: Tmux bridge diagnostics distinguish attach exit from resize failure
The workbench local server SHALL emit deterministic tmux WebSocket error details for attach failure, attach process exit, invalid input, read-only input, and resize failure.

The browser SHALL be able to surface these details without conflating them all into a generic attachment-ended message.

#### Scenario: Resize failure is visible as resize failure
- **WHEN** a browser tmux attachment is active
- **AND WHEN** applying a valid resize message fails in the bridge
- **THEN** the server sends or records an error detail that identifies resize handling
- **AND THEN** the browser does not report only a generic `[tmux] attachment ended` message for that failure

### Requirement: Tmux bridge releases attach clients when attachments close
The workbench local server tmux bridge SHALL release the tmux attach client associated with a browser WebSocket attachment when that attachment closes.

The bridge SHALL perform this cleanup for client close messages, browser WebSocket close, WebSocket errors, and attach process exits.

The bridge SHALL release only the browser-owned tmux attach client and SHALL NOT stop, restart, shut down, interrupt, or kill the underlying tmux session or Houmao managed agent.

The bridge SHALL tolerate tmux detach cleanup failures by reporting or logging deterministic diagnostics without crashing the workbench server.

#### Scenario: Client close releases only the attach client
- **WHEN** a browser tmux WebSocket is attached to session `houmao-alpha`
- **AND WHEN** the browser sends a close message or closes the WebSocket
- **THEN** the server detaches or terminates the browser-owned tmux attach client for `houmao-alpha`
- **AND THEN** the underlying `houmao-alpha` tmux session remains alive

#### Scenario: Attach process exit does not stop the tmux session
- **WHEN** a tmux attach process exits for a browser attachment
- **THEN** the server cleans up that attachment's process and WebSocket state
- **AND THEN** the server does not issue tmux kill-session or any Houmao managed-agent lifecycle command

### Requirement: Tmux scroll commands are scoped to the owning attachment
The workbench local server tmux bridge SHALL execute scroll commands against the tmux session bound to the WebSocket attachment that received the scroll message.

The bridge SHALL reject or ignore scroll messages that arrive before a successful attach or after the attachment has been cleaned up.

The bridge SHALL keep mouse-wheel scroll handling server-side rather than forwarding raw wheel or copy-mode input through the PTY passthrough path.

#### Scenario: Scroll uses the WebSocket-bound session
- **WHEN** a browser WebSocket is attached to session `utility-shell`
- **AND WHEN** that WebSocket sends a scroll-up message
- **THEN** the server runs the tmux scroll operation against `utility-shell`
- **AND THEN** the server does not scroll any previous session that used the same workbench pane

#### Scenario: Scroll before attach is rejected
- **WHEN** a browser opens a tmux attach WebSocket but has not attached to a session
- **AND WHEN** the browser sends a scroll message
- **THEN** the server rejects or ignores the message deterministically as not attached
- **AND THEN** no tmux session receives a scroll command


## MODIFIED Requirements

### Requirement: Standalone AG-UI workbench app
The repository SHALL provide a standalone AG-UI workbench application under `apps/ag-ui-workbench/` for testing and operating Houmao AG-UI protocol behavior without including the GUI in the Python package distribution.

The workbench SHALL run as a single-user local web application with a TypeScript Fastify backend server and a browser frontend.

The user SHALL start the local workbench server and open the browser to that server's loopback port.

The workbench backend SHALL be part of the GUI product and SHALL NOT be treated as part of the Houmao Python package distribution.

#### Scenario: Workbench app lives outside Python package contents
- **WHEN** a developer inspects the workbench files and Python build configuration
- **THEN** the workbench is located under `apps/ag-ui-workbench/`
- **AND THEN** the Python wheel target continues to include only the Houmao Python package under `src/houmao`

#### Scenario: Workbench starts as a local server-backed app
- **WHEN** a developer follows the workbench README in a checkout with Bun available
- **THEN** the documented command starts the local Fastify-backed workbench server
- **AND THEN** the command does not require entering `pixi shell`
- **AND THEN** the browser frontend is served from the local workbench server origin

#### Scenario: Vite remains a frontend development tool
- **WHEN** a developer runs the workbench in development mode
- **THEN** Vite may serve or build frontend assets
- **AND THEN** host-side AG-UI, tmux, Debug Agent, proxy, and presentation-session behavior is owned by the local Fastify server rather than Vite-only plugins

### Requirement: Direct AG-UI client and event reduction
The workbench SHALL include AG-UI client behavior for Houmao capabilities, connect, run, detach, SSE parsing, stream abort, raw event recording, and reduced display state.

The local workbench backend SHALL own AG-UI gateway network access and target-policy enforcement.

The browser frontend SHALL request AG-UI actions through the workbench backend's private protocol rather than directly owning arbitrary Houmao gateway connections.

For watched targets, the workbench SHALL route connect-stream events through the watched-target cache and reducer rather than storing them only in pane-local state.

Visible panes SHALL render the reduced state for their selected target from cached events plus live watcher updates.

Normal agent panes SHALL keep transcripts and rendered artifacts visible by default and SHALL expose state snapshots, activity/custom records, tool-call records, and raw event timelines through on-demand diagnostics instead of an always-visible diagnostics panel.

#### Scenario: Capabilities are fetched before interaction
- **WHEN** a pane target is configured
- **THEN** the browser requests capability state through the local workbench backend
- **AND THEN** the backend requests AG-UI capabilities from the target after applying target-policy checks
- **AND THEN** the pane displays whether HTTP SSE, text input, state snapshots, generated graphics, frontend tool execution, state deltas, and multimodal input are reported as supported

#### Scenario: Connect attaches without prompt submission
- **WHEN** a user connects or watches a target without submitting a prompt
- **THEN** the workbench backend sends an AG-UI connect request rather than a run request
- **AND THEN** the target records state snapshot, activity, custom, text, tool-call, and error events received from that connection stream

#### Scenario: Run stream is reduced into visible state
- **WHEN** a run stream emits `RUN_STARTED`, text message events, state snapshot events, activity events, tool call events, custom events, and `RUN_FINISHED`
- **THEN** the workbench reduces those events into pane-visible state
- **AND THEN** normal agent panes expose state snapshot content, activity/custom records, tool-call records, and the raw event timeline through on-demand diagnostics

#### Scenario: Cached connect stream is reduced into visible state
- **WHEN** a watched connect stream receives state snapshot events, activity events, tool call events, custom events, and errors
- **THEN** the workbench stores those events in the explicit watched-target cache boundary
- **AND THEN** any pane for that target renders the reduced display state from those cached events

#### Scenario: Run error remains visible
- **WHEN** a target returns a pre-admission HTTP error or an admitted stream emits `RUN_ERROR`
- **THEN** the pane displays the error status and records enough raw event or response detail for debugging without crashing the workbench

#### Scenario: Message info opens scoped diagnostics
- **WHEN** a normal agent pane has at least one transcript message
- **AND WHEN** the user activates that message's info control
- **THEN** the pane opens a side inspector scoped to that message
- **AND THEN** the inspector shows deterministic diagnostics for the message and any related raw events, tool calls, activity/custom records, and current state snapshot evidence

### Requirement: Local AG-UI development proxy
The workbench SHALL provide a local AG-UI proxy through the Fastify backend for browser-origin workbench requests that need to reach Houmao AG-UI gateways.

The proxy SHALL preserve AG-UI HTTP and SSE semantics while restricting target URLs.

The proxy SHALL be available in development and production-like workbench modes and SHALL NOT depend on Vite middleware plugins as the authoritative implementation.

#### Scenario: Proxy preserves SSE stream behavior
- **WHEN** the browser requests a proxied AG-UI run or connect operation for an allowed target that returns `text/event-stream`
- **THEN** the Fastify proxy forwards the upstream status, content type, and SSE bytes to the browser without buffering the full stream

#### Scenario: Proxy rejects disallowed targets
- **WHEN** a pane attempts to proxy an AG-UI request to a non-loopback or otherwise disallowed target
- **THEN** the Fastify proxy rejects the request before contacting the target
- **AND THEN** the workbench displays a deterministic target-policy error

#### Scenario: Browser abort aborts upstream request
- **WHEN** the browser aborts an in-flight proxied connect or run request
- **THEN** the Fastify proxy aborts the upstream request and releases stream resources

### Requirement: Deterministic browser E2E coverage
The repository SHALL include deterministic browser E2E coverage for the workbench using Bun-global Playwright and Fastify-backed local server fixtures.

The test harness SHALL start the local workbench server rather than relying on Vite middleware plugins as the only backend surface.

The deterministic fixture path SHALL cover AG-UI, Debug Agent, tmux bridge, and server teardown behavior without requiring live Houmao agents.

#### Scenario: E2E validates multi-pane flow
- **WHEN** the workbench E2E smoke runs against deterministic Fastify-backed fixtures
- **THEN** it adds at least two agent panes, moves a pane into an in-app split, connects panes independently, submits at least one run, and verifies visible transcript or status evidence for each target

#### Scenario: E2E validates graphics and detach behavior
- **WHEN** the deterministic fixture emits a `houmao_render_graphic` sequence and the test closes or disconnects a pane
- **THEN** the test verifies visible graphic evidence
- **AND THEN** the test verifies the browser-side detach or abort path without expecting a Houmao interrupt request

#### Scenario: E2E validates server-owned host integrations
- **WHEN** the workbench E2E suite exercises AG-UI proxy, Debug Agent, or tmux bridge behavior
- **THEN** the requests are served by the Fastify local server
- **AND THEN** the test does not depend on Vite-only plugin routes for host integration behavior

## MODIFIED Requirements

### Requirement: Runtime owns long-lived workbench lifecycles
The AG-UI workbench browser runtime SHALL own long-lived browser lifecycle workflows that can outlive a single React render.

Runtime-owned browser workflows SHALL include pane view-state updates, watched-target presentation state, browser subscriptions to local server streams, browser WebSocket lifecycle, browser-side stream cancellation, watched-target cache writes, runtime teardown, tmux terminal sink registration, and active-thread view-model updates.

The local Fastify server SHALL own host-side workflows, including Houmao AG-UI gateway HTTP/SSE clients, target-policy checks, Debug Agent fixture behavior, tmux host bridge processes, and presentation-session lifecycle.

React components SHALL dispatch typed runtime actions for browser workflows and SHALL render runtime-derived view models through selectors.

#### Scenario: Pane run lifecycle is coordinated through runtime and server
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action
- **AND THEN** the browser runtime sends a private workbench command to the local server
- **AND THEN** the local server owns the Houmao AG-UI run stream to the target gateway
- **AND THEN** the browser runtime tracks, reduces, and cancels the pane-visible subscription state

#### Scenario: Runtime teardown stops browser workflows
- **WHEN** the browser workbench runtime is disposed
- **THEN** active browser subscriptions, reconnect timers, browser WebSocket streams, and pending browser cache effects are stopped
- **AND THEN** the local server receives connection close or cancellation signals for matching server-owned resources

#### Scenario: Server teardown stops host workflows
- **WHEN** the local Fastify workbench server shuts down
- **THEN** server-owned AG-UI streams, tmux bridge resources, Debug Agent fixtures, and presentation sessions are closed or released deterministically
- **AND THEN** the server does not stop or interrupt Houmao agents solely because the GUI server shut down

### Requirement: Runtime exposes typed actions, selectors, and services
The browser runtime SHALL define typed actions for pane lifecycle, target changes, watched-target storage snapshots, watched-target cache clear requests, AG-UI connect requests, AG-UI run requests, AG-UI stream cancellation, tmux refresh requests, tmux attach requests, tmux input, tmux resize, tmux detach, active-thread requests, and runtime disposal.

The runtime SHALL expose selectors for panes, watched targets, AG-UI stream status, reduced AG-UI event state, tmux status, tmux sessions, tmux attachment state, active-thread state, and runtime errors.

The runtime SHALL accept service interfaces for local server HTTP, local server WebSocket, storage, cache, timer, and browser stream work so tests can run with deterministic fakes.

Services that previously contacted Houmao gateways or host tmux resources directly SHALL be routed through local Fastify server APIs after equivalent server APIs exist.

#### Scenario: Target change dispatches one typed action
- **WHEN** a pane changes from one AG-UI target to another
- **THEN** the component dispatches a typed target-change action
- **AND THEN** runtime effects cancel obsolete browser subscriptions and start required browser subscriptions for the new target

#### Scenario: Component reads derived runtime status
- **WHEN** a pane needs AG-UI stream status or tmux attach status
- **THEN** it reads that status through a runtime selector
- **AND THEN** it does not subscribe directly to internal runtime subjects

#### Scenario: Runtime service talks to local server
- **WHEN** the browser runtime needs capabilities, connect, run, detach, tmux inventory, or tmux attachment behavior after the Fastify API exists
- **THEN** it calls a typed local-server service
- **AND THEN** it does not construct direct host-integration or arbitrary gateway requests inside React components

### Requirement: Tmux effects use ephemeral terminal output sinks
The runtime SHALL own browser-side tmux status presentation, tmux session selection state, tmux attach WebSocket client lifecycle, tmux input commands, tmux resize commands, tmux detach requests, and terminal output sink registration.

The local Fastify server SHALL own host-side tmux inventory lookup, tmux process attachment, read-only enforcement at the host bridge boundary, and tmux bridge teardown.

React tmux panes SHALL keep xterm `Terminal`, `FitAddon`, and DOM refs outside runtime state and SHALL register an ephemeral output sink for the active attachment.

The runtime SHALL drop or report terminal output when no matching sink is registered, but SHALL NOT persist or replay raw terminal bytes.

#### Scenario: Tmux attach writes to registered sink
- **WHEN** a tmux pane attaches to a session and registers a terminal sink
- **AND WHEN** the browser runtime receives terminal output for that attachment from the local server
- **THEN** the runtime writes the output to the registered sink
- **AND THEN** the runtime updates attachment status without storing raw terminal output

#### Scenario: Pane close cleans up tmux attachment
- **WHEN** a tmux pane with an active attachment closes
- **THEN** the runtime closes the browser-side attachment WebSocket or sends a detach command to the local server
- **AND THEN** the runtime unregisters the terminal output sink
- **AND THEN** later WebSocket events cannot write to the removed pane

#### Scenario: Host tmux bridge enforces read-only mode
- **WHEN** a tmux pane attaches in read-only mode
- **THEN** the local Fastify server's tmux bridge rejects or ignores input messages for that attachment
- **AND THEN** the browser runtime also suppresses terminal input for that attachment

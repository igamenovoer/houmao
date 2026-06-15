## ADDED Requirements

### Requirement: Agent panes delegate AG-UI lifecycles to runtime
Agent panes SHALL delegate long-lived AG-UI lifecycle ownership to the workbench runtime.

Agent panes SHALL dispatch runtime actions for target changes, connect/watch requests, run requests, stream cancellation, clear-canvas requests, and pane disposal.

Agent panes SHALL keep UI-local concerns such as prompt editor state, target form editing, measured canvas size, and rendered DOM outside the runtime lifecycle effects.

Agent panes SHALL NOT keep component-local reconnect timers, stream abort refs, connection ids, or duplicated connect/run status after the equivalent workflow has moved into the runtime.

#### Scenario: Agent pane connect uses runtime action
- **WHEN** a user connects an agent pane to a target
- **THEN** the pane dispatches a runtime connect or watch action for that target
- **AND THEN** runtime effects own passive resolution, AG-UI connect stream startup, reconnect behavior, and detach cleanup

#### Scenario: Agent pane run uses runtime action
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action containing the submitted message and compact canvas-size context when available
- **AND THEN** runtime effects own the AG-UI run stream and reduce the received events into pane-visible state

#### Scenario: Pane close cancels pane-owned AG-UI streams
- **WHEN** an agent pane with a live pane-owned run stream closes
- **THEN** the pane dispatches disposal to the runtime
- **AND THEN** runtime effects abort that pane-owned stream without stopping watched-target listeners still required by storage state

### Requirement: Tmux panes delegate tmux lifecycles to runtime
Tmux panes SHALL delegate tmux status refresh, tmux session refresh, discovered Houmao agent refresh, tmux attach WebSocket lifecycle, tmux input, tmux resize, and tmux detach to the workbench runtime.

Tmux panes SHALL keep xterm `Terminal`, `FitAddon`, DOM refs, layout measurement, and direct terminal rendering outside reduced runtime state.

Tmux panes SHALL register and unregister an ephemeral terminal output sink for the active runtime attachment.

#### Scenario: Tmux refresh uses runtime selector
- **WHEN** a user opens or refreshes a tmux pane
- **THEN** the pane dispatches a runtime refresh action
- **AND THEN** the pane renders tmux status, session list, discovered-agent list, loading state, and errors from runtime selectors

#### Scenario: Tmux attach keeps terminal DOM local
- **WHEN** a user attaches to a tmux session
- **THEN** the pane creates or reuses its xterm DOM objects locally
- **AND THEN** runtime effects own the WebSocket and send terminal output to the pane through the registered sink

### Requirement: Runtime migration preserves pane-visible behavior
The runtime lifecycle refactor SHALL preserve existing workbench pane behavior unless this change explicitly changes ownership.

Agent panes SHALL continue to render transcripts, Houmao graphics, typed components, state snapshots, activity, custom events, raw event timelines, visible errors, and active-thread status.

Tmux panes SHALL continue to list sessions, search/filter sessions, filter Houmao agent sessions, attach read-write by default, support read-only attachment, send input only for read-write attachment, and show attach status.

#### Scenario: Graphics remain visible after runtime migration
- **WHEN** an AG-UI stream emits a valid Houmao chart or graphic event sequence
- **THEN** the agent pane renders the graphic from reduced runtime event state
- **AND THEN** the migration does not require a gateway protocol change

#### Scenario: Read-only tmux attach suppresses input
- **WHEN** a tmux pane is attached in read-only mode
- **AND WHEN** the user types in the terminal
- **THEN** the pane does not dispatch tmux input to the runtime attachment
- **AND THEN** output received from the tmux session remains visible

## MODIFIED Requirements

### Requirement: Direct AG-UI client and event reduction
The workbench SHALL include direct AG-UI client behavior for Houmao capabilities, connect, run, detach, SSE parsing, stream abort, raw event recording, and reduced display state.

For watched targets, the workbench SHALL route connect-stream events through the watched-target cache and reducer rather than storing them only in pane-local state.

Visible panes SHALL render the reduced state for their selected target from cached events plus live watcher updates.

Normal agent panes SHALL keep transcripts and rendered artifacts visible by default and SHALL expose state snapshots, activity/custom records, tool-call records, and raw event timelines through on-demand diagnostics instead of an always-visible diagnostics panel.

#### Scenario: Capabilities are fetched before interaction
- **WHEN** a pane target is configured
- **THEN** the workbench can request AG-UI capabilities for that target
- **AND THEN** the pane displays whether HTTP SSE, text input, state snapshots, generated graphics, frontend tool execution, state deltas, and multimodal input are reported as supported

#### Scenario: Connect attaches without prompt submission
- **WHEN** a user connects or watches a target without submitting a prompt
- **THEN** the workbench sends an AG-UI connect request rather than a run request
- **AND THEN** the target records state snapshot, activity, custom, text, tool-call, and error events received from that connection stream

#### Scenario: Run stream is reduced into visible state
- **WHEN** a run stream emits `RUN_STARTED`, text message events, state snapshot events, activity events, tool call events, custom events, and `RUN_FINISHED`
- **THEN** the pane shows run status and transcript messages in the main display
- **AND THEN** normal agent panes expose state snapshot content, activity/custom records, tool-call records, and the raw event timeline through on-demand diagnostics

#### Scenario: Cached connect stream is reduced into visible state
- **WHEN** a watched connect stream receives state snapshot events, activity events, tool call events, custom events, and errors
- **THEN** the workbench stores those events in the client cache
- **AND THEN** any pane for that target renders the reduced display state from those cached events

#### Scenario: Run error remains visible
- **WHEN** a target returns a pre-admission HTTP error or an admitted stream emits `RUN_ERROR`
- **THEN** the pane displays the error status and records enough raw event or response detail for debugging without crashing the workbench

#### Scenario: Message info opens scoped diagnostics
- **WHEN** a normal agent pane has at least one transcript message
- **AND WHEN** the user activates that message's info control
- **THEN** the pane opens a side inspector scoped to that message
- **AND THEN** the inspector shows deterministic diagnostics for the message and any related raw events, tool calls, activity/custom records, and current state snapshot evidence

### Requirement: Workbench lists and searches tmux sessions
The workbench SHALL provide a local tmux session picker for tmux tabs.

The picker SHALL be presented as a top-placed searchable combobox/dropdown so the tmux terminal can use the pane's full content width.

The picker SHALL list local tmux sessions available to the host running the workbench development server when the user opens the dropdown or explicitly refreshes the picker.

The picker SHALL support quick fuzzy search using Fuse.js while the user types in the combobox input.

The searchable fields SHALL include tmux session name and matched Houmao agent metadata when available, including agent name, agent id, tool, backend, and generation id.

The picker SHALL provide a checkbox filter that shows only tmux sessions matched to Houmao managed agents.

The workbench SHALL NOT require a persistent left-side tmux session list for normal tmux attachment.

#### Scenario: Picker lists local tmux sessions on open
- **WHEN** tmux is available and the host has local tmux sessions
- **AND WHEN** the user opens the tmux session combobox
- **THEN** the tmux picker refreshes inventory and displays matching sessions with at least session name, window count, attached status, and created time

#### Scenario: Picker degrades when tmux is unavailable
- **WHEN** tmux is unavailable on the host running the workbench development server
- **AND WHEN** the user opens the tmux session combobox
- **THEN** the tmux picker shows a deterministic unavailable or empty state
- **AND THEN** the workbench does not crash

#### Scenario: Search matches tmux and Houmao fields
- **WHEN** a developer types a search query matching a session name or matched Houmao agent metadata into the combobox
- **THEN** the tmux picker filters the visible dropdown rows using Fuse.js fuzzy search
- **AND THEN** non-matching sessions are hidden while the query is active

#### Scenario: Houmao-only filter hides non-agent sessions
- **WHEN** the tmux picker has the Houmao-only checkbox enabled
- **THEN** the picker shows only tmux sessions whose session name matches a discovered Houmao agent `tmux_session_name`
- **AND THEN** tmux sessions without a matched Houmao agent are hidden

#### Scenario: Houmao-only filter handles discovery outage
- **WHEN** passive-server agent discovery is unavailable
- **AND WHEN** the Houmao-only checkbox is enabled
- **THEN** the picker shows a deterministic no-matched-Houmao-sessions or discovery-error state
- **AND THEN** disabling the checkbox still allows raw tmux sessions to be listed when tmux itself is available

#### Scenario: Selecting dropdown row attaches session
- **WHEN** a developer selects a tmux session row from the combobox dropdown
- **THEN** the tmux tab attaches to that selected session using the currently selected read-only/read-write mode
- **AND THEN** the dropdown closes and the full-width terminal remains available for session output

### Requirement: Agent panes expose explicit active-thread controls
The workbench SHALL provide an active-thread control or marker on each eligible Houmao agent pane.

The control SHALL be eligible only when the pane targets a discovered Houmao agent gateway that supports the Houmao active-thread extension.

The active-thread control SHALL show an inactive gray state when the pane's thread is not the gateway active thread.

The active-thread control SHALL show an active green state when the pane's thread matches the gateway active thread.

The active-thread control SHALL show a deterministic unavailable or error state when the workbench cannot read active-thread status from a gateway that previously appeared to support active-thread.

The active-thread control SHALL show a deterministic unsupported state, or be disabled with unsupported text, when the gateway responds as if `/active-thread` is not implemented.

The active-thread presentation SHALL NOT label a pane inactive merely because the gateway does not support the active-thread extension.

Activating the control from an inactive eligible pane SHALL set the gateway active-thread to that pane's current thread id.

#### Scenario: User marks a pane as active thread
- **WHEN** a developer has an eligible Houmao agent pane whose active-thread control is gray
- **AND WHEN** the developer activates the control
- **THEN** the workbench sends the gateway an active-thread update for that pane's current thread id
- **AND THEN** the pane's control becomes green after the gateway reports that thread as active

#### Scenario: Active marker moves between panes
- **WHEN** two eligible panes target the same gateway with different thread ids
- **AND WHEN** the developer marks the second pane active
- **THEN** the second pane shows the active green state
- **AND THEN** the first pane shows the inactive gray state after the next active-thread status update

#### Scenario: Unsupported gateway is not shown as inactive
- **WHEN** a discovered agent pane targets a live gateway whose `/active-thread` route returns `404` or `405`
- **THEN** the pane shows active-thread as unsupported or disabled
- **AND THEN** the pane does not show `Inactive thread` with an active-thread error for that unsupported extension

### Requirement: Active-thread status is polled and reflected in pane UI
The workbench SHALL poll each interested gateway's active-thread status periodically when that gateway is eligible and not known to be unsupported.

The default poll interval SHALL be 1 second.

The workbench SHALL update eligible pane active-thread presentation from the polled gateway state.

The polling implementation SHALL be shared per gateway rather than duplicated per pane.

The workbench SHALL stop active-thread polling for a gateway after the gateway is classified as unsupported until the pane target or gateway key changes.

The workbench SHALL avoid UI flicker caused by overlapping or aborting active-thread polls under ordinary slow-response conditions.

#### Scenario: External active-thread change updates pane controls
- **WHEN** an external caller changes the gateway active-thread
- **THEN** the workbench reflects the new active-thread state in eligible pane controls after the next poll

#### Scenario: Poll failure is visible without disconnecting pane stream
- **WHEN** active-thread polling fails for a gateway that is not known to be unsupported
- **THEN** panes for that gateway show a deterministic unavailable or error state for active-thread
- **AND THEN** existing AG-UI streams for those panes remain connected unless they fail independently

#### Scenario: Unsupported active-thread extension stops polling
- **WHEN** active-thread polling receives a deterministic unsupported-route response such as `404` or `405`
- **THEN** the workbench marks active-thread unsupported for that gateway
- **AND THEN** the workbench stops scheduling active-thread polls for that gateway until the target or gateway key changes

#### Scenario: Slow poll does not flash error
- **WHEN** an active-thread poll takes longer than the default poll interval but eventually succeeds
- **THEN** the pane does not flash an active-thread error caused only by the next scheduled poll tick
- **AND THEN** the pane updates from the successful poll result

### Requirement: Tmux panes delegate tmux lifecycles to runtime
Tmux panes SHALL delegate tmux status refresh, tmux session refresh, discovered Houmao agent refresh, tmux attach WebSocket lifecycle, tmux input, tmux resize, and tmux detach to the workbench runtime.

Tmux panes SHALL keep xterm `Terminal`, `FitAddon`, DOM refs, layout measurement, and direct terminal rendering outside reduced runtime state.

Tmux panes SHALL register and unregister an ephemeral terminal output sink for the active runtime attachment.

#### Scenario: Tmux picker refresh uses runtime selector
- **WHEN** a user opens or refreshes the tmux session combobox
- **THEN** the pane dispatches a runtime refresh action
- **AND THEN** the pane renders tmux status, session list, discovered-agent list, loading state, and errors from runtime selectors

#### Scenario: Tmux attach keeps terminal DOM local
- **WHEN** a user attaches to a tmux session
- **THEN** the pane creates or reuses its xterm DOM objects locally
- **AND THEN** runtime effects own the WebSocket and send terminal output to the pane through the registered sink

### Requirement: Runtime migration preserves pane-visible behavior
The runtime lifecycle refactor SHALL preserve existing workbench pane behavior unless this change explicitly changes ownership or presentation.

Agent panes SHALL continue to render transcripts, Houmao graphics, typed components, visible errors, and active-thread status.

Normal agent panes SHALL expose state snapshots, activity, custom events, raw event timelines, and per-message tool-call evidence through the on-demand message diagnostics inspector.

Tmux panes SHALL continue to search/filter sessions, filter Houmao agent sessions, attach read-write by default, support read-only attachment, send input only for read-write attachment, and show attach status through the top session combobox and full-width terminal layout.

#### Scenario: Graphics remain visible after runtime migration
- **WHEN** an AG-UI stream emits a valid Houmao chart or graphic event sequence
- **THEN** the agent pane renders the graphic from reduced runtime event state
- **AND THEN** the migration does not require a gateway protocol change

#### Scenario: Read-only tmux attach suppresses input
- **WHEN** a tmux pane is attached in read-only mode
- **AND WHEN** the user types in the terminal
- **THEN** the pane does not dispatch tmux input to the runtime attachment
- **AND THEN** output received from the tmux session remains visible

#### Scenario: Normal agent diagnostics are available on demand
- **WHEN** a normal agent pane receives state snapshots, activity records, tool calls, and raw events
- **AND WHEN** the user opens a transcript message info inspector
- **THEN** the pane shows diagnostics related to the selected message without requiring the default transcript layout to reserve a permanent diagnostics column

### Requirement: Tmux tabs fill available workspace height
Tmux tabs SHALL make the terminal attachment area consume the remaining vertical space inside the Dockview panel after fixed tmux controls are laid out.

Tmux tabs SHALL make the terminal attachment area consume the pane's available content width instead of reserving a permanent side column for tmux sessions.

Tmux tabs SHALL refit the visible xterm terminal when the browser viewport, Dockview panel, or terminal host size changes.

Session discovery controls and dropdown lists SHALL remain usable without causing the attached terminal to shrink below the available panel area.

#### Scenario: Browser resize refits tmux terminal
- **WHEN** a tmux tab is attached to a session
- **AND WHEN** the browser window or Dockview panel is resized
- **THEN** the tmux tab refits the terminal to the new visible terminal host size
- **AND THEN** the runtime receives the updated terminal columns and rows for the active attachment

#### Scenario: Tmux terminal consumes remaining panel height and width
- **WHEN** a developer opens a tmux tab in a tall or wide Dockview panel
- **THEN** the terminal attachment area expands to use the vertical space not needed by the header, picker, and fixed controls
- **AND THEN** the terminal attachment area expands to use the pane width not needed by fixed controls
- **AND THEN** the tmux tab does not leave an unused side list or footer area that prevents the terminal from filling the pane

### Requirement: Tmux session lists remove dead sessions
The workbench SHALL remove a tmux session from visible tmux session picker results after the host tmux bridge reports that the session no longer exists.

The workbench SHALL refresh tmux session inventory after a tmux attachment exits or disconnects, when the user opens the session combobox, and when the user explicitly refreshes the picker.

If an attached session exits, the tmux tab SHALL mark the attachment disconnected, preserve any terminal output already written to the xterm instance, and update the next shown session list without sending a Houmao agent lifecycle command or tmux kill command.

#### Scenario: Session closed from attached terminal disappears from list
- **WHEN** a user is attached to tmux session `HOUMAO-alpha` in a workbench tmux tab
- **AND WHEN** the user exits the session from inside the terminal
- **THEN** the tab marks the attachment disconnected
- **AND THEN** the next tmux session list shown by the workbench does not include `HOUMAO-alpha`
- **AND THEN** the workbench does not send any Houmao stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control request

#### Scenario: Externally killed tmux session disappears from list
- **WHEN** the tmux session picker previously listed tmux session `HOUMAO-beta`
- **AND WHEN** that session is killed outside the browser
- **AND WHEN** the user next opens or refreshes the tmux session picker
- **THEN** the workbench removes `HOUMAO-beta` from the visible session list

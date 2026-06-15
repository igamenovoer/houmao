## MODIFIED Requirements

### Requirement: Docked multi-agent panes
The workbench SHALL use a dockable pane layout where each agent pane can be added, removed, moved within the main workbench, and configured independently for one running Houmao agent or watched AG-UI target.

Agent panes SHALL be presentation surfaces for target event state. They SHALL NOT be the only ownership boundary for a watched target's background AG-UI listener.

#### Scenario: User can add multiple panes
- **WHEN** a developer clicks the add-pane control
- **THEN** the workbench creates a new docked agent pane with its own target configuration and event state

#### Scenario: User can move panes within the docked layout
- **WHEN** a developer drags an agent pane tab or group in the workbench
- **THEN** the pane can be moved into another tab group or into an in-app split position above, below, left, or right of another group
- **AND THEN** the pane remains inside the main workbench browser page

#### Scenario: Floating and popout panes are unavailable
- **WHEN** a developer uses the workbench pane controls, tab context menu, drag behavior, and restored saved layouts
- **THEN** the workbench does not create Dockview floating groups
- **AND THEN** the workbench does not create Dockview popout windows or require a `popout.html` page

#### Scenario: Each pane presents its selected target independently
- **WHEN** two panes are configured with different AG-UI targets and both targets have event state
- **THEN** each pane presents only the cached and live events for its own target
- **AND THEN** events received by one target do not appear in the other pane's transcript, state view, or raw event list

#### Scenario: Pane close does not stop watched target listener
- **WHEN** a pane presenting a watched target is closed
- **THEN** the workbench removes that pane from the docked layout
- **AND THEN** the watched target listener remains active when the target is still marked watched
- **AND THEN** the workbench does not send any Houmao lifecycle stop, restart, shutdown, or interrupt request

#### Scenario: Explicit unwatch disconnects listener without controlling agent
- **WHEN** a tester explicitly unwatches or disconnects a watched target
- **THEN** the workbench aborts that target's active browser stream and performs explicit AG-UI connection cleanup when a connection id is available
- **AND THEN** the workbench does not send any Houmao lifecycle stop, restart, shutdown, or interrupt request

### Requirement: Direct AG-UI client and event reduction
The workbench SHALL include direct AG-UI client behavior for Houmao capabilities, connect, run, detach, SSE parsing, stream abort, raw event recording, and reduced display state.

For watched targets, the workbench SHALL route connect-stream events through the watched-target cache and reducer rather than storing them only in pane-local state.

Visible panes SHALL render the reduced state for their selected target from cached events plus live watcher updates.

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
- **THEN** the pane shows run status, transcript messages, state snapshot content, activity/custom records, tool-call records, and the raw event timeline

#### Scenario: Cached connect stream is reduced into visible state
- **WHEN** a watched connect stream receives state snapshot events, activity events, tool call events, custom events, and errors
- **THEN** the workbench stores those events in the client cache
- **AND THEN** any pane for that target renders the reduced display state from those cached events

#### Scenario: Run error remains visible
- **WHEN** a target returns a pre-admission HTTP error or an admitted stream emits `RUN_ERROR`
- **THEN** the pane displays the error status and records enough raw event or response detail for debugging without crashing the workbench

### Requirement: Workbench persistence boundary
The workbench SHALL persist layout and non-sensitive configuration in localStorage or an equivalent browser configuration store.

The workbench SHALL persist AG-UI stream events only in the client-owned event cache for watched targets.

The workbench SHALL NOT store stream content in localStorage by default.

The workbench SHALL NOT persist discovered-agent list responses, gateway-status response bodies, prompt text, AG-UI request bodies, forwarded props, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Layout and target metadata persist
- **WHEN** a developer creates panes, moves them, assigns labels, configures target URLs, and watches targets
- **THEN** the workbench can restore the pane layout, target metadata, and watched-target metadata after a browser reload
- **AND THEN** restored layout state contains only docked grid groups, not floating groups or popout groups

#### Scenario: Watched stream content persists only in client event cache
- **WHEN** a watched target receives messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench stores those received stream events in the client-owned event cache
- **AND THEN** the workbench does not store those stream contents in localStorage

#### Scenario: Unwatched pane stream content is not persisted by default
- **WHEN** an unwatched pane receives prompts, messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench does not persist those stream contents to localStorage by default
- **AND THEN** the workbench persists them in the client event cache only after the target is watched

## REMOVED Requirements

### Requirement: Workbench reconnect uses event cursors when supported
**Reason**: Gateway-published GUI events are no longer replayable from the gateway. The workbench owns retention for events it received, so reconnects must resume live listening without asking the gateway to fill missed ranges.

**Migration**: Remove pane-level `lastSeenEventId` replay behavior. Use the watched-target client cache for previously received events and reopen connect streams without replay cursors.

#### Scenario: Reconnect does not send last seen event id
- **WHEN** a watched target reconnects after receiving cached AG-UI events
- **THEN** the connect request does not include `lastSeenEventId` as a gateway replay cursor
- **AND THEN** the pane renders previously received events from the client cache

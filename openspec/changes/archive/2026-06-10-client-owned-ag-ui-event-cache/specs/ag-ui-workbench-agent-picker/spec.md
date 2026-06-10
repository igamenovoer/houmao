## ADDED Requirements

### Requirement: Agent picker can watch targets without opening panes
The workbench agent picker SHALL let a tester mark a discovered agent and thread as watched without creating a visible pane.

The picker SHALL also let a tester open a pane for an already watched target.

The picker SHALL expose unwatch as an explicit action distinct from closing a pane.

Watch and unwatch actions SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control requests.

#### Scenario: Watch discovered agent without pane
- **WHEN** the picker lists discovered agent `abc123`
- **AND WHEN** the tester chooses the watch action for `abc123` and thread `thread-1`
- **THEN** the workbench adds a watched target for `abc123` and `thread-1`
- **AND THEN** it does not create a Dockview pane unless the tester also chooses to open one

#### Scenario: Open pane for watched target
- **WHEN** discovered agent `abc123` is already watched
- **AND WHEN** the tester chooses to open a pane for `abc123`
- **THEN** the workbench creates a docked pane presenting the watched target
- **AND THEN** the pane renders any cached events already received for that target

#### Scenario: Unwatch is separate from pane close
- **WHEN** a pane presenting watched agent `abc123` is open
- **AND WHEN** the tester closes the pane
- **THEN** the watched target remains watched
- **AND WHEN** the tester chooses unwatch for `abc123`
- **THEN** the workbench closes the background watcher stream for that target

### Requirement: Picker displays watched-target state for discovered agents
The picker SHALL show whether a discovered agent/thread is watched, connected, reconnecting, offline, or unwatched.

The watched state SHALL be derived from the workbench watched-target registry and watcher status.

When a discovered agent is watched by durable `agent_id`, a later gateway host or port change SHALL NOT create a second watched target for the same agent/thread.

#### Scenario: Watched agent appears in picker
- **WHEN** agent `abc123` is watched
- **AND WHEN** the tester opens the picker
- **THEN** the picker shows `abc123` as watched
- **AND THEN** the picker exposes its watcher status

#### Scenario: Gateway change preserves watched identity
- **WHEN** watched agent `abc123` restarts on a different gateway port
- **AND WHEN** the passive server reports the new gateway for `abc123`
- **THEN** the picker still shows one watched entry for `abc123`
- **AND THEN** it does not duplicate the watched target by gateway URL

### Requirement: Picker persists watched target metadata safely
The workbench SHALL persist watched target metadata needed to restore background listeners after browser reload.

Persisted watched metadata SHALL include passive-server base URL when needed, durable agent address, canonical `agent_id` when known, canonical `agent_name` when known, thread id, target label, and safe display metadata.

Persisted watched metadata SHALL NOT include gateway status bodies, discovered-agent list responses, streamed AG-UI events, transcript content, component payloads, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Browser reload restores watched target
- **WHEN** a tester watches agent `abc123` and thread `thread-1`
- **AND WHEN** the browser reloads the workbench
- **THEN** the watched target metadata is restored
- **AND THEN** the watcher resolves the current gateway through the passive server before connecting

#### Scenario: Persisted watch metadata excludes stream payloads
- **WHEN** a watched target receives chart and table events
- **AND WHEN** the workbench persists watched target metadata
- **THEN** the metadata does not include the chart or table payloads
- **AND THEN** stream events are stored only in the client-owned event cache

## ADDED Requirements

### Requirement: Agent panes expose explicit active-thread controls
The workbench SHALL provide an active-thread control on each eligible Houmao agent pane.

The control SHALL be eligible only when the pane targets a discovered Houmao agent gateway that supports the Houmao active-thread extension.

The active-thread control SHALL show an inactive gray state when the pane's thread is not the gateway active thread.

The active-thread control SHALL show an active green state when the pane's thread matches the gateway active thread.

The active-thread control SHALL show a deterministic unavailable or error state when the workbench cannot read active-thread status from the gateway.

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

### Requirement: Connect marks eligible pane active automatically
When a user connects an eligible discovered Houmao agent pane, the workbench SHALL set that pane's current thread as the gateway active-thread with source `gui_connect`.

Background watchers, passive reconnects, hidden panes, and client event-cache listeners SHALL NOT set active-thread merely because they open or reopen an AG-UI stream.

#### Scenario: Connect auto-activates pane thread
- **WHEN** a developer clicks Connect on an eligible discovered Houmao agent pane
- **THEN** the workbench sets the gateway active-thread to that pane's current thread id
- **AND THEN** the normal AG-UI connect request remains metadata-minimal

#### Scenario: Background watcher does not steal active thread
- **WHEN** one pane is active for a gateway
- **AND WHEN** a watched target for another thread on the same gateway reconnects in the background
- **THEN** the gateway active-thread remains the foreground pane's active thread

### Requirement: Active-thread status is polled and reflected in pane UI
The workbench SHALL poll each interested gateway's active-thread status periodically.

The default poll interval SHALL be 1 second.

The workbench SHALL update eligible pane active-thread presentation from the polled gateway state.

The polling implementation SHALL be shared per gateway rather than duplicated per pane.

#### Scenario: External active-thread change updates pane controls
- **WHEN** an external caller changes the gateway active-thread
- **THEN** the workbench reflects the new active-thread state in eligible pane controls after the next poll

#### Scenario: Poll failure is visible without disconnecting pane stream
- **WHEN** active-thread polling fails for a gateway
- **THEN** panes for that gateway show a deterministic unavailable or error state for active-thread
- **AND THEN** existing AG-UI streams for those panes remain connected unless they fail independently

### Requirement: Inactive panes still render explicitly addressed AG-UI events
The workbench SHALL treat active-thread as a default destination marker only.

Inactive panes SHALL continue to receive, reduce, cache when watched, and render AG-UI events that are explicitly addressed to their target thread.

Inactive panes SHALL NOT be hidden, disconnected, cleared, or prevented from rendering merely because another pane is active.

#### Scenario: Inactive pane renders explicit publish
- **WHEN** pane alpha is the active thread for a gateway
- **AND WHEN** pane beta is connected to the same gateway with thread id `beta-thread`
- **AND WHEN** an agent publishes AG-UI events with explicit `threadId = "beta-thread"`
- **THEN** pane beta receives and renders those events
- **AND THEN** pane alpha remains the gateway active thread

### Requirement: Active-thread clear is conditional when pane ownership is stale
When a pane closes or retargets away, the workbench SHALL clear gateway active-thread only if the gateway still reports the pane's old thread as active.

The workbench SHALL NOT clear a newer active-thread value set by another pane.

#### Scenario: Closing stale pane does not clear newer active thread
- **WHEN** pane alpha was active
- **AND WHEN** pane beta becomes active for the same gateway
- **AND WHEN** pane alpha closes
- **THEN** the workbench does not clear pane beta's active-thread state


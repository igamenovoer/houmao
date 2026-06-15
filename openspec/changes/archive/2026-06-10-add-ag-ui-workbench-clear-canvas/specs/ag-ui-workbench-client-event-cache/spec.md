## ADDED Requirements

### Requirement: Watched target clear-canvas resets cache and runtime display state
When an agent pane presents a watched target, the workbench SHALL make the pane's clear-canvas control clear the watched target's browser-owned cached stream events and reset the watched target's in-memory reduced display state.

Clear-canvas SHALL preserve the watched target registration, active watcher connection when present, reconnect loop, resolved target metadata, and future event caching behavior.

Clear-canvas SHALL NOT request gateway replay, gateway deletion, or managed agent lifecycle changes.

#### Scenario: Watched chart does not reappear after clear and reopen
- **WHEN** a watched target has cached AG-UI events that render a Houmao chart
- **AND WHEN** a tester clears the canvas from an agent pane presenting that target
- **AND WHEN** the tester closes and reopens a pane for the same watched target
- **THEN** the previously cached chart does not reappear
- **AND THEN** the watched target remains available for future live AG-UI events

#### Scenario: Clear watched target affects all panes for that target
- **WHEN** two visible agent panes present the same watched target
- **AND WHEN** one pane clears the canvas
- **THEN** cached watched-target evidence is removed from both panes
- **AND THEN** pane-local output that belongs only to the other pane is not cleared by the watched-target cache reset

#### Scenario: Clear keeps watcher connected
- **WHEN** a watched target has an active AG-UI connect stream
- **AND WHEN** the tester clears the canvas
- **THEN** the watcher remains watched and connected or reconnecting according to its current network state
- **AND THEN** future live events from the same stream or a later reconnect are cached and rendered normally

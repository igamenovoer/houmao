## ADDED Requirements

### Requirement: Agent pane can clear visible AG-UI canvas
The workbench SHALL provide a clear-canvas control on agent panes.

The clear-canvas control SHALL clear the pane's client-side AG-UI display evidence, including transcript messages, rendered graphics/tool calls, state snapshot, activity/custom records, raw timeline entries, and visible errors.

The clear-canvas control SHALL preserve target configuration, prompt text, active AG-UI connections, watcher reconnect behavior, gateway state, and managed Houmao agent lifecycle.

The clear-canvas control SHALL NOT send detach, stop, restart, shutdown, interrupt, or agent-memory-clear requests.

#### Scenario: Clear removes rendered graphics from agent pane
- **WHEN** an agent pane displays a rendered Houmao graphic from AG-UI events
- **AND WHEN** the tester activates the clear-canvas control
- **THEN** the rendered graphic is removed from the agent pane
- **AND THEN** the pane no longer shows the prior transcript, tool-call record, state snapshot, raw event evidence, or visible error evidence for that cleared display state

#### Scenario: Clear preserves connection and target metadata
- **WHEN** an agent pane is connected to a target and has prompt text or target metadata configured
- **AND WHEN** the tester activates the clear-canvas control
- **THEN** the pane remains configured for the same target
- **AND THEN** the prompt text remains unchanged
- **AND THEN** the workbench does not send an AG-UI detach request or any Houmao lifecycle command

#### Scenario: Future events render after clear
- **WHEN** an agent pane canvas has been cleared
- **AND WHEN** the same connected target later emits new AG-UI transcript, graphic, state, activity, custom, or error events
- **THEN** the pane renders those new events from an empty display baseline

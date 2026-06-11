## ADDED Requirements

### Requirement: Skill explains gateway destination fallback publishing
The `houmao-agent-ag-ui` skill SHALL explain that a tmux-controlled Houmao agent may not receive GUI-appended canvas or thread context in its prompt.

The skill SHALL teach agents that, for Houmao gateway publishing, they may omit explicit routing and let the gateway resolve the destination.

The skill SHALL describe the omitted-routing order as message-specified destination, last-sent-thread, last-bound-thread, then Houmao default sink.

The skill SHALL tell agents that explicit `threadId`, `runId`, or `connectionId` values should still be used when the user or environment provides them.

The skill SHALL explain that the default sink is gateway-defined and not an agent-visible thread name.

The skill SHALL instruct agents not to claim GUI visibility when publishing reports default-sink routing or zero live delivery.

#### Scenario: Tmux-controlled agent omits route for gateway fallback
- **WHEN** an agent is being controlled through a tmux tab
- **AND WHEN** it needs to send a chart to the workbench GUI
- **THEN** the skill tells the agent to render and validate the chart as AG-UI events
- **AND THEN** the skill permits the agent to use the Houmao gateway publish helper without an explicit `--thread-id`

#### Scenario: Agent handles default sink warning
- **WHEN** the agent publishes without explicit routing
- **AND WHEN** the helper reports that the gateway used the default sink due to no destination
- **THEN** the skill tells the agent that no GUI destination was available
- **AND THEN** it tells the agent not to say the GUI displayed the message

#### Scenario: Agent handles no live delivery
- **WHEN** the agent publishes to a real thread through explicit routing, last-sent-thread, or last-bound-thread
- **AND WHEN** the response reports `delivered_count = 0`
- **THEN** the skill tells the agent that no live GUI stream received the events at publish time
- **AND THEN** it tells the agent not to claim that the workbench displayed the graphic

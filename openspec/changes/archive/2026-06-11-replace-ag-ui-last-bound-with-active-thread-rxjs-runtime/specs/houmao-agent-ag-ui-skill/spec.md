## ADDED Requirements

### Requirement: Skill explains active-thread fallback publishing
The `houmao-agent-ag-ui` skill SHALL explain that a tmux-controlled Houmao agent may not receive GUI-appended canvas or thread context in its prompt.

The skill SHALL teach agents that, for Houmao gateway publishing, they may omit explicit routing and let the gateway resolve the destination through active-thread fallback.

The skill SHALL describe the omitted-routing order as message-specified destination, active-thread, then Houmao default sink.

The skill SHALL state that last-sent-thread is gateway bookkeeping and is not a fallback destination.

The skill SHALL tell agents that explicit `threadId`, `runId`, or `connectionId` values should still be used when the user or environment provides them.

The skill SHALL explain that the default sink is gateway-defined and not an agent-visible thread name.

The skill SHALL instruct agents not to claim GUI visibility when publishing reports default-sink routing or zero live delivery.

#### Scenario: Tmux-controlled agent omits route for active-thread fallback
- **WHEN** an agent is being controlled through a tmux tab
- **AND WHEN** it needs to send a chart to the workbench GUI
- **THEN** the skill tells the agent to render and validate the chart as AG-UI events
- **AND THEN** the skill permits the agent to use the Houmao gateway publish helper without an explicit `--thread-id`
- **AND THEN** the skill identifies active-thread as the gateway fallback destination

#### Scenario: Agent handles missing active thread
- **WHEN** the agent publishes without explicit routing
- **AND WHEN** the helper reports that the gateway used the default sink due to no destination
- **THEN** the skill tells the agent that no active GUI destination was available
- **AND THEN** it tells the agent not to say the GUI displayed the message

#### Scenario: Agent does not rely on last-sent thread
- **WHEN** an agent reads the omitted-routing guidance
- **THEN** the skill states that last-sent-thread is bookkeeping
- **AND THEN** it does not instruct the agent to rely on last-sent-thread for routing fallback

### Requirement: Skill explains active GUI selection to users and agents
The `houmao-agent-ag-ui` skill SHALL explain that the workbench user can mark one eligible pane as the active default AG-UI thread.

The skill SHALL explain that inactive panes may still receive explicitly addressed AG-UI events.

The skill SHALL tell agents to ask the user to connect or mark the intended GUI pane active when omitted-route publishing reaches the default sink but the user expects visible graphics.

#### Scenario: Agent asks user to mark active pane before retry
- **WHEN** an omitted-route publish reaches the default sink
- **AND WHEN** the user expected the chart to appear in the workbench
- **THEN** the skill tells the agent to ask the user to connect or mark the intended pane active before retrying

#### Scenario: Skill distinguishes active default from explicit delivery
- **WHEN** an agent explains why an inactive pane can still display graphics
- **THEN** the skill states that active-thread controls only omitted-route default publishing
- **AND THEN** it states that explicit thread routing can still deliver to an inactive pane's thread

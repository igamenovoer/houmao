## ADDED Requirements

### Requirement: Skill explains reconnect-aware publish results
The `houmao-agent-ag-ui` skill SHALL teach agents how to interpret AG-UI publish responses that report accepted, stored, and delivered event counts.

The skill SHALL state that `accepted_count` means the gateway accepted valid AG-UI events, `stored_count` means events were retained for bounded replay when supported, and `delivered_count` means live streams received events at publish time.

The skill SHALL state that `delivered_count = 0` with `stored_count > 0` does not necessarily mean the GUI will never see the events, because a reconnecting GUI may replay retained events.

The skill SHALL state that `delivered_count = 0` with `stored_count = 0` means no live stream received the events and no replay storage was reported.

#### Scenario: Agent interprets stored but not delivered events
- **WHEN** an agent publishes a valid AG-UI event batch
- **AND WHEN** the response reports `accepted_count > 0`, `stored_count > 0`, and `delivered_count = 0`
- **THEN** the skill guidance tells the agent that the batch was retained for bounded replay when supported
- **AND THEN** it does not tell the agent to assume the GUI missed the batch forever

#### Scenario: Agent interprets no storage and no delivery
- **WHEN** an agent publishes a valid AG-UI event batch
- **AND WHEN** the response reports `accepted_count > 0`, `stored_count = 0`, and `delivered_count = 0`
- **THEN** the skill guidance tells the agent that no live stream received the batch and no replay storage was reported

### Requirement: Skill prefers agent-addressed GUI targets for Houmao workbench use
The `houmao-agent-ag-ui` skill SHALL explain that Houmao workbench panes should target a stable `agent_id` or unambiguous `agent_name` rather than treating a gateway host and port as durable.

The skill SHALL continue to instruct agents not to guess gateway host, port, thread id, run id, connection id, or endpoint URL.

The skill SHALL direct agents to supported Houmao discovery and gateway publish helpers when publishing to the current agent's Houmao gateway.

For third-party AG-UI-compatible endpoints, the skill SHALL continue to instruct agents to generate and validate events with `houmao-mgr` and then use that endpoint's own delivery method.

#### Scenario: Agent does not treat gateway port as durable
- **WHEN** an agent needs to describe how a GUI should reconnect to a Houmao agent
- **THEN** the skill guidance identifies `agent_id` or unambiguous `agent_name` as the durable address
- **AND THEN** it describes gateway host and port as live metadata that may change

#### Scenario: Third-party delivery remains outside Houmao publish helper
- **WHEN** the user provides a third-party AG-UI-compatible endpoint
- **THEN** the skill tells the agent to use `houmao-mgr` for event generation and validation
- **AND THEN** it tells the agent to use the third-party endpoint's own delivery constraints rather than the Houmao gateway publish helper

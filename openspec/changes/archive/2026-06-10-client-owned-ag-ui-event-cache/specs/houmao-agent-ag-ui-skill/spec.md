## MODIFIED Requirements

### Requirement: Skill explains reconnect-aware publish results
The `houmao-agent-ag-ui` skill SHALL teach agents how to interpret AG-UI publish responses that report accepted, stored, and delivered event counts.

The skill SHALL state that `accepted_count` means the gateway accepted valid AG-UI events.

The skill SHALL state that Houmao gateway publish is live-only for GUI events and normally reports `stored_count = 0`.

The skill SHALL state that `delivered_count` means live streams received events at publish time.

The skill SHALL state that `delivered_count = 0` with `stored_count = 0` means no live GUI stream received the events and the Houmao gateway did not retain them for later replay.

The skill SHALL instruct agents not to claim that the GUI displayed a graphic when `delivered_count = 0`, unless the user or another explicit observation confirms that a GUI received it through another path.

The skill SHALL instruct agents to ask the user to open or watch the intended GUI target and retry when the user expects visible graphics but the publish response reports no live delivery.

#### Scenario: Agent interprets live delivery
- **WHEN** an agent publishes a valid AG-UI event batch
- **AND WHEN** the response reports `accepted_count > 0` and `delivered_count > 0`
- **THEN** the skill guidance tells the agent that at least one live stream received the batch at publish time

#### Scenario: Agent interprets no storage and no delivery
- **WHEN** an agent publishes a valid AG-UI event batch
- **AND WHEN** the response reports `accepted_count > 0`, `stored_count = 0`, and `delivered_count = 0`
- **THEN** the skill guidance tells the agent that no live stream received the batch and no replay storage was reported
- **AND THEN** it tells the agent not to claim that the GUI displayed the message

#### Scenario: Agent retries only after a GUI watcher exists
- **WHEN** the user expects a chart to appear in the workbench
- **AND WHEN** the agent's previous publish response reported `delivered_count = 0`
- **THEN** the skill guidance tells the agent to have the user open or watch the target GUI
- **AND THEN** it tells the agent to publish again only after a live listener is expected

### Requirement: Skill prefers agent-addressed GUI targets for Houmao workbench use
The `houmao-agent-ag-ui` skill SHALL explain that Houmao workbench panes and watchers should target a stable `agent_id` or unambiguous `agent_name` rather than treating a gateway host and port as durable.

The skill SHALL continue to instruct agents not to guess gateway host, port, thread id, run id, connection id, or endpoint URL.

The skill SHALL explain that the workbench can cache GUI events only while it is watching the intended target.

The skill SHALL direct agents to supported Houmao discovery and gateway publish helpers when publishing to the current agent's Houmao gateway.

For third-party AG-UI-compatible endpoints, the skill SHALL continue to instruct agents to generate and validate events with `houmao-mgr` and then use that endpoint's own delivery method.

#### Scenario: Agent does not treat gateway port as durable
- **WHEN** an agent needs to describe how a GUI should reconnect to a Houmao agent
- **THEN** the skill guidance identifies `agent_id` or unambiguous `agent_name` as the durable address
- **AND THEN** it describes gateway host and port as live metadata that may change

#### Scenario: Agent understands GUI-side cache responsibility
- **WHEN** an agent explains whether a missed AG-UI graphic can be recovered
- **THEN** the skill guidance states that the workbench must have been watching the target to cache the event
- **AND THEN** it states that the Houmao gateway does not replay missed published GUI events

#### Scenario: Third-party delivery remains outside Houmao publish helper
- **WHEN** the user provides a third-party AG-UI-compatible endpoint
- **THEN** the skill tells the agent to use `houmao-mgr` for event generation and validation
- **AND THEN** it tells the agent to use the third-party endpoint's own delivery constraints rather than the Houmao gateway publish helper

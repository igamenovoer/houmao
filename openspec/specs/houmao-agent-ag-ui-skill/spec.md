# houmao-agent-ag-ui-skill Specification

## Purpose
Define the maintained `houmao-agent-ag-ui` system skill that teaches Houmao agents how to generate, validate, render, and publish AG-UI-conforming GUI messages with Houmao typed component schemas.
## Requirements
### Requirement: Houmao packages a `houmao-agent-ag-ui` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-ag-ui` under the maintained system-skill asset root.

The skill SHALL teach agents how to produce AG-UI-conforming GUI messages by using `houmao-mgr internals ag-ui` for schema discovery, payload validation, AG-UI event rendering, event validation, and optional publishing.

The skill SHALL state that AG-UI is the wire/event protocol and that Houmao typed components are an application-layer convention.

The skill SHALL be installable through the Houmao system-skill catalog like other maintained Houmao system skills.

#### Scenario: Installed skill explains the protocol split
- **WHEN** an agent opens the installed `houmao-agent-ag-ui` skill
- **THEN** the skill states that AG-UI standardizes event envelopes and tool-call events
- **AND THEN** it states that component names such as `houmao.chart.bar` are Houmao application-layer schemas, not AG-UI core standard names

#### Scenario: System-skill catalog includes the skill
- **WHEN** an operator lists maintained Houmao system skills
- **THEN** `houmao-agent-ag-ui` appears as an installable Houmao-owned skill

### Requirement: Skill provides a validated authoring workflow
The `houmao-agent-ag-ui` skill SHALL provide a concrete workflow for generating GUI messages.

The workflow SHALL instruct the agent to resolve `houmao-mgr`, inspect the target component schema, create a JSON payload, validate the payload, render AG-UI events, validate the rendered events, and then publish or hand off the generated events.

The workflow SHALL include examples for at least one chart component and one non-chart component.

The workflow SHALL prefer `houmao-mgr` validation over hand-written AG-UI JSON.

#### Scenario: Agent follows chart workflow
- **WHEN** an agent needs to send a bar chart to a GUI
- **THEN** the skill instructs it to retrieve the `houmao.chart.bar` schema
- **AND THEN** the skill instructs it to validate the chart payload
- **AND THEN** the skill instructs it to render standard AG-UI tool-call events before publishing

#### Scenario: Agent follows table workflow
- **WHEN** an agent needs to send a table to a GUI
- **THEN** the skill instructs it to retrieve and validate the `houmao.table` schema
- **AND THEN** the skill instructs it to render standard AG-UI events rather than sending an ad hoc table object to the gateway

### Requirement: Skill documents endpoint selection without guessing
The `houmao-agent-ag-ui` skill SHALL describe how to choose a publish target.

The skill SHALL allow publishing to a known Houmao per-agent gateway AG-UI event ingestion endpoint.

For third-party AG-UI-compatible endpoints, the skill SHALL instruct agents to use `houmao-mgr` to generate and validate events, then perform delivery themselves according to the third-party endpoint's own request, authentication, header, framing, and admission constraints.

The skill SHALL instruct agents not to guess gateway host, port, thread id, run id, or endpoint URL when those values are absent from the current environment or user context.

The skill SHALL direct agents to supported Houmao discovery surfaces when they need a live gateway URL.

#### Scenario: Known Houmao gateway can be used through publish helper
- **WHEN** the user provides or the agent discovers a Houmao gateway AG-UI event ingestion target
- **THEN** the skill permits the agent to publish rendered and validated AG-UI events through the Houmao gateway publish helper

#### Scenario: Third-party endpoint uses generated events only
- **WHEN** the user provides an explicit non-Houmao AG-UI-compatible endpoint
- **THEN** the skill tells the agent to generate and validate AG-UI events with `houmao-mgr`
- **AND THEN** the skill tells the agent to send those events outside the Houmao publish helper using the endpoint's own constraints

#### Scenario: Missing endpoint is not guessed
- **WHEN** the agent does not know a live gateway or third-party endpoint URL
- **THEN** the skill tells the agent to discover the Houmao gateway endpoint through supported Houmao commands or ask for the needed endpoint
- **AND THEN** it does not tell the agent to invent a loopback port

### Requirement: Skill enforces safe GUI payload guidance
The `houmao-agent-ag-ui` skill SHALL warn agents that GUI payloads are untrusted until validated and rendered.

The skill SHALL instruct agents not to embed raw unsanitized HTML, scriptable SVG, JavaScript URLs, credential material, or local file contents in component payloads.

The skill SHALL tell agents to use typed chart, table, metric, and dashboard components before considering free-form media.

#### Scenario: Skill warns against raw HTML and scriptable SVG
- **WHEN** an agent reads the GUI payload safety guidance
- **THEN** the skill tells it not to send raw unsanitized HTML or scriptable SVG
- **AND THEN** the skill directs it to typed Houmao component schemas instead

#### Scenario: Skill keeps secrets out of GUI messages
- **WHEN** an agent is preparing GUI payload data
- **THEN** the skill tells it not to include credentials, API keys, bearer tokens, cookies, or private local file contents

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
- **THEN** the skill guidance tells the agent that no live stream received the events and no replay storage was reported
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

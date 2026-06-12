## MODIFIED Requirements

### Requirement: Houmao packages a `houmao-interop-ag-ui` system skill
The system SHALL package a Houmao-owned system skill named `houmao-interop-ag-ui` under the maintained system-skill asset root.

The skill SHALL teach agents how to produce AG-UI-conforming GUI messages by using `houmao-mgr internals ag-ui` for schema discovery, payload validation, AG-UI event rendering, event validation, and optional publishing.

The skill SHALL state that AG-UI is the wire/event protocol and that Houmao typed components are an application-layer convention.

The skill SHALL be installable through the Houmao system-skill catalog like other maintained Houmao system skills.

#### Scenario: Installed skill explains the protocol split
- **WHEN** an agent opens the installed `houmao-interop-ag-ui` skill
- **THEN** the skill states that AG-UI standardizes event envelopes and tool-call events
- **AND THEN** it states that component names such as `houmao.graphic.template` are Houmao application-layer schemas, not AG-UI core standard names

#### Scenario: System-skill catalog includes the skill
- **WHEN** an operator lists maintained Houmao system skills
- **THEN** `houmao-interop-ag-ui` appears as an installable Houmao-owned skill
- **AND THEN** `houmao-agent-ag-ui` does not appear as a current installable skill

### Requirement: Skill provides a validated authoring workflow
The `houmao-interop-ag-ui` skill SHALL provide a concrete workflow for generating GUI messages.

The workflow SHALL instruct the agent to resolve `houmao-mgr`, inspect the target component schema, create a JSON payload, validate the payload, render AG-UI events, validate the rendered events, and then publish or hand off the generated events.

The workflow SHALL include examples for at least one `houmao.graphic.template` chart and one non-chart component.

The workflow SHALL prefer `houmao-mgr` validation over hand-written AG-UI JSON.

The workflow SHALL NOT instruct agents to retrieve, validate, render, or publish retired fixed chart component schemas named `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

#### Scenario: Agent follows chart workflow
- **WHEN** an agent needs to send a bar chart to a GUI
- **THEN** the skill instructs it to retrieve the `houmao.graphic.template` schema
- **AND THEN** the skill instructs it to validate the chart payload
- **AND THEN** the skill instructs it to render standard AG-UI tool-call events before publishing

#### Scenario: Agent follows table workflow
- **WHEN** an agent needs to send a table to a GUI
- **THEN** the skill instructs it to retrieve and validate the `houmao.table` schema
- **AND THEN** the skill instructs it to render standard AG-UI events rather than sending an ad hoc table object to the gateway

#### Scenario: Agent avoids retired fixed chart workflow
- **WHEN** an agent needs to create a chart
- **THEN** the skill does not recommend `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`
- **AND THEN** it directs the agent to `houmao.graphic.template`

### Requirement: Skill enforces safe GUI payload guidance
The `houmao-interop-ag-ui` skill SHALL warn agents that GUI payloads are untrusted until validated and rendered.

The skill SHALL instruct agents not to embed raw unsanitized HTML, scriptable SVG, JavaScript URLs, credential material, or local file contents in component payloads.

The skill SHALL tell agents to use typed graphic template, table, metric, and dashboard components before considering free-form media.

#### Scenario: Skill warns against raw HTML and scriptable SVG
- **WHEN** an agent reads the GUI payload safety guidance
- **THEN** the skill tells it not to send raw unsanitized HTML or scriptable SVG
- **AND THEN** the skill directs it to typed Houmao component schemas instead

#### Scenario: Skill keeps secrets out of GUI messages
- **WHEN** an agent is preparing GUI payload data
- **THEN** the skill tells it not to include credentials, API keys, bearer tokens, cookies, or private local file contents

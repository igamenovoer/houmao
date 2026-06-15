## MODIFIED Requirements

### Requirement: Skill provides a validated authoring workflow
The `houmao-interop-ag-ui` skill SHALL provide concrete workflows for generating GUI messages through AG-UI protocol events.

For already-chosen Houmao-known implementations, the workflow SHALL instruct the agent to resolve `houmao-mgr`, inspect the target implementation schema, create or receive a JSON payload, validate the payload, render AG-UI events, validate the rendered events, and then publish or hand off the generated events.

For frontend-specific implementations that Houmao does not know, the workflow SHALL instruct the agent to use `houmao-mgr ag-ui impl new-component render`, validate the rendered events with AG-UI protocol validation, and then publish or hand off the generated events according to the target endpoint.

The workflow SHALL include examples for at least one non-chart Houmao-known implementation and one frontend-specific implementation unknown to Houmao.

The workflow SHALL prefer `houmao-mgr` implementation validation over hand-written AG-UI JSON when the payload uses a Houmao-known implementation.

The workflow SHALL tell agents that `houmao-mgr ag-ui impl list` lists Houmao-known implementation schemas and that `houmao-mgr ag-ui impl schema <implementation>` inspects a chosen implementation.

The workflow SHALL NOT instruct agents to retrieve, validate, render, or publish retired fixed chart component schemas named `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

The workflow SHALL NOT route graphing authoring requests to `houmao-ext-graphing`.

#### Scenario: Agent follows already-chosen known implementation workflow
- **WHEN** an agent already has a chosen Houmao-known implementation name and payload
- **THEN** the skill instructs it to retrieve or inspect that implementation schema
- **AND THEN** the skill instructs it to validate the payload
- **AND THEN** the skill instructs it to render standard AG-UI tool-call events before publishing

#### Scenario: Agent follows table implementation workflow
- **WHEN** an agent needs to send a table to a GUI
- **THEN** the skill instructs it to retrieve and validate the `houmao.table` implementation schema
- **AND THEN** the skill instructs it to render standard AG-UI events rather than sending an ad hoc table object to the gateway

#### Scenario: Agent follows custom new-component workflow
- **WHEN** an agent needs to send a payload for a frontend-specific implementation unknown to Houmao
- **THEN** the skill instructs it to render a generic standard AG-UI tool-call sequence through `houmao-mgr ag-ui impl new-component render`
- **AND THEN** the skill instructs it to validate the rendered event batch before publishing or handoff

#### Scenario: Agent avoids retired fixed chart workflow
- **WHEN** an agent needs to create a chart
- **THEN** the skill does not recommend `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`
- **AND THEN** it does not route the request to `houmao-ext-graphing`

## ADDED Requirements

### Requirement: Skill does not route non-extension work to graphing extension
The `houmao-interop-ag-ui` skill SHALL remain a non-extension skill focused on AG-UI protocol, implementation rendering for already-chosen payloads, gateway publishing, endpoint boundaries, and delivery interpretation.

The skill SHALL NOT list `houmao-ext-graphing` as a required related skill, delegated workflow, or graphing handoff.

The skill SHALL NOT require the graphing extension for AG-UI protocol validation, generic implementation rendering, gateway publishing, or delivery-result interpretation.

#### Scenario: Agent reads AG-UI interop related-skill guidance
- **WHEN** an agent reads the `houmao-interop-ag-ui` related-skill or help guidance
- **THEN** the guidance does not tell the agent to invoke `houmao-ext-graphing`
- **AND THEN** the AG-UI interop workflow remains usable when extension skills are ignored

#### Scenario: Agent publishes already-rendered AG-UI events without graphing extension
- **WHEN** an agent has a valid AG-UI event batch to publish
- **THEN** the skill provides publishing and delivery-result guidance without requiring `houmao-ext-graphing`

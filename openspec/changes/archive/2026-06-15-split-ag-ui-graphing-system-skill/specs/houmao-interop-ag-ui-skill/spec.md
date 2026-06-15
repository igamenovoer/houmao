## MODIFIED Requirements

### Requirement: Skill provides a validated authoring workflow
The `houmao-interop-ag-ui` skill SHALL provide concrete workflows for generating GUI messages through AG-UI protocol events.

For Houmao-known implementations, the workflow SHALL instruct the agent to resolve `houmao-mgr`, inspect the selected implementation schema, validate an already-authored JSON payload, render AG-UI events, validate the rendered events, and then publish or hand off the generated events.

For built-in graphing payload authoring, the workflow SHALL direct the agent to `houmao-utils-graphing` before returning to AG-UI event rendering and delivery.

For frontend-specific implementations that Houmao does not know, the workflow SHALL instruct the agent to use `houmao-mgr ag-ui impl new-component render`, validate the rendered events with AG-UI protocol validation, and then publish or hand off the generated events according to the target endpoint.

The workflow SHALL include examples for at least one non-graph Houmao implementation and at least one schema-agnostic custom tool call.

The workflow SHALL prefer `houmao-mgr` implementation validation over hand-written AG-UI JSON when the payload uses a Houmao-known implementation.

The workflow SHALL NOT instruct agents to retrieve, validate, render, or publish retired fixed chart component schemas named `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

#### Scenario: Agent delegates built-in graph authoring
- **WHEN** an agent needs to author a Plotly.js or Vega-Lite graphing payload
- **THEN** the skill directs it to `houmao-utils-graphing`
- **AND THEN** the skill continues to describe how rendered AG-UI events are validated, published, or handed off after graphing authoring is complete

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
- **AND THEN** it directs the agent to `houmao-utils-graphing` for built-in graphing authoring

### Requirement: Skill explains protocol and impl for custom renderer contracts
The `houmao-interop-ag-ui` skill SHALL teach agents that `houmao-mgr ag-ui impl new-component render` can render standard tool-call events for frontend-specific implementation names that Houmao does not know.

The skill SHALL teach agents that Houmao implementation commands add schema discovery and payload validation only for Houmao-known implementations.

The skill SHALL state that protocol validation means the event batch is valid AG-UI, not that the target GUI implements or displayed the implementation payload.

The skill SHALL teach agents that built-in graphing implementation selection and payload authoring belong to `houmao-utils-graphing`.

#### Scenario: Agent uses new-component path for custom frontend implementation
- **WHEN** an agent needs to send a project-specific tool-call payload such as `myapp.graphic.timeline`
- **THEN** the skill directs it to use `houmao-mgr ag-ui impl new-component render`
- **AND THEN** the skill does not require `myapp.graphic.timeline` to be listed by `houmao-mgr ag-ui impl list`

#### Scenario: Agent distinguishes protocol validity from rendering
- **WHEN** a custom frontend implementation event batch passes AG-UI protocol validation
- **THEN** the skill tells the agent that only a GUI implementing the matching contract can render it
- **AND THEN** the skill does not let the agent claim GUI visibility from protocol validation alone

#### Scenario: Agent routes built-in graphing decisions to graphing utility
- **WHEN** an agent needs to choose between built-in `templated-graphics` and `freeform-graphics`
- **THEN** the skill directs it to `houmao-utils-graphing`
- **AND THEN** the skill does not duplicate Plotly.js or Vega-Lite authoring rules

## REMOVED Requirements

### Requirement: Skill explains Layer 2 Vega-Lite authoring
**Reason**: Built-in Vega-Lite graphing authoring now belongs to the dedicated `houmao-utils-graphing` utility skill.
**Migration**: Use `houmao-utils-graphing` for `houmao.graphic.vegalite` payload authoring, then return to `houmao-interop-ag-ui` or gateway guidance for event delivery.

### Requirement: Skill preserves least-powerful-layer guidance
**Reason**: Plotly.js versus Vega-Lite layer selection is graphing-specific authoring guidance and now belongs to `houmao-utils-graphing`.
**Migration**: Use `houmao-utils-graphing` to choose `templated-graphics` or `freeform-graphics`, inspect graphing schemas and catalogs, validate graphing payloads, and render AG-UI events.

### Requirement: Skill explains Vega-Lite safety limits
**Reason**: Vega-Lite safety limits are graphing-specific and now belong to `houmao-utils-graphing`.
**Migration**: Use `houmao-utils-graphing` for Vega-Lite freeform graphics safety guidance and validation workflow.

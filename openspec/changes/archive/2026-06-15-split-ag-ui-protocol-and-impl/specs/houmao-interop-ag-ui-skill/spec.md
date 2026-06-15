## ADDED Requirements

### Requirement: Skill explains protocol and impl for custom renderer contracts
The `houmao-interop-ag-ui` skill SHALL teach agents that `houmao-mgr ag-ui impl new-component render` can render standard tool-call events for frontend-specific implementation names that Houmao does not know.

The skill SHALL teach agents that Houmao implementation commands add schema discovery and payload validation only for Houmao-known implementations.

The skill SHALL state that protocol validation means the event batch is valid AG-UI, not that the target GUI implements or displayed the implementation payload.

The skill SHALL teach agents to use `houmao-mgr ag-ui impl templated-graphics list` for supported Layer 1 templated graphics schemas and `houmao-mgr ag-ui impl freeform-graphics list` for supported higher-freedom graphics schemas.

#### Scenario: Agent uses new-component path for custom frontend implementation
- **WHEN** an agent needs to send a project-specific tool-call payload such as `myapp.graphic.timeline`
- **THEN** the skill directs it to use `houmao-mgr ag-ui impl new-component render`
- **AND THEN** the skill does not require `myapp.graphic.timeline` to be listed by `houmao-mgr ag-ui impl list`

#### Scenario: Agent distinguishes protocol validity from rendering
- **WHEN** a custom frontend implementation event batch passes AG-UI protocol validation
- **THEN** the skill tells the agent that only a GUI implementing the matching contract can render it
- **AND THEN** the skill does not let the agent claim GUI visibility from protocol validation alone

## MODIFIED Requirements

### Requirement: Houmao packages a `houmao-interop-ag-ui` system skill
The system SHALL package a Houmao-owned system skill named `houmao-interop-ag-ui` under the maintained system-skill asset root.

The skill SHALL teach agents how to produce AG-UI-conforming GUI messages by using `houmao-mgr ag-ui protocol` for standard AG-UI event generation, event validation, event framing, and schema-agnostic tool-call rendering.

The skill SHALL teach agents how to use `houmao-mgr ag-ui impl` for Houmao-known implementation schema discovery, payload validation, implementation rendering, and implementation catalog discovery.

The skill SHALL state that AG-UI is the wire/event protocol and that Houmao typed components are AG-UI implementation contracts carried by standard tool-call events.

The skill SHALL be installable through the Houmao system-skill catalog like other maintained Houmao system skills.

#### Scenario: Installed skill explains the protocol and impl split
- **WHEN** an agent opens the installed `houmao-interop-ag-ui` skill
- **THEN** the skill states that AG-UI protocol standardizes event envelopes and tool-call events
- **AND THEN** it states that implementation names such as `houmao.graphic.template` are Houmao application-layer payload contracts, not AG-UI protocol names

#### Scenario: System-skill catalog includes the skill
- **WHEN** an operator lists maintained Houmao system skills
- **THEN** `houmao-interop-ag-ui` appears as an installable Houmao-owned skill
- **AND THEN** `houmao-agent-ag-ui` does not appear as a current installable skill

### Requirement: Skill provides a validated authoring workflow
The `houmao-interop-ag-ui` skill SHALL provide concrete workflows for generating GUI messages through AG-UI protocol events.

For Houmao-known implementations, the workflow SHALL instruct the agent to resolve `houmao-mgr`, inspect the target implementation schema, create a JSON payload, validate the payload, render AG-UI events, validate the rendered events, and then publish or hand off the generated events.

For frontend-specific implementations that Houmao does not know, the workflow SHALL instruct the agent to use `houmao-mgr ag-ui impl new-component render`, validate the rendered events with AG-UI protocol validation, and then publish or hand off the generated events according to the target endpoint.

The workflow SHALL include examples for at least one `houmao.graphic.template` chart and one non-chart implementation.

The workflow SHALL prefer `houmao-mgr` implementation validation over hand-written AG-UI JSON when the payload uses a Houmao-known implementation.

The workflow SHALL tell agents that `houmao-mgr ag-ui impl templated-graphics list` lists Layer 1 templated graphics schemas, `houmao-mgr ag-ui impl freeform-graphics list` lists higher-freedom graphics schemas, and `houmao-mgr ag-ui impl list` lists all Houmao-known implementation schemas.

The workflow SHALL NOT instruct agents to retrieve, validate, render, or publish retired fixed chart component schemas named `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

#### Scenario: Agent follows chart implementation workflow
- **WHEN** an agent needs to send a bar chart to a GUI
- **THEN** the skill instructs it to retrieve the `houmao.graphic.template` implementation schema
- **AND THEN** the skill instructs it to validate the chart payload
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
- **AND THEN** it directs the agent to `houmao.graphic.template`

### Requirement: Skill documents endpoint selection without guessing
The `houmao-interop-ag-ui` skill SHALL describe how to choose a publish target.

The skill SHALL allow publishing to a known Houmao per-agent gateway AG-UI event ingestion endpoint.

For third-party AG-UI-compatible endpoints, the skill SHALL instruct agents to use `houmao-mgr ag-ui protocol` to generate or validate standard AG-UI events, then perform delivery themselves according to the third-party endpoint's own request, authentication, header, framing, and admission constraints.

For Houmao-known implementation payloads, the skill SHALL instruct agents to use `houmao-mgr ag-ui impl` before protocol validation so payload semantics are checked before delivery.

The skill SHALL instruct agents not to guess gateway host, port, thread id, run id, connection id, or endpoint URL when those values are absent from the current environment or user context.

The skill SHALL direct agents to supported Houmao discovery surfaces when they need a live gateway URL.

#### Scenario: Known Houmao gateway can be used through publish helper
- **WHEN** the user provides or the agent discovers a Houmao gateway AG-UI event ingestion target
- **THEN** the skill permits the agent to publish rendered and validated AG-UI events through the Houmao gateway publish helper

#### Scenario: Third-party endpoint uses generated protocol events only
- **WHEN** the user provides an explicit non-Houmao AG-UI-compatible endpoint
- **THEN** the skill tells the agent to generate and validate AG-UI protocol events with `houmao-mgr`
- **AND THEN** the skill tells the agent to send those events outside the Houmao publish helper using the endpoint's own constraints

#### Scenario: Missing endpoint is not guessed
- **WHEN** the agent does not know a live gateway or third-party endpoint URL
- **THEN** the skill tells the agent to discover the Houmao gateway endpoint through supported Houmao commands or ask for the needed endpoint
- **AND THEN** it does not tell the agent to invent a loopback port

### Requirement: Skill preserves least-powerful-layer guidance
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer the `houmao.graphic.template` implementation for supported Plotly 2D snapshot charts and to use the `houmao.graphic.vegalite` implementation only when they need Vega-Lite grammar, custom declarative structure, Vega-Lite interaction, or a chart shape outside the Layer 1 Plotly 2D trace catalog.

The skill SHALL teach agents that `houmao.graphic.template` schema version `3` uses `figureType: "plotly2d"` and `traces[].type` rather than the previous five-item `chartType` contract.

The skill SHALL tell agents to inspect `houmao-mgr ag-ui impl schema houmao.graphic.template`, `houmao-mgr ag-ui impl catalog houmao.graphic.template traces`, or AG-UI capabilities to see the supported Plotly 2D trace catalog before authoring uncommon trace families.

The skill SHALL tell agents to inspect `houmao-mgr ag-ui impl templated-graphics list` before choosing supported Layer 1 templated graphics and `houmao-mgr ag-ui impl freeform-graphics list` before choosing supported higher-freedom graphics contracts.

The skill SHALL continue to state that Layer 1 does not accept Vega-Lite renderer ids, fallback renderer lists, or `extra.vega-lite`.

#### Scenario: Agent keeps supported Plotly 2D charts on Layer 1
- **WHEN** an agent needs an ordinary supported Plotly 2D chart with inline data, such as a heatmap, box plot, violin plot, polar chart, financial chart, treemap, table, or Sankey diagram
- **THEN** the skill directs it to prefer the `houmao.graphic.template` implementation
- **AND THEN** it does not direct the agent to use Vega-Lite only because Layer 2 exists

#### Scenario: Agent checks catalog coverage for uncommon traces
- **WHEN** an agent wants to emit an uncommon Plotly trace family
- **THEN** the skill tells it to inspect the template graphics schema, implementation trace catalog, or capabilities for the supported trace catalog
- **AND THEN** the skill tells it to validate the payload before rendering AG-UI events

#### Scenario: Agent lists supported graphics categories first
- **WHEN** an agent needs to know which renderable graphics schemas Houmao supports
- **THEN** the skill tells it to run `houmao-mgr ag-ui impl templated-graphics list` for Layer 1 schemas
- **AND THEN** the skill tells it to run `houmao-mgr ag-ui impl freeform-graphics list` for higher-freedom schemas
- **AND THEN** the skill does not tell it to infer schema names from the Plotly trace catalog

#### Scenario: Agent does not put Vega-Lite inside Layer 1
- **WHEN** an agent has a raw Vega-Lite spec
- **THEN** the skill tells it to use `houmao.graphic.vegalite`
- **AND THEN** the skill tells it not to place the raw spec in `houmao.graphic.template.extra`

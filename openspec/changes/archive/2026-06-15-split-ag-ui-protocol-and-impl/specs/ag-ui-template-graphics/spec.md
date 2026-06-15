## MODIFIED Requirements

### Requirement: Houmao defines standardized template graphic payloads
Houmao SHALL define a Layer 1 AG-UI implementation named `houmao.graphic.template`.

The Plotly-backed payload SHALL use `schemaVersion` equal to `3`.

The payload SHALL include `schemaVersion`, `figureType`, `title`, and non-empty `traces`.

The `figureType` value SHALL be `plotly2d`.

The payload MAY include `renderer`, `subtitle`, `dataRefs`, `layout`, `config`, `display`, and `extra`.

The schema SHALL use `traces[].type` as the primary chart-family selector.

The schema SHALL define supported trace types through a Houmao-owned Plotly 2D trace catalog.

The trace catalog SHALL be derived from Plotly.js schema metadata and SHALL include Plotly trace families whose categories do not include `gl3d`, except where Houmao safety policy explicitly disables a trace or field.

The trace catalog SHALL reject true 3D scene trace families, including `scatter3d`, `surface`, `mesh3d`, `cone`, `streamtube`, `volume`, and `isosurface`.

The trace catalog SHALL reject unsafe Plotly fields such as `*src` remote-source fields, `stream`, raw transforms, frames, templates, executable content, remote URLs, credential-bearing map settings, and unrestricted backend replacement fields.

The schema SHALL represent ordinary chart data through curated Plotly-aligned trace data and style fields rather than the previous row-and-encoding shape.

The schema SHALL support inline static arrays and nested trace data objects for immutable snapshots.

The schema SHALL reserve datasource-bound traces through `dataRefs` and trace field-path `source.bindings` for future runtime materialization.

The standardized fields SHALL be sufficient for a GUI to render the chart without using `extra`.

The schema SHALL NOT expose the full raw Plotly figure schema as the public Layer 1 contract.

#### Scenario: Template graphic implementation schema is discoverable
- **WHEN** an agent asks `houmao-mgr ag-ui impl schema houmao.graphic.template`
- **THEN** the command returns the implementation name, schema version `3`, JSON Schema-compatible payload shape, supported Plotly 2D trace catalog metadata, and a valid Plotly-backed example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Standardized inline Plotly 2D payload validates offline
- **WHEN** an agent validates a `houmao.graphic.template` payload with `schemaVersion` equal to `3`, `figureType` equal to `plotly2d`, and an allowed Plotly 2D trace type such as `heatmap`, `box`, `sankey`, `candlestick`, or `scatterpolar`
- **THEN** the command exits successfully
- **AND THEN** the output identifies `houmao.graphic.template`, schema version `3`, and the accepted trace type

#### Scenario: True 3D trace type is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload with `traces.0.type` equal to `scatter3d`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic explains that true 3D Plotly scene traces are outside Layer 1 template graphics

#### Scenario: Schema version 2 chart type payload is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload that uses `schemaVersion` equal to `2` with `chartType`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic directs the author toward schema version `3`, `figureType`, and `traces[].type`

#### Scenario: Legacy encoding payload is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload that uses `data.values` and `encoding` instead of `traces`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic directs the author toward the Plotly-backed trace shape

### Requirement: Template graphic rendering emits standard AG-UI events
`houmao-mgr ag-ui impl render` SHALL render a validated `houmao.graphic.template` payload into a complete standard AG-UI tool-call event sequence.

The generated `TOOL_CALL_START` event SHALL use `toolCallName` equal to `houmao.graphic.template`.

The generated `TOOL_CALL_ARGS` event SHALL contain the normalized Plotly-backed payload with stable camelCase field names, `schemaVersion` equal to `3`, and `figureType` equal to `plotly2d`.

The generated sequence SHALL remain compatible with the existing Houmao gateway publish helper because publish accepts standard AG-UI protocol events and does not require template schema knowledge.

#### Scenario: Template graphic implementation renders to tool-call events
- **WHEN** an agent renders a valid schema version `3` `houmao.graphic.template` payload with `houmao-mgr ag-ui impl render`
- **THEN** the output event sequence contains `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `houmao.graphic.template`
- **AND THEN** the rendered event sequence passes standard AG-UI protocol event validation

#### Scenario: Publish helper accepts rendered template events
- **WHEN** an agent passes rendered `houmao.graphic.template` AG-UI events to the Houmao gateway publish helper
- **THEN** the helper validates the standard event sequence before sending
- **AND THEN** the helper does not require knowledge of the template graphic schema at publish time

### Requirement: Capabilities advertise Layer 1 template graphics
The AG-UI capabilities response SHALL advertise Houmao Layer 1 template graphics in Houmao custom AG-UI implementation metadata.

The metadata SHALL include the template implementation tool name, implementation category `templated-graphics`, schema version, figure type, supported trace types, excluded trace types, supported renderer ids, default renderer id, Plotly bundle identifier, `extra` policy, datasource binding vocabulary support, datasource materialization support, and whether raw Plotly or Vega-Lite DSL specs are supported.

The metadata SHALL list Plotly 2D trace catalog coverage rather than advertising the previous five chart types as the complete Layer 1 surface.

The metadata SHALL list true 3D scene traces as excluded from Layer 1 template graphics.

The metadata SHALL list `plotly` as the only supported Layer 1 renderer id.

The metadata SHALL list `plotly` as the default Layer 1 renderer id.

The metadata SHALL state that raw Plotly DSL figures are not part of Layer 1 template graphics.

The metadata SHALL state that raw Vega-Lite DSL graphics are not part of Layer 1 template graphics.

The metadata SHALL state the offline policy for geo and map traces, including that remote tile URLs, remote style URLs, and credential-bearing map settings are not accepted in template payloads.

#### Scenario: Capabilities list Plotly renderer id
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom implementation metadata for template graphics
- **AND THEN** that metadata classifies the implementation as `templated-graphics`
- **AND THEN** that metadata lists `plotly` as the only supported Layer 1 renderer id
- **AND THEN** that metadata lists `plotly` as the default renderer id

#### Scenario: Capabilities list Plotly 2D trace coverage
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response lists supported Plotly 2D trace types such as `bar`, `heatmap`, `box`, `violin`, `sankey`, `table`, `treemap`, `scatterpolar`, and `candlestick`
- **AND THEN** the response does not describe `bar`, `line`, `scatter`, `pie`, and `histogram` as the complete Layer 1 coverage

#### Scenario: Capabilities list true 3D exclusions
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response lists true 3D traces such as `scatter3d` and `surface` as excluded from Layer 1 template graphics
- **AND THEN** the response does not advertise support for Plotly 3D scene rendering in `houmao.graphic.template`

#### Scenario: Capabilities describe datasource materialization status
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes whether Layer 1 datasource binding vocabulary is recognized
- **AND THEN** the response states whether datasource materialization is supported by the current workbench path
- **AND THEN** the response distinguishes supported binding field paths from available runtime row materialization features

### Requirement: Agent guidance prefers template graphics for supported Plotly charts
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer the `houmao.graphic.template` implementation for supported Plotly 2D charts.

The skill SHALL explain that Layer 1 template graphics use standardized Houmao JSON rendered through Plotly.js.

The skill SHALL explain that agents should not choose among Layer 1 template renderers.

The skill SHALL explain that `extra.plotly` is disposable and must not be used as a full Plotly, Vega-Lite, Vega, React, HTML, or JavaScript escape hatch.

The skill SHALL explain that ordinary static charts can use inline trace arrays and nested trace data objects.

The skill SHALL explain that datasource metadata and trace source bindings are catalog-backed vocabulary, and that agents must check capabilities before assuming datasource materialization support.

The skill SHALL keep the render, validate, and publish workflow based on `houmao-mgr ag-ui impl`, `houmao-mgr ag-ui protocol`, and `houmao-mgr agents ... gateway ag-ui publish`.

#### Scenario: Agent chooses template graphics implementation
- **WHEN** an agent needs to display a supported Plotly 2D chart such as a heatmap, violin plot, polar chart, financial chart, treemap, table, or Sankey diagram
- **THEN** the skill directs it to inspect and use `houmao.graphic.template`
- **AND THEN** the skill tells it to validate and render the payload before publishing

#### Scenario: Agent does not use Layer 1 as raw Plotly
- **WHEN** an agent needs a Plotly feature or field that is not represented in the supported template trace catalog
- **THEN** the skill tells it that raw Plotly is not accepted in Layer 1
- **AND THEN** the skill does not tell it to place a full Plotly figure in Layer 1 `extra`

#### Scenario: Agent does not use Layer 1 as raw Vega-Lite
- **WHEN** an agent needs a custom Vega-Lite chart structure that cannot be represented by standardized template fields
- **THEN** the skill tells it that raw Vega-Lite belongs to a separate Layer 2 DSL graphics implementation
- **AND THEN** the skill does not tell it to place a full Vega-Lite spec in Layer 1 `extra`

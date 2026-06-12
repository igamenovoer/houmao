# ag-ui-template-graphics Specification

## Purpose
TBD - created by archiving change add-ag-ui-template-graphics-vega. Update Purpose after archive.
## Requirements
### Requirement: Houmao defines standardized template graphic payloads
Houmao SHALL define a Layer 1 AG-UI component named `houmao.graphic.template`.

The Plotly-backed payload SHALL use `schemaVersion` equal to `2`.

The payload SHALL include `schemaVersion`, `chartType`, `title`, and non-empty `traces`.

The payload MAY include `renderer`, `subtitle`, `dataRefs`, `layout`, `config`, `display`, and `extra`.

The initial `chartType` values SHALL be exactly `bar`, `line`, `scatter`, `pie`, and `histogram`.

The `line` chart type SHALL compile to Plotly scatter-family traces with line mode.

The `histogram` chart type SHALL compile to Plotly histogram traces.

The schema SHALL reject unsupported 2D and 3D Plotly chart families as outside this round's Layer 1 template graphics scope.

The payload SHALL represent ordinary chart series through curated Plotly-aligned trace fields rather than the previous row-and-encoding shape.

The payload SHALL support inline static arrays for immutable snapshots.

The payload SHALL reserve datasource-bound traces through `dataRefs` and trace `source` bindings for future runtime materialization.

The standardized fields SHALL be sufficient for a GUI to render the chart without using `extra`.

The schema SHALL NOT expose the full raw Plotly figure schema as the public Layer 1 contract.

#### Scenario: Template graphic schema is discoverable
- **WHEN** an agent asks `houmao-mgr internals ag-ui components schema houmao.graphic.template`
- **THEN** the command returns the component name, schema version `2`, JSON Schema-compatible payload shape, and a valid Plotly-backed example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Standardized inline payload validates offline
- **WHEN** an agent validates a `houmao.graphic.template` payload with inline trace arrays and valid layout fields for one of the five supported `chartType` values
- **THEN** the command exits successfully
- **AND THEN** the output identifies `houmao.graphic.template` and schema version `2`

#### Scenario: Unsupported chart type is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload with `chartType` equal to `heatmap`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic explains that the chart type is outside this round's supported Layer 1 template graphics scope

#### Scenario: Legacy encoding payload is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload that uses `data.values` and `encoding` instead of `traces`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic directs the author toward the Plotly-backed trace shape

### Requirement: Renderer-specific extra fields are constrained refinements
Template graphic payloads SHALL allow an optional `extra` object keyed by renderer id.

For Layer 1 template graphics, the only supported renderer-scoped extra key SHALL be `plotly`.

The `extra` object SHALL be optional and SHALL NOT be required for correct rendering.

Python authoring validation SHALL reject `extra` content that attempts to replace standardized chart semantics, including full backend specs, raw trace replacement, raw data replacement, raw layout replacement, raw config replacement, arbitrary JavaScript, HTML, iframe content, scriptable SVG, or remote URL loading.

The Plotly `extra` block SHALL be limited to safe renderer presentation refinements such as margins, axis formatting, legend placement, hover mode, bar gap, marker refinements, line interpolation, point sizing, and responsive sizing hints.

Unsupported renderer keys or unsupported fields inside `extra.plotly` SHALL be ignored by renderers or reported as non-fatal diagnostics.

#### Scenario: Safe Plotly extra validates
- **WHEN** a `houmao.graphic.template` payload includes `extra.plotly.layout.bargap`
- **THEN** Python authoring validation accepts the payload
- **AND THEN** the chart remains renderable from standardized fields if the extra block is ignored

#### Scenario: Full Plotly figure in extra is rejected
- **WHEN** a `houmao.graphic.template` payload includes `extra.plotly.data` or `extra.plotly.traces`
- **THEN** Python authoring validation rejects the payload before rendering AG-UI events
- **AND THEN** the diagnostic names the invalid field path without echoing unsafe content

#### Scenario: Vega-Lite extra is rejected
- **WHEN** a `houmao.graphic.template` payload includes `extra.vega-lite`
- **THEN** Python authoring validation rejects the payload
- **AND THEN** the diagnostic explains that raw Vega-Lite belongs outside Layer 1 template graphics

### Requirement: Template graphic rendering emits standard AG-UI events
`houmao-mgr internals ag-ui events render` SHALL render a validated `houmao.graphic.template` payload into a complete standard AG-UI tool-call event sequence.

The generated `TOOL_CALL_START` event SHALL use `toolCallName` equal to `houmao.graphic.template`.

The generated `TOOL_CALL_ARGS` event SHALL contain the normalized Plotly-backed payload with stable camelCase field names and `schemaVersion` equal to `2`.

The generated sequence SHALL remain compatible with the existing Houmao gateway publish helper.

#### Scenario: Template graphic renders to tool-call events
- **WHEN** an agent renders a valid schema version `2` `houmao.graphic.template` payload
- **THEN** the output event sequence contains `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `houmao.graphic.template`
- **AND THEN** the rendered event sequence passes standard AG-UI event validation

#### Scenario: Publish helper accepts rendered template events
- **WHEN** an agent passes rendered `houmao.graphic.template` AG-UI events to the Houmao gateway publish helper
- **THEN** the helper validates the standard event sequence before sending
- **AND THEN** the helper does not require knowledge of the template graphic schema at publish time

### Requirement: Capabilities advertise Layer 1 template graphics
The AG-UI capabilities response SHALL advertise Houmao Layer 1 template graphics in Houmao custom metadata.

The metadata SHALL include the template tool name, schema version, supported chart types, supported renderer ids, default renderer id, `extra` policy, datasource binding vocabulary support, datasource materialization support, and whether raw Plotly or Vega-Lite DSL specs are supported.

The metadata SHALL list the five supported chart types and SHALL NOT list deferred 2D or 3D chart families.

The metadata SHALL list `plotly` as the only supported Layer 1 renderer id.

The metadata SHALL list `plotly` as the default Layer 1 renderer id.

The metadata SHALL state that raw Plotly DSL figures are not part of Layer 1 template graphics.

The metadata SHALL state that raw Vega-Lite DSL graphics are not part of Layer 1 template graphics.

#### Scenario: Capabilities list Plotly renderer id
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom metadata for template graphics
- **AND THEN** that metadata lists `plotly` as the only supported Layer 1 renderer id
- **AND THEN** that metadata lists `plotly` as the default renderer id

#### Scenario: Capabilities list initial chart coverage
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response lists `bar`, `line`, `scatter`, `pie`, and `histogram` as supported chart types
- **AND THEN** the response does not list deferred chart types such as `area`, `donut`, `heatmap`, `box`, `scatterpolar`, or `scatter3d`

#### Scenario: Capabilities describe datasource materialization status
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes whether Layer 1 datasource binding vocabulary is recognized
- **AND THEN** the response states that datasource materialization is not supported in this round
- **AND THEN** the response does not advertise row update modes, max materialized rows, or datasource refresh behavior as available runtime features

### Requirement: Agent guidance prefers template graphics for supported Plotly charts
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer `houmao.graphic.template` for the supported Plotly-backed chart types.

The skill SHALL explain that Layer 1 template graphics use standardized Houmao JSON rendered through Plotly.js.

The skill SHALL explain that agents should not choose among Layer 1 template renderers.

The skill SHALL explain that `extra.plotly` is disposable and must not be used as a full Plotly, Vega-Lite, Vega, React, HTML, or JavaScript escape hatch.

The skill SHALL explain that ordinary static charts can use inline trace arrays.

The skill SHALL explain that datasource metadata and trace source bindings are reserved vocabulary until the workbench advertises datasource materialization support.

The skill SHALL keep the existing render, validate, and publish workflow based on `houmao-mgr internals ag-ui` and `houmao-mgr agents ... gateway ag-ui publish`.

#### Scenario: Agent chooses template graphics
- **WHEN** an agent needs to display a bar, line, scatter, pie, or histogram chart
- **THEN** the skill directs it to inspect and use `houmao.graphic.template`
- **AND THEN** the skill tells it to validate and render the payload before publishing

#### Scenario: Agent does not use Layer 1 as raw Plotly
- **WHEN** an agent needs a custom Plotly figure structure that cannot be represented by standardized template fields
- **THEN** the skill tells it that raw Plotly is not accepted in Layer 1
- **AND THEN** the skill does not tell it to place a full Plotly figure in Layer 1 `extra`

#### Scenario: Agent does not use Layer 1 as raw Vega-Lite
- **WHEN** an agent needs a custom Vega-Lite chart structure that cannot be represented by standardized template fields
- **THEN** the skill tells it that raw Vega-Lite belongs to a separate Layer 2 DSL graphics capability
- **AND THEN** the skill does not tell it to place a full Vega-Lite spec in Layer 1 `extra`

### Requirement: Template graphics use Plotly as the sole Layer 1 renderer
Layer 1 template graphics SHALL support exactly one renderer id: `plotly`.

The default Layer 1 renderer SHALL be `plotly`.

The `renderer` object MAY be omitted, in which case authoring validation and workbench rendering SHALL use `plotly`.

If a payload includes `renderer.preferred`, the value SHALL be `plotly`.

Layer 1 renderer fallback lists SHALL NOT affect rendering.

#### Scenario: Missing renderer defaults to Plotly
- **WHEN** an agent validates a `houmao.graphic.template` payload without a `renderer` object
- **THEN** validation accepts the payload
- **AND THEN** the normalized payload uses `renderer.preferred` equal to `plotly`

#### Scenario: Non-Plotly renderer is rejected
- **WHEN** an agent validates a `houmao.graphic.template` payload with `renderer.preferred` equal to `vega-lite` or `recharts`
- **THEN** validation rejects the payload
- **AND THEN** the diagnostic identifies `renderer.preferred` without rendering through a fallback backend

### Requirement: Workbench renders template graphics through Plotly.js
The AG-UI workbench SHALL render completed `houmao.graphic.template` tool calls through Plotly.js.

The workbench SHALL compile validated Houmao template payloads into Plotly trace, layout, and config objects before rendering.

The workbench SHALL use `Plotly.react` as the default render and refresh path.

The workbench SHALL clean up mounted Plotly charts when the React component unmounts, the pane clears, or the tool-call render is replaced.

The workbench SHALL show deterministic invalid or unsupported component fallbacks for malformed template payloads, unsupported chart types, unsupported trace shapes, datasource-bound payloads when materialization is unsupported, or rejected renderer fields.

#### Scenario: Plotly bar chart renders visibly
- **WHEN** a stream emits a complete `houmao.graphic.template` tool-call sequence for a valid inline bar chart
- **THEN** the workbench renders a visible Plotly chart in the AG-UI pane
- **AND THEN** the raw tool-call event details remain available for diagnostics

#### Scenario: Malformed template payload degrades visibly
- **WHEN** a stream emits a complete `houmao.graphic.template` tool-call sequence with missing required fields
- **THEN** the workbench shows an invalid component fallback
- **AND THEN** the workbench does not crash or remove unrelated pane content

### Requirement: Template graphics reserve presentation datasource binding vocabulary
Layer 1 template graphics SHALL define optional datasource binding fields for future presentation-server-managed table data.

Datasource-bound template payloads SHALL declare datasource dependencies through `dataRefs`.

A trace SHALL use either inline channel arrays or a `source` binding for a channel, not both.

Trace source bindings SHALL reference datasource columns through Houmao-owned binding fields such as `source.dataRef`, `source.x.column`, `source.y.column`, `source.z.column`, `source.labels.column`, `source.values.column`, `source.text.column`, `source.marker.color.column`, and `source.marker.size.column`.

This change SHALL NOT require the workbench server to own datasource rows, materialize datasource bindings, or refresh charts from datasource updates.

Capability metadata SHALL distinguish datasource binding vocabulary from datasource materialization support.

Datasource-bound payloads that reach a workbench without materialization support SHALL render as visible diagnostics rather than blank charts.

#### Scenario: Datasource-bound shape validates as reserved vocabulary
- **WHEN** an agent validates a schema version `2` `houmao.graphic.template` payload that declares `dataRefs` and trace `source` bindings
- **THEN** validation accepts the datasource binding shape when field names and binding paths are valid
- **AND THEN** validation output does not claim that the current workbench can materialize datasource rows

#### Scenario: Datasource-bound rendering is diagnostic-only before materialization
- **WHEN** a workbench receives a valid datasource-bound `houmao.graphic.template` payload
- **AND WHEN** the workbench reports datasource materialization support as false
- **THEN** the pane shows a visible renderer diagnostic that datasource materialization is not supported yet
- **AND THEN** the workbench does not silently render an empty chart

